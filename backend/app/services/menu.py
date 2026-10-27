"""Điều phối thực đơn: sinh ngày, +/- nguyên liệu, pantry, lưu/đọc DB. Số liệu luôn do planner tính."""

import uuid
from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import AppError
from app.core.i18n import Lang, names
from app.db import foods_repo
from app.db import models as M
from app.foods.catalog import FoodCatalog
from app.foods.restrictions import exclusion_reason, reason_msg
from app.nutrition.schemas import DIABETES, HealthProfileIn, NutritionNeeds
from app.planner import (
    DayPlan,
    LockedItem,
    MealPlan,
    MealStructure,
    PlanItem,
    PlanRequest,
    Requirement,
    forbidden_mains,
    solve_day,
)
from app.planner.solver import finalize, totals_of
from app.services import preferences as PREF
from app.services import profile as P
from app.services.targets import day_energy, planner_targets

WINDOW = 4  # số ngày xung quanh để kiểm tra lặp món


# ---------------- catalog & mục tiêu ----------------
def catalogs(s: Session, user_id: uuid.UUID, p: HealthProfileIn) -> tuple[FoodCatalog, FoodCatalog]:
    """(catalog đầy đủ, catalog đã lọc theo dị ứng/chế độ ăn + nguyên liệu riêng hợp lệ của người dùng)."""
    full = foods_repo.global_catalog(s)
    own = foods_repo.user_foods(s, user_id)
    allowed = full.with_foods(own).filtered(p.allergies, p.diets)
    return full.with_foods(own), allowed


def energy_delta(s: Session, user_id: uuid.UUID, day: date) -> float:
    rows = s.scalars(select(M.EnergyAdjustment).where(M.EnergyAdjustment.user_id == user_id,
                                                      M.EnergyAdjustment.day == day)).all()
    return sum(r.delta_kcal for r in rows)


def energy_target(s: Session, user_id: uuid.UUID, needs: NutritionNeeds, day: date) -> float:
    return day_energy(needs, energy_delta(s, user_id, day))


def targets_for(s, user_id, needs, day, energy_override: float | None = None):
    return planner_targets(needs, energy_override if energy_override is not None
                           else energy_target(s, user_id, needs, day))


# ---------------- DB ↔ DayPlan ----------------
def get_day(s: Session, user_id: uuid.UUID, day: date) -> M.MenuDay | None:
    return s.scalar(select(M.MenuDay).where(M.MenuDay.user_id == user_id, M.MenuDay.day == day))


def to_plan(md: M.MenuDay, catalog: FoodCatalog, tolerance: float, include_inactive: bool = False) -> DayPlan:
    meals = []
    for m in md.meals:
        if not m.active and not include_inactive:
            continue
        items = [PlanItem(food_code=i.ingredient_code, grams=i.grams, locked=i.locked, origin=i.origin)
                 for i in m.items if i.ingredient_code in catalog.foods]
        meals.append(MealPlan(slot=m.slot, dish_code=m.dish_code, items=items, totals=totals_of(items, catalog)))
    rep = md.report or {}
    plan = DayPlan(day=md.day, status=md.status, meals=meals, totals=totals_of(
        [i for m in meals for i in m.items], catalog), deviations=rep.get("deviations", []),
        shortfalls=rep.get("shortfalls", []), suggestions=rep.get("suggestions", []),
        conflicts=rep.get("conflicts", []), warnings=rep.get("warnings", []))
    return plan


def save_plan(s: Session, user_id: uuid.UUID, plan: DayPlan, targets) -> M.MenuDay:
    md = get_day(s, user_id, plan.day)
    if md is None:
        md = M.MenuDay(user_id=user_id, day=plan.day, version=0, status=plan.status, targets=[], report={})
        s.add(md)
    md.version = (md.version or 0) + 1
    md.status = plan.status
    md.targets = [t.model_dump() for t in targets]
    md.report = {k: [x.model_dump(mode="json") if hasattr(x, "model_dump") else x for x in getattr(plan, k)]
                 for k in ("deviations", "shortfalls", "suggestions", "conflicts", "warnings")}
    by_slot = {m.slot: m for m in md.meals}
    plan_slots = {m.slot for m in plan.meals}
    for mp in plan.meals:
        row = by_slot.get(mp.slot)
        if row is None:
            row = M.Meal(slot=mp.slot)
            md.meals.append(row)
        changed = row.dish_code != mp.dish_code or sorted((i.ingredient_code for i in row.items)) != sorted(
            i.food_code for i in mp.items)
        row.active, row.dish_code = True, mp.dish_code
        row.items = [M.MealItem(ingredient_code=i.food_code, grams=i.grams, locked=i.locked, origin=i.origin)
                     for i in mp.items]
        if changed:
            row.recipe = None  # công thức cũ không còn khớp
    for slot, row in by_slot.items():
        if slot not in plan_slots:
            if slot == "snack":
                md.meals.remove(row)
            else:
                row.active = False  # giữ dữ liệu bữa khi số bữa thay đổi
    s.flush()
    return md


