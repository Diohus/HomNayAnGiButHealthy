"""Sinh thực đơn 1 ngày bằng ILP (PuLP + CBC).

Mô hình (xem docs/ARCHITECTURE.md §5):
- q[i,m] nguyên ≥ 0: số bước khối lượng nguyên liệu tự do i trong bữa m; g = step·q.
- u[i,m] nhị phân: i có trong bữa m; min_g·u ≤ g ≤ max_g·u.
- y[d,m] nhị phân: món chính d ở bữa m.
- p[i,m] liên tục: phân bổ nguyên liệu có sẵn (pantry) vào bữa; Σ_m p = khối lượng có sẵn.
- Đồ ăn vặt (slot "snack") là hằng số cố định, cộng vào tổng ngày.
- Độ lệch so với mục tiêu là biến slack ⇒ bài toán luôn khả thi; slack vượt ngưỡng ±tol bị phạt rất nặng.
Tổng dinh dưỡng trả về được tính lại từ nguyên liệu (không lấy từ solver).
"""

import hashlib
from collections import defaultdict

import pulp

from app.foods.catalog import Food, FoodCatalog
from app.planner.schemas import DayPlan, Deviation, MealPlan, PlanItem, PlanRequest, Suggestion

MEAL_SHARE = {
    2: {"lunch": 0.5, "dinner": 0.5},
    3: {"breakfast": 0.25, "lunch": 0.40, "dinner": 0.35},
}
SLOT_ORDER = ["breakfast", "lunch", "dinner"]
SNACK = "snack"
REPORT_CODES = ["energy_kcal", "protein_g", "carb_g", "fat_g", "fiber_g", "calcium_mg", "iron_mg", "zinc_mg",
                "vitamin_d_ug", "sodium_mg", "potassium_mg", "phosphorus_mg"]
CATEGORY_ORDER = ["protein", "carb", "vegetable", "dairy", "fruit", "nut", "fat", "snack"]
UNKNOWN_GI = 70.0  # giả định bảo thủ cho tinh bột chưa có GI
DAILY_MAX_FACTOR = 1.5  # tổng 1 nguyên liệu tự do trong ngày ≤ 1.5 × max_g một bữa
MICROS = ("calcium_mg", "iron_mg", "zinc_mg", "vitamin_d_ug")
FOOD_REPEAT_PENALTY = 2.0  # mỗi ngày (trong 2 ngày trước) đã dùng cùng nguyên liệu protein; > 0,5 của lặp món
EGG_EXTRA_MEAL_PENALTY = 40.0  # trứng là nguồn đạm chính tối đa 1 bữa/ngày (đa dạng — không phải khuyến nghị y khoa)
DISLIKE_PENALTY = 30.0  # phạt mềm cho món/nguyên liệu không thích (< 50 của "bữa thiếu món chính")
MAIN_MIN_SHARE = 0.4  # nguyên liệu chính của món ≥ 40% khẩu phần tối đa (giả định, tránh "món gà" chỉ 50 g)
POOL = {"dish": 6, "carb": 4, "vegetable": 6, "fruit": 3, "dairy": 3, "nut": 2, "fat": 2}


def _jitter(day, key: str, scale: float = 0.3) -> float:
    """Nhiễu xác định theo ngày → thực đơn đa dạng giữa các ngày nhưng tái lập được."""
    h = hashlib.sha256(f"{day.isoformat()}:{key}".encode()).digest()
    return h[0] / 255 * scale


def totals_of(items: list[PlanItem], catalog: FoodCatalog) -> dict[str, float]:
    t = defaultdict(float)
    for it in items:
        f = catalog.food(it.food_code)
        for c in REPORT_CODES:
            t[c] += f.nutrient(c, it.grams)
    return {c: t[c] for c in REPORT_CODES}