# ---------------- ràng buộc ngày ----------------
def mains_by_date(s: Session, user_id: uuid.UUID, center: date) -> dict[date, set[str]]:
    rows = s.scalars(select(M.MenuDay).where(M.MenuDay.user_id == user_id,
                                             M.MenuDay.day >= center - timedelta(days=WINDOW),
                                             M.MenuDay.day <= center + timedelta(days=WINDOW))).all()
    return {r.day: {m.dish_code for m in r.meals if m.active and m.dish_code} for r in rows}


def locked_items(s: Session, user_id: uuid.UUID, day: date, md: M.MenuDay | None) -> list[LockedItem]:
    out: list[LockedItem] = []
    if md is not None:
        for m in md.meals:
            for i in m.items:
                if not i.locked or i.origin == "pantry":
                    continue
                if m.slot == "snack":
                    out.append(LockedItem(food_code=i.ingredient_code, grams=i.grams, slot="snack", origin="snack"))
                else:  # bữa đã tắt vẫn gửi slot cũ → planner chuyển thành "có sẵn", không mất nguyên liệu
                    out.append(LockedItem(food_code=i.ingredient_code, grams=i.grams, slot=m.slot, origin=i.origin))
    for pi in s.scalars(select(M.PantryItem).where(M.PantryItem.user_id == user_id, M.PantryItem.day == day)):
        out.append(LockedItem(food_code=pi.ingredient_code, grams=pi.grams, slot=None, origin="pantry"))
    return out


class Ctx:
    """Ngữ cảnh người dùng cho một request."""

    def __init__(self, s: Session, user_id: uuid.UUID, lang: Lang = "vi"):
        self.s, self.user_id, self.lang = s, user_id, lang
        # no_limits: bệnh nền nhạy cảm chưa có giới hạn ⇒ chỉ hiện notice, KHÔNG chặn (vòng 4: tự quản lý)
        self.profile, self.needs, self.no_limits = P.current_needs(s, user_id, lang)
        self.full, self.catalog = catalogs(s, user_id, self.profile)
        self.tol = get_settings().planner_tolerance
        self.disliked_foods, self.disliked_dishes = PREF.dislikes(s, user_id)

    def _recent(self, day: date, mains: dict[date, set[str]]) -> dict[str, int]:
        recent: dict[str, int] = {}
        for d in range(1, 4):
            for dish in mains.get(day - timedelta(days=d), set()):
                recent[dish] = recent.get(dish, 0) + 1
        return recent

    def request(self, day: date, targets, locked: list[LockedItem], forbidden: set[str], **kw) -> PlanRequest:
        return PlanRequest(
            day=day, slots=self.needs.meal_slots, targets=targets, tolerance=self.tol, forbidden_dishes=forbidden,
            locked=locked, prefer_low_gi=bool(set(self.profile.conditions) & DIABETES),
            disliked_foods=self.disliked_foods, disliked_dishes=self.disliked_dishes, **kw)

    def solve(self, day: date, required: list[Requirement] | None = None, snacks: list[LockedItem] | None = None,
              energy_override: float | None = None, keep_structure: bool = False,
              min_meal_energy: float | None = None, extra_locked: list[LockedItem] = ()) -> tuple[DayPlan, list]:
        """`extra_locked`: thành phần món ghép AI ước tính (origin="ai_estimate") từ chatbot."""
        md = get_day(self.s, self.user_id, day)
        locked = locked_items(self.s, self.user_id, day, md)
        if snacks is not None:  # thay danh sách đồ ăn vặt
            locked = [x for x in locked if x.slot != "snack"] + snacks
        if extra_locked:  # món ghép thay chỗ nguyên liệu khóa cũ ở cùng bữa
            slots = {x.slot for x in extra_locked}
            locked = [x for x in locked if x.slot not in slots or x.origin == "pantry"] + list(extra_locked)
        mains = mains_by_date(self.s, self.user_id, day)
        targets = targets_for(self.s, self.user_id, self.needs, day, energy_override)
        recent = self._recent(day, mains)
        structure = None
        if keep_structure and md is not None:
            structure = {m.slot: MealStructure(dish_code=m.dish_code,
                                               food_codes=[i.ingredient_code for i in m.items if not i.locked])
                         for m in md.meals if m.active and m.slot != "snack"}
        req = self.request(day, targets, locked, forbidden_mains(day, mains, self.catalog.dishes),
                           recent_dishes=recent, structure=structure, required=required or [],
                           min_meal_energy_kcal=min_meal_energy)
        return solve_day(req, self.catalog), targets


def generate(s: Session, user_id: uuid.UUID, start: date, days: int) -> list[DayPlan]:
    if not 1 <= days <= 7:
        raise AppError(422, "DAYS_RANGE", key="error.DAYS_RANGE.generate")
    c = Ctx(s, user_id)
    out = []
    for i in range(days):  # tuần tự: ngày sau thấy món chính của ngày trước (ràng buộc lặp món)
        plan, targets = c.solve(start + timedelta(days=i))
        save_plan(s, user_id, plan, targets)
        s.commit()
        out.append(plan)
    return out


def swap(s: Session, user_id: uuid.UUID, day: date, slot: str) -> DayPlan:
    """Đổi MỘT bữa: sinh lại bữa đó, các bữa khác giữ nguyên (khóa đúng slot), pantry/đồ ăn vặt giữ nguyên.
    Cấm món chính hiện tại, món của các bữa khác trong ngày, món không thích; giữ ràng buộc lặp món."""
    c = Ctx(s, user_id)
    md = get_day(s, user_id, day)
    if md is None:
        raise AppError(404, "MENU_NOT_FOUND")
    row = next((m for m in md.meals if m.slot == slot and m.active and slot != "snack"), None)
    if row is None:
        raise AppError(404, "MEAL_NOT_FOUND")
    current = to_plan(md, c.catalog, c.tol)
    target = next(m for m in current.meals if m.slot == slot)
    others = [m for m in current.meals if m.slot not in (slot, "snack")]
    snack = [m for m in current.meals if m.slot == "snack"]
    # bữa giữ nguyên: mọi item (kể cả phần có sẵn) khóa cứng ở đúng slot; origin "frozen" để solver không phân bổ
    # lại phần có sẵn. Kết quả các bữa này lấy lại từ DB (giữ nguyên cờ locked/origin gốc).
    locked = [LockedItem(food_code=i.food_code, grams=i.grams, slot=m.slot, origin="frozen")
              for m in others for i in m.items]
    locked += [LockedItem(food_code=i.food_code, grams=i.grams, slot="snack", origin="snack")
               for m in snack for i in m.items]
    # phần nguyên liệu có sẵn đang nằm ở bữa này được phân bổ lại trong bữa mới
    locked += [LockedItem(food_code=i.food_code, grams=i.grams, slot=None, origin="pantry")
               for i in target.items if i.origin == "pantry"]
    mains = mains_by_date(s, user_id, day)
    forbidden = (forbidden_mains(day, mains, c.catalog.dishes) | c.disliked_dishes
                 | {m.dish_code for m in others if m.dish_code} | ({row.dish_code} if row.dish_code else set()))
    if not any(d.allowed_in(slot) and d.code not in forbidden for d in c.catalog.dishes.values()):
        raise AppError(409, "NO_ALTERNATIVE")
    targets = targets_for(s, user_id, c.needs, day)
    req = c.request(day, targets, locked, forbidden, recent_dishes=c._recent(day, mains),
                    frozen_slots={m.slot for m in others})
    plan = solve_day(req, c.catalog)
    new = next((m for m in plan.meals if m.slot == slot), None)
    if new is None or not new.dish_code or new.dish_code == row.dish_code:
        raise AppError(409, "NO_ALTERNATIVE")
    order = {m.slot: i for i, m in enumerate(current.meals)}
    meals = sorted([*others, new, *snack], key=lambda m: order.get(m.slot, 99))
    final = finalize(PlanRequest(day=day, slots=c.needs.meal_slots, targets=targets, tolerance=c.tol), c.catalog,
                     meals, plan.conflicts, plan.warnings)
    save_plan(s, user_id, final, targets)  # bữa đổi ⇒ xóa công thức cũ; bữa khác không đổi ⇒ giữ công thức
    s.commit()
    return final