def solve_day(req: PlanRequest, catalog: FoodCatalog) -> DayPlan:
    """`catalog` phải đã được lọc theo dị ứng/chế độ ăn của người dùng."""
    conflicts: list[str] = []
    warnings: list[str] = []
    slots = [s for s in SLOT_ORDER if s in req.slots]
    targets = {t.code: t for t in req.targets}
    tol = req.tolerance

    # ---------- Tiền kiểm tra ràng buộc khóa ----------
    fixed: dict[tuple[str, str], float] = defaultdict(float)  # (food, slot) → gram cố định
    fixed_origin: dict[tuple[str, str], str] = {}
    pantry: dict[str, float] = defaultdict(float)
    snacks: dict[str, float] = defaultdict(float)
    for li in req.locked:
        if li.food_code not in catalog.foods:
            conflicts.append(f"FORBIDDEN_LOCKED_ITEM:{li.food_code}")
            continue
        if li.grams <= 0:
            continue
        if li.slot == SNACK or catalog.food(li.food_code).category == "snack":
            snacks[li.food_code] += li.grams
        elif li.slot is None or li.origin == "pantry":
            pantry[li.food_code] += li.grams
        elif li.slot not in slots:
            warnings.append(f"LOCKED_SLOT_INACTIVE:{li.food_code}:{li.slot}")
            pantry[li.food_code] += li.grams
        else:
            fixed[(li.food_code, li.slot)] += li.grams
            fixed_origin[(li.food_code, li.slot)] = li.origin

    frozen = set(req.frozen_slots) | {s for (_, s), o in fixed_origin.items() if o == "ai_estimate"}

    def locked_amount(nutrient: str) -> float:
        return (sum(catalog.food(f).nutrient(nutrient, gr) for (f, _), gr in fixed.items())
                + sum(catalog.food(f).nutrient(nutrient, gr) for f, gr in pantry.items())
                + sum(catalog.food(f).nutrient(nutrient, gr) for f, gr in snacks.items()))

    e_t = targets.get("energy_kcal")
    if e_t and locked_amount("energy_kcal") > e_t.value * (1 + tol):
        conflicts.append("LOCKED_EXCEEDS_ENERGY")
    for code in ("protein_g", "carb_g", "fat_g"):
        t = targets.get(code)
        if t and locked_amount(code) > t.value * (1 + tol):
            conflicts.append(f"LOCKED_EXCEEDS:{code}")

    required_dishes = [r for r in req.required if r.kind == "dish"]
    required_foods = [r for r in req.required if r.kind == "food"]
    for r in required_dishes:
        if r.code not in catalog.dishes:
            conflicts.append(f"REQUIRED_NOT_ALLOWED:{r.code}")
        elif r.code in req.forbidden_dishes:
            conflicts.append(f"REQUIRED_DISH_ROTATION:{r.code}")
        elif r.slot and (r.slot not in slots or not catalog.dishes[r.code].allowed_in(r.slot)
                         or not all(catalog.food(m).allowed_in(r.slot) for m in catalog.dishes[r.code].main)):
            conflicts.append(f"REQUIRED_SLOT_INVALID:{r.code}:{r.slot}")
    for r in required_foods:
        if r.code not in catalog.foods:
            conflicts.append(f"REQUIRED_NOT_ALLOWED:{r.code}")
    req_dish_codes = {r.code for r in required_dishes if not any(r.code in c for c in conflicts)}
    req_food_codes = {r.code for r in required_foods if r.code in catalog.foods}

    # ---------- Mô hình ----------
    prob = pulp.LpProblem("day_plan", pulp.LpMinimize)
    obj = []
    g: dict[tuple[str, str], pulp.LpAffineExpression] = {}
    u: dict[tuple[str, str], pulp.LpVariable] = {}
    y: dict[tuple[str, str], pulp.LpVariable] = {}
    p: dict[tuple[str, str], pulp.LpVariable] = {}

    # Heuristic có kiểm soát: mỗi bữa chỉ đưa một nhóm ứng viên vào ILP (chọn xác định theo ngày) để giải nhanh
    # và đa dạng giữa các ngày. Nguyên liệu khóa/có sẵn/bắt buộc và món dùng chúng luôn được giữ.
    keep_codes = set(pantry) | {c for c, _ in fixed} | req_food_codes

    def disliked_dish(d) -> bool:
        return d.code in req.disliked_dishes or bool(set(d.main) & req.disliked_foods)

    def dish_candidates(slot: str):
        if slot in frozen:
            return []
        if req.structure is not None:
            st = req.structure.get(slot)
            if st and st.dish_code and st.dish_code in catalog.dishes and st.dish_code not in req.forbidden_dishes:
                return [catalog.dishes[st.dish_code]]
            return []
        cands = [d for d in catalog.dishes.values() if d.allowed_in(slot) and d.code not in req.forbidden_dishes]
        must = [d for d in cands if d.code in req_dish_codes or set(d.main) & keep_codes]
        rest = sorted((d for d in cands if d not in must), key=lambda d: (
            disliked_dish(d), _jitter(req.day, f"{slot}:{d.code}", 1.0) + 0.5 * req.recent_dishes.get(d.code, 0)
            + FOOD_REPEAT_PENALTY * sum(req.recent_foods.get(c, 0) for c in d.main), d.code))
        return must + rest[:max(0, (req.dish_pool or POOL["dish"]) - len(must))]

    def free_foods(slot: str, dishes) -> list[Food]:
        if slot in frozen:
            return []
        if req.structure is not None:
            st = req.structure.get(slot)
            codes = set(st.food_codes) if st else set()
            return [catalog.food(c) for c in sorted(codes) if c in catalog.foods and (c, slot) not in fixed]
        allowed = [f for f in catalog.foods.values() if f.allowed_in(slot) and (f.code, slot) not in fixed]
        mains = {c for d in dishes for c in d.main}
        out = [f for f in allowed if f.category == "protein" and f.code in mains]
        for cat, k in POOL.items():
            if cat == "dish":
                continue
            items = [f for f in allowed if f.category == cat]
            keep = [f for f in items if f.code in mains or f.code in keep_codes]
            other = sorted((f for f in items if f not in keep), key=lambda f: (f.code in req.disliked_foods, _jitter(
                req.day, f"{slot}:{f.code}", 1.0) + ((f.gi or UNKNOWN_GI) / 100
                                                     if req.prefer_low_gi and cat == "carb" else 0.0), f.code))
            out += keep + other[:max(0, k - len(keep))]
        return out

    for m in slots:
        dishes_m = dish_candidates(m)
        for f in free_foods(m, dishes_m):
            q = pulp.LpVariable(f"q_{f.code}_{m}", 0, int(f.max_g // f.step_g), cat="Integer")
            uv = pulp.LpVariable(f"u_{f.code}_{m}", cat="Binary")
            expr = f.step_g * q
            prob += expr <= f.max_g * uv
            prob += expr >= f.min_g * uv
            if req.structure is not None:
                prob += uv == 1  # giữ nguyên tập nguyên liệu khi rebalance
            g[(f.code, m)], u[(f.code, m)] = expr, uv
        for d in dishes_m:
            y[(d.code, m)] = pulp.LpVariable(f"y_{d.code}_{m}", cat="Binary")
        for code in pantry:
            f = catalog.food(code)
            if m in frozen:
                continue
            if f.allowed_in(m) or not any(f.allowed_in(s) for s in slots if s not in frozen):
                p[(code, m)] = pulp.LpVariable(f"p_{code}_{m}", 0)
    for code, grams in pantry.items():
        prob += pulp.lpSum(p[(code, m)] for m in slots if (code, m) in p) == grams

    def present(code: str, m: str):
        e = fixed.get((code, m), 0.0)
        if (code, m) in g:
            e = e + g[(code, m)]
        if (code, m) in p:
            e = e + p[(code, m)]
        return e

    def meal_total(nutrient: str, m: str):
        terms = []
        for code in {c for c, s in (*g, *p, *fixed) if s == m}:
            per_g = (catalog.food(code).per_100g.get(nutrient) or 0.0) / 100.0
            if per_g:
                terms.append(per_g * present(code, m))
        return pulp.lpSum(terms)

    # ---------- Cấu trúc bữa ----------
    for m in slots:
        if m in frozen:
            continue
        ys = [v for (d, s), v in y.items() if s == m]
        prob += pulp.lpSum(ys) <= 1
        if req.structure is None or (req.structure.get(m) and req.structure[m].dish_code):
            miss = pulp.LpVariable(f"miss_main_{m}", 0, 1)
            prob += miss >= 1 - pulp.lpSum(ys)
            obj.append(50 * miss)
        for (dcode, s), yv in y.items():
            if s != m:
                continue
            for main in catalog.dishes[dcode].main:
                mf = catalog.food(main)
                prob += present(main, m) >= max(mf.min_g, MAIN_MIN_SHARE * mf.max_g) * yv
            obj.append((0.5 * req.recent_dishes.get(dcode, 0) + _jitter(req.day, dcode)
                        + (DISLIKE_PENALTY if disliked_dish(catalog.dishes[dcode]) else 0.0)) * yv)
        if req.structure is not None:
            continue
        by_cat = defaultdict(list)
        for (code, s), uv in u.items():
            if s == m:
                by_cat[catalog.food(code).category].append((code, uv))
        # protein tự do chỉ xuất hiện khi món chính dùng nó
        for code, uv in by_cat["protein"]:
            prob += uv <= pulp.lpSum(yv for (d, s), yv in y.items() if s == m and code in catalog.dishes[d].main)
        if m != "breakfast":
            for _, uv in by_cat["dairy"]:
                prob += uv == 0
        locked_cats = defaultdict(int)
        for (code, s) in fixed:
            if s == m:
                locked_cats[catalog.food(code).category] += 1
        n_carb = pulp.lpSum(uv for _, uv in by_cat["carb"])
        prob += n_carb <= 2
        miss_carb = pulp.LpVariable(f"miss_carb_{m}", 0, 1)
        prob += n_carb + locked_cats["carb"] + miss_carb >= 1
        obj.append(20 * miss_carb)
        n_veg = pulp.lpSum(uv for _, uv in by_cat["vegetable"])
        if m == "breakfast":
            prob += n_veg <= 2
        else:
            prob += n_veg <= 3
            miss_veg = pulp.LpVariable(f"miss_veg_{m}", 0, 1)
            prob += n_veg + locked_cats["vegetable"] + miss_veg >= 1
            obj.append(10 * miss_veg)
        for cat, cap in (("fruit", 1), ("nut", 1), ("fat", 1), ("dairy", 2)):
            prob += pulp.lpSum(uv for _, uv in by_cat[cat]) <= cap
    for dcode in catalog.dishes:
        vs = [v for (d, _), v in y.items() if d == dcode]
        if len(vs) > 1:
            prob += pulp.lpSum(vs) <= 1  # không lặp cùng món chính trong một ngày

    # Yêu cầu từ người dùng (chatbot): món chính / nguyên liệu phụ bắt buộc
    for r in required_dishes:
        if r.code not in req_dish_codes:
            continue
        vs = [v for (d, s), v in y.items() if d == r.code and (r.slot is None or s == r.slot)]
        if vs:
            prob += pulp.lpSum(vs) >= 1
    for r in required_foods:
        vs = [uv for (c, s), uv in u.items() if c == r.code and (r.slot is None or s == r.slot)]
        already = any(c == r.code and (r.slot is None or s == r.slot) for c, s in fixed)
        if vs and not already:
            prob += pulp.lpSum(vs) >= 1
        elif not vs and not already and r.code in catalog.foods:
            conflicts.append(f"REQUIRED_SLOT_INVALID:{r.code}:{r.slot}")

    # ---------- Mục tiêu dinh dưỡng ----------
    def day_total(nutrient):
        const = sum(catalog.food(c).nutrient(nutrient, gr) for c, gr in snacks.items())
        return pulp.lpSum(meal_total(nutrient, m) for m in slots) + const

    for code, t in targets.items():
        if t.value <= 0:
            continue
        tot = day_total(code)
        if t.kind == "target":
            under = pulp.LpVariable(f"under_{code}", 0)
            over = pulp.LpVariable(f"over_{code}", 0)
            excess = pulp.LpVariable(f"excess_{code}", 0)
            prob += tot - t.value + under - over == 0
            prob += excess >= under - tol * t.value
            prob += excess >= over - tol * t.value
            w = 150 if code == "energy_kcal" else 100
            obj.append(w * (under + over) / t.value)
            obj.append(10 * w * excess / t.value)
        elif t.kind == "min" and code in ("fiber_g", *MICROS):
            under = pulp.LpVariable(f"under_{code}", 0)
            prob += under >= t.value - tot
            obj.append((20 if code == "fiber_g" else 5) * under / t.value)
        elif t.kind == "max":
            over = pulp.LpVariable(f"over_{code}", 0)
            prob += over >= tot - t.value
            obj.append(500 * over / t.value)

    if req.min_meal_energy_kcal:
        prob += pulp.lpSum(meal_total("energy_kcal", m) for m in slots) >= req.min_meal_energy_kcal

    # Phân bổ năng lượng giữa các bữa (phạt ngoài khoảng ±8% năng lượng còn lại sau đồ ăn vặt)
    if e_t and len(slots) in MEAL_SHARE:
        meal_energy = max(e_t.value - sum(catalog.food(c).nutrient("energy_kcal", gr) for c, gr in snacks.items()), 0)
        for m in slots:
            share = MEAL_SHARE[len(slots)][m]
            dev = pulp.LpVariable(f"share_dev_{m}", 0)
            mt = meal_total("energy_kcal", m)
            prob += dev >= mt - (share + 0.08) * meal_energy
            prob += dev >= (share - 0.08) * meal_energy - mt
            obj.append(5 * dev / e_t.value)

    for m, floor in req.min_slot_energy_kcal.items():
        if m in slots and m not in frozen:
            short = pulp.LpVariable(f"slot_floor_{m}", 0)
            prob += short >= floor - meal_total("energy_kcal", m)
            obj.append(200 * short / (e_t.value if e_t else 2000.0))

    # Tiểu đường: ưu tiên GI thấp (phạt tải đường huyết xấp xỉ)
    c_t = targets.get("carb_g")
    if req.prefer_low_gi and c_t:
        gl = []
        for (code, m), expr in g.items():
            f = catalog.food(code)
            if f.category in ("carb", "fruit", "dairy"):
                gl.append((f.gi or UNKNOWN_GI) / 100 * (f.per_100g.get("carb_g") or 0) / 100 * expr)
        obj.append(3 * pulp.lpSum(gl) / c_t.value)

    # Khuyến khích dùng chung nguyên liệu giữa các bữa; giới hạn tổng/ngày; nhiễu để đa dạng giữa các ngày
    for code in sorted({c for c, _ in u}):
        f = catalog.food(code)
        v = pulp.LpVariable(f"distinct_{code}", cat="Binary")
        for (c, m), uv in u.items():
            if c == code:
                prob += v >= uv
        if req.structure is None:
            prob += pulp.lpSum(e for (c, _), e in g.items() if c == code) <= DAILY_MAX_FACTOR * f.max_g
        obj.append((0.3 + _jitter(req.day, code, 0.4)) * v)
        if f.category == "protein" and req.recent_foods.get(code):
            obj.append(FOOD_REPEAT_PENALTY * req.recent_foods[code] * v)
        if code in req.disliked_foods:
            obj.append(DISLIKE_PENALTY * v)

    # Trứng (gà/vịt): tối đa 1 bữa/ngày — ràng buộc mềm, phạt nặng mỗi bữa vượt
    eggs = {c for c, f in catalog.foods.items() if "egg" in f.tags and f.category == "protein"}
    egg_terms = [uv for (c, _), uv in u.items() if c in eggs]
    fixed_egg_meals = len({sl for (c, sl) in fixed if c in eggs})
    if egg_terms:
        egg_excess = pulp.LpVariable("egg_excess", 0)
        prob += egg_excess >= pulp.lpSum(egg_terms) + fixed_egg_meals - 1
        obj.append(EGG_EXTRA_MEAL_PENALTY * egg_excess)

    prob += pulp.lpSum(obj)
    status = prob.solve(pulp.PULP_CBC_CMD(msg=False, timeLimit=req.time_limit_s, gapRel=0.01, gapAbs=3.0))
    if status != pulp.LpStatusOptimal and prob.sol_status not in (pulp.LpSolutionOptimal,
                                                                  pulp.LpSolutionIntegerFeasible):
        return DayPlan(day=req.day, status="conflict", meals=[], totals={}, deviations=[],
                       conflicts=conflicts + ["SOLVER_NO_SOLUTION"], warnings=warnings)

    # ---------- Trích kết quả ----------
    meals: list[MealPlan] = []
    for m in slots:
        items: list[PlanItem] = []
        for (code, s), expr in g.items():
            if s == m:
                grams = round(pulp.value(expr) or 0)
                if grams > 0:
                    items.append(PlanItem(food_code=code, grams=grams))
        for (code, s), grams in fixed.items():
            if s == m:
                items.append(PlanItem(food_code=code, grams=grams, locked=True, origin=fixed_origin[(code, s)]))
        for (code, s), var in p.items():
            if s == m:
                grams = round(var.value() or 0)
                if grams > 0:
                    items.append(PlanItem(food_code=code, grams=grams, locked=True, origin="pantry"))
        dish = next((d for (d, s), v in y.items() if s == m and (v.value() or 0) > 0.5), None)
        meals.append(MealPlan(slot=m, dish_code=dish, items=_sorted(items, catalog), totals={}))

    # Bảo toàn tổng pantry sau khi làm tròn
    for code, grams in pantry.items():
        its = [it for ml in meals for it in ml.items if it.food_code == code and it.origin == "pantry"]
        diff = grams - sum(it.grams for it in its)
        if its and diff:
            its[-1].grams += diff
    if snacks:
        meals.append(MealPlan(slot=SNACK, dish_code=None, totals={}, items=[
            PlanItem(food_code=c, grams=gr, locked=True, origin="snack") for c, gr in sorted(snacks.items())]))
    for ml in meals:
        ml.totals = totals_of(ml.items, catalog)
    # Không còn lựa chọn khác ⇒ vẫn dùng món/nguyên liệu không thích nhưng báo rõ
    for ml in meals:
        if ml.dish_code and ml.dish_code in req.disliked_dishes:
            warnings.append(f"USED_DISLIKED:{ml.dish_code}")
        for it in ml.items:
            if it.food_code in req.disliked_foods and not it.locked:
                warnings.append(f"USED_DISLIKED:{it.food_code}")
    warnings = list(dict.fromkeys(warnings))

    return finalize(req, catalog, meals, conflicts, warnings)


def _sorted(items: list[PlanItem], catalog: FoodCatalog) -> list[PlanItem]:
    return sorted(items, key=lambda it: (CATEGORY_ORDER.index(catalog.food(it.food_code).category), it.food_code))


def finalize(req: PlanRequest, catalog: FoodCatalog, meals: list[MealPlan], conflicts: list[str],
             warnings: list[str]) -> DayPlan:
    """Tính tổng từ nguyên liệu, so với mục tiêu, liệt kê thiếu hụt và gợi ý bổ sung."""
    all_items = [it for m in meals for it in m.items]
    totals = totals_of(all_items, catalog)
    deviations, shortfalls, hard_fail = [], [], False
    for t in req.targets:
        actual = totals.get(t.code, 0.0)
        pct = (actual - t.value) / t.value if t.value else 0.0
        if t.kind == "target":
            within = abs(pct) <= req.tolerance + 1e-9
        elif t.kind == "min":
            within = actual >= t.value * (1 - req.tolerance) - 1e-9
        else:
            within = actual <= t.value * (1 + 1e-9)
        deviations.append(Deviation(code=t.code, kind=t.kind, target=t.value, actual=actual, pct=pct, within=within))
        if not within:
            shortfalls.append(t.code)
            if t.kind in ("target", "max"):
                hard_fail = True
    for m in meals:
        kept = m.slot in req.frozen_slots or (m.items and all(
            it.origin in ("frozen", "ai_estimate", "intake") for it in m.items))
        if m.slot != SNACK and m.dish_code is None and m.items and not kept:  # bữa giữ nguyên/đã ăn: không báo
            warnings.append(f"NO_MAIN_DISH:{m.slot}")

    used = {it.food_code for it in all_items}
    suggestions = []
    for d in deviations:
        if d.within or d.kind == "max" or d.actual >= d.target:
            continue
        # Không bao giờ gợi ý đồ ăn vặt / số liệu người dùng tự nhập để bù thiếu hụt.
        ranked = sorted(
            (f for f in catalog.foods.values() if f.code not in used and f.category != "snack"
             and not f.user_provided and (f.per_100g.get(d.code) or 0) > 0),
            key=lambda f: (-f.nutrient(d.code, f.max_g), f.code),
        )
        suggestions.append(Suggestion(nutrient=d.code, food_codes=[f.code for f in ranked[:3]]))

    status = "conflict" if conflicts and hard_fail else ("partial" if hard_fail else "ok")
    return DayPlan(day=req.day, status=status, meals=meals, totals=totals, deviations=deviations,
                   shortfalls=shortfalls, suggestions=suggestions, conflicts=conflicts, warnings=warnings)