def adjust(s: Session, user_id: uuid.UUID, day: date, slot: str, food_code: str, delta_g: float) -> DayPlan:
    """Nút +/-: cố định nguyên liệu tại khối lượng mới, cân bằng lại phần còn lại (giữ cấu trúc bữa)."""
    c = Ctx(s, user_id)
    md = get_day(s, user_id, day)
    if md is None:
        raise AppError(404, "MENU_NOT_FOUND")
    meal = next((m for m in md.meals if m.slot == slot and m.active), None)
    item = next((i for i in meal.items if i.ingredient_code == food_code), None) if meal else None
    if item is None:
        raise AppError(404, "ITEM_NOT_FOUND")
    if food_code not in c.catalog.foods:
        f = c.full.food(food_code)
        reason = exclusion_reason(f, c.profile.allergies, c.profile.diets) or ""
        raise AppError(422, "ALLERGEN_CONFLICT", key="error.ALLERGEN_CONFLICT.item",
                       params={"food": names(f), "reason": reason_msg(reason)}, reason=reason)
    if item.origin == "pantry":
        raise AppError(422, "PANTRY_ITEM")
    if delta_g == 0 or abs(delta_g) > 500:
        raise AppError(422, "DELTA_RANGE")

    if delta_g < 0:
        current = to_plan(md, c.catalog, c.tol).totals.get("energy_kcal", 0.0)
        if current >= energy_target(s, user_id, c.needs, day) * (1 - c.tol):  # đã ăn đủ (trong ngưỡng ±tol)
            P.record_event(s, user_id, "DECREASE_WHEN_MET")
            s.commit()
        if P.ed_status(s, user_id).flagged:
            raise AppError(409, "ED_SUPPORT")

    new_grams = max(0.0, item.grams + delta_g)
    if new_grams == 0:
        meal.items.remove(item)
    else:
        item.grams, item.locked = new_grams, True
        item.origin = "user_adjust" if item.origin == "optimizer" else item.origin
    s.flush()
    plan, targets = c.solve(day, keep_structure=True)
    save_plan(s, user_id, plan, targets)
    s.commit()
    return plan


def unlock(s: Session, user_id: uuid.UUID, day: date, slot: str, food_code: str) -> DayPlan:
    c = Ctx(s, user_id)
    md = get_day(s, user_id, day)
    meal = next((m for m in md.meals if m.slot == slot), None) if md else None
    item = next((i for i in meal.items if i.ingredient_code == food_code), None) if meal else None
    if item is None:
        raise AppError(404, "ITEM_NOT_FOUND")
    item.locked, item.origin = False, "optimizer"
    s.flush()
    plan, targets = c.solve(day, keep_structure=True)
    save_plan(s, user_id, plan, targets)
    s.commit()
    return plan


# ---------------- pantry ----------------
def add_pantry(s: Session, user_id: uuid.UUID, day: date, food_code: str, grams: float) -> list[str]:
    p = P.require_profile(s, user_id)
    if not (0 < grams <= 3000):
        raise AppError(422, "GRAMS_RANGE")
    ing = foods_repo.visible_ingredient(s, user_id, food_code)
    if ing is None:
        raise AppError(404, "FOOD_NOT_FOUND")
    _, allowed = catalogs(s, user_id, p)
    full, _ = catalogs(s, user_id, p)
    if food_code not in allowed.foods:
        reason = exclusion_reason(full.food(food_code), p.allergies, p.diets)
        raise AppError(422, "ALLERGEN_CONFLICT", key="error.ALLERGEN_CONFLICT.item",
                       params={"food": names(ing), "reason": reason_msg(reason)}, reason=reason)
    s.add(M.PantryItem(user_id=user_id, day=day, ingredient_code=food_code, grams=grams))
    s.flush()
    # Phát hiện mâu thuẫn: tổng nguyên liệu tự thêm vượt nhu cầu năng lượng
    warnings = []
    _, needs, _ = P.current_needs(s, user_id)
    rows = s.scalars(select(M.PantryItem).where(M.PantryItem.user_id == user_id, M.PantryItem.day == day)).all()
    kcal = sum(allowed.food(r.ingredient_code).nutrient("energy_kcal", r.grams) for r in rows
               if r.ingredient_code in allowed.foods)
    if kcal > energy_target(s, user_id, needs, day) * (1 + get_settings().planner_tolerance):
        warnings.append("PANTRY_EXCEEDS_ENERGY")
    s.commit()
    return warnings


def apply_plan(s: Session, user_id: uuid.UUID, plan: DayPlan) -> M.MenuDay:
    """Lưu một DayPlan đã được người dùng xác nhận (từ chatbot). Kiểm tra lại dị ứng + lặp món."""
    c = Ctx(s, user_id)
    for m in plan.meals:
        for it in m.items:
            if it.food_code not in c.catalog.foods:
                raise AppError(422, "ALLERGEN_CONFLICT", key="error.ALLERGEN_CONFLICT.proposal")
    mains = mains_by_date(s, user_id, plan.day)
    bad = plan.main_dishes() & forbidden_mains(plan.day, mains, plan.main_dishes())
    if bad:
        raise AppError(409, "ROTATION_VIOLATION", dishes=sorted(bad))
    targets = targets_for(s, user_id, c.needs, plan.day)
    final = finalize(PlanRequest(day=plan.day, slots=c.needs.meal_slots, targets=targets, tolerance=c.tol),
                     c.catalog, plan.meals, plan.conflicts, [])
    return save_plan(s, user_id, final, targets)
