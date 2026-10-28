"""Logic xác định của chatbot. Không I/O: mọi dữ liệu và planner được truyền qua ChatContext.
Mọi câu trả lời lấy từ catalog i18n theo `ctx.lang` (app/i18n)."""

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from itertools import pairwise

from app.chat.schemas import ChatReply, DetectedFood, ParsedIntent, Proposal
from app.core.i18n import Lang, Msg, name_of, tr
from app.foods.catalog import FoodCatalog
from app.foods.matching import (
    CONTAINER_WORDS,
    FoodMatch,
    find_dishes,
    find_foods,
    find_unknown_compounds,
    has_diacritics,
    normalize,
)
from app.foods.resolve import Resolution
from app.foods.restrictions import exclusion_reason, reason_msg
from app.guardrails.eating_disorder import SUPPORT_KEY, SafetyEventIn, detect_text_signals, would_flag
from app.nutrition.compensation import (
    MAX_DAYS,
    MEAL_FLOOR_SHARE,
    DayEnergy,
    cheat_day_energy,
    plan_compensation,
)
from app.planner.rotation import forbidden_mains
from app.planner.schemas import DayPlan, LockedItem, Requirement

MAX_SNACK_PORTIONS = 10
TEXT_DISLIKE_MAX = 40  # "không thích" dạng chữ (ngoài catalog), vd "hành", "ngò"

# plan_fn(day, required, snack_items, energy_override_kcal, min_meal_energy_kcal, extra_locked) -> DayPlan
# extra_locked: thành phần món ghép do AI ước tính (origin="ai_estimate"), cố định ở bữa của nó
PlanFn = Callable[[date, list[Requirement], list[LockedItem], float | None, float | None, list[LockedItem]],
                  DayPlan]
# resolve_fn(mentions) -> {mention: Resolution} (K1, LLM). None/thiếu mention ⇒ giữ hành vi cũ (need_label)
ResolveFn = Callable[[list[str]], dict[str, Resolution]]


@dataclass
class ChatContext:
    now: datetime
    slots: list[str]
    allergies: list[str]
    diets: list[str]
    catalog_full: FoodCatalog  # chưa lọc (để giải thích vì sao bị loại)
    catalog: FoodCatalog  # đã lọc + nguyên liệu riêng của người dùng
    energy_target: Callable[[date], float]  # mục tiêu năng lượng ngày (đã gồm điều chỉnh bù)
    energy_floor: float
    plan_fn: PlanFn
    mains_by_date: dict[date, set[str]] = field(default_factory=dict)
    snacks_by_date: dict[date, list[LockedItem]] = field(default_factory=dict)
    safety_events: list[SafetyEventIn] = field(default_factory=list)
    ed_flagged: bool = False
    lang: Lang = "vi"  # ngôn ngữ câu trả lời (Accept-Language); tin đã lưu giữ nguyên ngôn ngữ lúc gửi
    resolve_fn: ResolveFn | None = None
    # rebalance_preview(intake_items) -> DayPlan | None: thực đơn sau khi cân lại (service tính, engine không I/O)
    rebalance_preview: Callable[[list[dict]], DayPlan | None] | None = None
    resolved: dict[str, str] = field(default_factory=dict)  # lựa chọn của người dùng sau "clarify": mention → mã

    def t(self, key: str, **params) -> str:
        return tr(key, self.lang, **params)

    def food_name(self, code: str) -> str:
        cat = self.catalog if code in self.catalog.foods else self.catalog_full
        return name_of(cat.food(code), self.lang)

    def slot_name(self, slot: str) -> str:
        return self.t(f"slot.{slot}")

    def inline(self, name: str) -> str:
        """Tên đặt giữa câu: tiếng Việt viết thường như cũ; tiếng Anh giữ nguyên (tên hiển thị đã tự nhiên)."""
        return name.lower() if self.lang == "vi" else name


def kcal(v: float) -> int:
    """Hiển thị năng lượng làm tròn 10 kcal (dữ liệu chỉ chính xác ±10–20%)."""
    return int(round(v / 10.0) * 10)


def _plan_lines(plan: DayPlan, ctx: ChatContext) -> list[str]:
    lines = []
    for m in plan.meals:
        dish = name_of(ctx.catalog_full.dishes[m.dish_code], ctx.lang) if m.dish_code else None
        items = ", ".join(f"{int(it.grams)} g {ctx.inline(ctx.food_name(it.food_code))}" for it in m.items)
        lines.append(f"• {ctx.slot_name(m.slot)}{' — ' + dish if dish else ''}: {items} "
                     f"(~{kcal(m.totals['energy_kcal'])} kcal)")
    return lines


def _target_day(p: ParsedIntent, now: datetime) -> date:
    return now.date() + timedelta(days=1) if p.day == "tomorrow" else now.date()


def _default_slot(ctx: ChatContext, day: date) -> str:
    if day > ctx.now.date():
        return "lunch"
    h = ctx.now.hour
    if h < 10 and "breakfast" in ctx.slots:
        return "breakfast"
    if h < 14:
        return "lunch"
    return "dinner"


def _meal_energy(plan: DayPlan) -> float:
    return sum(m.totals.get("energy_kcal", 0.0) for m in plan.meals if m.slot != "snack")


def handle(text: str, parsed: ParsedIntent, ctx: ChatContext, parser_name: str = "rules") -> ChatReply:
    reply = _handle(text, parsed, ctx)
    reply.parser = parser_name
    return reply


def _handle(text: str, parsed: ParsedIntent, ctx: ChatContext) -> ChatReply:
    # ---------- 1. Guardrail rối loạn ăn uống ----------
    signals = detect_text_signals(text)
    if parsed.intent == "restrict" and "RESTRICT_INTENT" not in signals and "DISTRESS" not in signals:
        signals.append("RESTRICT_INTENT")
    if "DISTRESS" in signals:
        return ChatReply(kind="support", text=ctx.t(SUPPORT_KEY), safety_events=["DISTRESS"])
    if "RESTRICT_INTENT" in signals:
        flagged = ctx.ed_flagged or would_flag(ctx.safety_events, "RESTRICT_INTENT", ctx.now)
        msg = ctx.t(SUPPORT_KEY) if flagged else ctx.t("chat.restrict", floor=kcal(ctx.energy_floor))
        return ChatReply(kind="support", text=msg, safety_events=["RESTRICT_INTENT"])

    # Câu nói về DỊ ỨNG: không tự sửa hồ sơ (dữ liệu sức khỏe, ràng buộc cứng) ⇒ hướng dẫn cập nhật trong Hồ sơ
    if parsed.intent == "allergy":
        return ChatReply(kind="allergy_redirect", text=ctx.t("chat.allergy_redirect"))

    # ---------- 2. Nhận diện món ----------
    matches = find_foods(text, ctx.catalog_full)
    for mention in parsed.mentions:  # LLM có thể tách tên món; vẫn phải khớp catalog bằng quy tắc
        for m in find_foods(mention, ctx.catalog_full):
            if all(m.food_code != x.food_code for x in matches):
                matches.append(m)
    unknown = [m for m in parsed.mentions if not find_foods(m, ctx.catalog_full) and not find_foods(m, ctx.catalog)]
    user_names = {f.name_vi.lower() for f in ctx.catalog.foods.values() if f.user_provided}
    unknown += [c for c in find_unknown_compounds(text) if c not in unknown and c not in user_names]
    # nguyên liệu riêng của người dùng (nhập từ nhãn)
    for m in find_foods(text, ctx.catalog):
        if m.food_code not in ctx.catalog_full.foods and all(m.food_code != x.food_code for x in matches):
            matches.append(m)

    # 2a. Món gọi đúng tên trong catalog ("phở bò", "canh chua cá lóc") ⇒ dùng món đó, không tách nguyên liệu,
    #     không cần LLM (vòng 7: catalog có món thì ưu tiên dish hơn món ghép)
    dish_hint: dict[str, str] = {}
    named = find_dishes(text, ctx.catalog_full)
    if named:
        inner = {m.food_code for code, s, e in named for m in find_foods(text, ctx.catalog_full)
                 if m.start >= s and m.end <= e}
        matches = [m for m in matches if m.food_code not in inner]
        for code, _, _ in named:
            mains = ctx.catalog_full.dishes[code].main
            dish_hint[mains[0]] = code
            for fc in mains if parsed.intent == "log_food" else mains[:1]:
                if all(fc != x.food_code for x in matches):
                    matches.append(FoodMatch(food_code=fc, alias=code, start=0, end=0))
        unknown = [u for u in unknown if not find_dishes(u, ctx.catalog_full)]

    # 2b. K1: mention chưa khớp chính xác ⇒ LLM chọn trong ứng viên; lựa chọn của người dùng (clarify) thắng
    composites: list[Resolution] = []
    clarify: list[Resolution] = []
    res: dict[str, Resolution] = {}
    picked = {m: r for m, code in ctx.resolved.items() if (r := _picked(m, code, ctx)) is not None}
    # mention chỉ khớp MỘT PHẦN alias ("bún bò huế" ⇒ "bún" + "bò") cũng nhờ LLM hiểu cả cụm
    partial = [m for m in parsed.mentions if m not in unknown and not find_dishes(m, ctx.catalog_full)
               and _partial(m, ctx)] if ctx.resolve_fn else []
    todo = [m for m in unknown + partial if m not in picked]  # lựa chọn không hợp lệ ⇒ hỏi LLM như bình thường
    if ctx.resolve_fn and todo:
        res.update(ctx.resolve_fn(todo))
    res.update(picked)
    for m in partial:  # LLM hiểu thành món/món ghép/nguyên liệu khác ⇒ bỏ các khớp lẻ bên trong cụm
        r = res.get(m)
        inner = {x.food_code for x in find_foods(m, ctx.catalog_full)}
        if r is None or r.kind in ("not_food", "unknown") or (r.kind == "ingredient" and r.food_code in inner):
            res.pop(m, None)  # giữ khớp alias cũ (kể cả số lượng "2 cây kem")
            continue
        matches = [x for x in matches if x.food_code not in inner]
    for mention, r in res.items():
        code = r.food_code or (ctx.catalog_full.dishes[r.dish_code].main[0] if r.dish_code else None)
        if r.kind in ("ingredient", "dish") and code:
            if r.dish_code:
                dish_hint[code] = r.dish_code
            if all(code != x.food_code for x in matches):
                matches.append(FoodMatch(food_code=code, alias=mention, start=0, end=0))
        elif r.kind == "composite":
            composites.append(r)
        elif r.kind == "clarify":
            clarify.append(r)
    unknown = [m for m in unknown if m not in res or res[m].kind in ("not_food", "unknown")]
    if clarify:
        return ChatReply(kind="clarify", text=ctx.t("chat.clarify"), clarify=[
            {"mention": r.mention, "options": [{"code": o, "name": _option_name(o, ctx)} for o in r.options]}
            for r in clarify])

    if parsed.intent == "log_food":
        return _log(matches, composites, unknown, parsed, ctx, dish_hint)

    if parsed.intent == "dislike":
        objs = unknown + [r.mention for r in composites]
        if not matches and not objs and parsed.dislike_object:  # parser quy tắc không tách được mention
            objs = [parsed.dislike_object]
        return _dislike(matches, ctx, objs)

    if not matches and not composites:
        if parsed.intent == "want_food" or unknown:
            what = ctx.t("chat.unknown_named", names=", ".join(unknown)) if unknown else ctx.t("chat.unknown_any")
            return ChatReply(kind="need_label", unknown_mentions=unknown, text=ctx.t("chat.need_label", what=what))
        return ChatReply(kind="info", text=ctx.t("chat.help"))

    detected: list[DetectedFood] = []
    for m in matches:
        cat = ctx.catalog if m.food_code in ctx.catalog.foods else ctx.catalog_full
        f = cat.food(m.food_code)
        reason = None if m.food_code in ctx.catalog.foods else exclusion_reason(f, ctx.allergies, ctx.diets)
        role = cat.role(m.food_code)
        detected.append(DetectedFood(food_code=f.code, name=name_of(f, ctx.lang), role=role, allowed=reason is None,
                                     reason=reason, dish_code=dish_hint.get(f.code)))

    refused = [d for d in detected if not d.allowed]
    ok = [d for d in detected if d.allowed]
    refusal_text = ""
    if refused:
        # Lý do luôn là tên đã dịch ("dị ứng cá" / "fish allergy"), không bao giờ là mã thô
        refusal_text = " ".join(ctx.t("chat.refusal", food=ctx.inline(d.name), reason=reason_msg(d.reason))
                                for d in refused)
    # Món ghép: dị ứng vẫn là ràng buộc CỨNG — thành phần nào bị loại thì từ chối cả món và nêu thành phần đó
    ok_composites: list[Resolution] = []
    for r in composites:
        bad = [c for c, _ in r.components if c not in ctx.catalog.foods]
        if bad:
            f = ctx.catalog_full.food(bad[0])
            refusal_text = " ".join(x for x in [refusal_text, ctx.t(
                "chat.refusal_component", food=r.mention, component=ctx.inline(name_of(f, ctx.lang)),
                reason=reason_msg(exclusion_reason(f, ctx.allergies, ctx.diets)))] if x)
        else:
            ok_composites.append(r)
    if (refused or len(ok_composites) < len(composites)) and not ok and not ok_composites:
        return ChatReply(kind="refusal", text=refusal_text, detected=detected, unknown_mentions=unknown)

    day = _target_day(parsed, ctx.now)
    mains = [d for d in ok if d.role == "main"]
    sides = [d for d in ok if d.role == "side"]
    snacks = [d for d in ok if d.role == "snack"]

    # ---------- 3. Món chính / phụ → xây thực đơn xoay quanh ----------
    required: list[Requirement] = []
    notes: list[str] = []
    slot = parsed.slot if parsed.slot in ctx.slots else None
    if parsed.slot and parsed.slot not in ("snack", None) and parsed.slot not in ctx.slots:
        notes.append(ctx.t("chat.slot_not_in_plan", slot=ctx.slot_name(parsed.slot)))
    used_slots: set[str] = set()
    extra: list[LockedItem] = []
    for r in ok_composites[:2]:  # món ghép chiếm trọn một bữa, khối lượng do AI ước tính (sai số cao)
        cslot = next((s for s in [slot or _default_slot(ctx, day), *ctx.slots] if s not in used_slots), None)
        if cslot is None:
            continue
        used_slots.add(cslot)
        extra += [LockedItem(food_code=c, grams=g, slot=cslot, origin="ai_estimate") for c, g in r.components]
    if ok_composites:
        notes.append(ctx.t("chat.ai_estimate_note", dishes=", ".join(r.mention for r in ok_composites)))

    def plan_fn(d, req, sn, e, mm):
        return ctx.plan_fn(d, req, sn, e, mm, extra)

    for d in mains[:2]:
        want_slot = slot or _default_slot(ctx, day)
        cands = [x for x in ctx.catalog.dishes.values() if d.food_code in x.main]
        forbidden = forbidden_mains(day, ctx.mains_by_date, [c.code for c in cands])
        order = [want_slot] + [s for s in ctx.slots if s != want_slot]
        hinted = ctx.catalog.dishes.get(d.dish_code) if d.dish_code else None
        if hinted is not None and hinted.code not in forbidden:  # gọi đích danh món ⇒ không đổi sang món khác
            cands = [hinted]
        chosen = None
        for s in order:
            if s in used_slots:
                continue
            ok_dishes = sorted(c.code for c in cands if c.allowed_in(s) and c.code not in forbidden)
            if ok_dishes:
                chosen = (d.dish_code if d.dish_code in ok_dishes else ok_dishes[0], s)
                break
        if chosen is None:
            if cands and all(c.code in forbidden for c in cands):
                when = ctx.t("chat.day.today" if day == ctx.now.date() else "chat.day.selected")
                notes.append(ctx.t("chat.rotation_blocked", food=ctx.inline(d.name), when=when))
            else:
                notes.append(ctx.t("chat.no_dish_for", food=ctx.inline(d.name)))
            continue
        required.append(Requirement(kind="dish", code=chosen[0], slot=chosen[1]))
        used_slots.add(chosen[1])
        if chosen[1] != want_slot:
            notes.append(ctx.t("chat.moved_to_slot", food=d.name, slot=ctx.slot_name(chosen[1]).lower()))
    for d in sides:
        f = ctx.catalog.food(d.food_code)
        s = next(iter(used_slots), None) or slot
        if s and not f.allowed_in(s):
            s = None
        required.append(Requirement(kind="food", code=d.food_code, slot=s))

    existing_snacks = list(ctx.snacks_by_date.get(day, []))

    if not snacks:
        if not required and not extra:
            return ChatReply(kind="info", detected=detected, unknown_mentions=unknown,
                             text=" ".join([refusal_text, *notes]).strip() or ctx.t("chat.no_change"))
        plan = plan_fn(day, required, existing_snacks, None, None)
        around = list(dict.fromkeys(  # món gọi đích danh ⇒ nêu tên món, không nêu nguyên liệu
            ctx.inline(name_of(ctx.catalog_full.dishes[d.dish_code], ctx.lang) if d.dish_code else d.name)
            for d in mains + sides)) + [r.mention for r in ok_composites]
        if not _usable(plan):  # không bao giờ đưa đề xuất thực đơn rỗng/xung đột
            return ChatReply(kind="info", detected=detected, unknown_mentions=unknown, text=" ".join(
                [ctx.t("chat.cannot_schedule", foods=", ".join(around), day=_day_name(day, ctx)), *notes,
                 refusal_text]).strip())
        text_lines = [ctx.t("chat.propose_around", day=_day_name(day, ctx), foods=", ".join(around)),
                      *_plan_lines(plan, ctx)]
        text_lines.append(_totals_line(plan, ctx.energy_target(day), ctx))
        text_lines += _shortfall_lines(plan, ctx)
        text_lines += notes
        if refusal_text:
            text_lines.append(refusal_text)
        return ChatReply(kind="proposal", detected=detected, unknown_mentions=unknown, text="\n".join(text_lines),
                         proposals=[Proposal(key="plan_update", label=ctx.t("chat.label.apply_plan"), day=day,
                                             plan=plan)])

    # ---------- 4. Đồ ăn vặt → điều chỉnh cả ngày / cheat day ----------
    qty = {m.food_code: (m.qty_value, m.qty_unit) for m in matches}
    new_items: list[LockedItem] = []
    for sn in snacks:
        food = ctx.catalog.food(sn.food_code)
        portion_g = food.portion.grams if food.portion else 100.0
        qv, qu = qty.get(sn.food_code, (None, None))
        if qv is None and len(snacks) == 1:
            qv, qu = parsed.quantity_value, parsed.quantity_unit
        if qv and qu in ("g", "ml"):
            grams = qv  # GIẢ ĐỊNH: đồ uống 1 ml ≈ 1 g
        elif qv and qu == "portion":
            grams = qv * portion_g
        else:
            grams = portion_g
        if grams <= 0 or grams > MAX_SNACK_PORTIONS * portion_g:
            return ChatReply(kind="warning", detected=detected, text=ctx.t(
                "chat.snack_out_of_range", food=ctx.inline(sn.name), grams=f"{grams:g}", max=MAX_SNACK_PORTIONS))
        new_items.append(LockedItem(food_code=sn.food_code, grams=round(grams), slot="snack", origin="snack"))

    def snack_kcal(items: list[LockedItem]) -> float:
        return sum(ctx.catalog.food(i.food_code).nutrient("energy_kcal", i.grams) for i in items)

    def snack_dicts(items: list[LockedItem]) -> list[dict]:
        return [{"food_code": i.food_code, "grams": i.grams} for i in items]

    def fits(plan: DayPlan) -> bool:
        return plan.status == "ok" and _meal_energy(plan) >= MEAL_FLOOR_SHARE * target - 1e-6

    target = ctx.energy_target(day)
    head = "; ".join(
        f"{ctx.food_name(i.food_code)} {int(i.grams)} g ≈ "
        f"{kcal(ctx.catalog.food(i.food_code).nutrient('energy_kcal', i.grams))} kcal"
        f"{ctx.t('chat.from_label') if ctx.catalog.food(i.food_code).user_provided else ''}"
        for i in new_items) + ". "
    all_snacks = [*existing_snacks, *new_items]

    absorb = plan_fn(day, required, all_snacks, None, None)
    if fits(absorb):
        cheat_note = [ctx.t("chat.no_cheat_needed")] if parsed.cheat_day else []
        lines = [head + ctx.t("chat.absorbed", day=_day_name(day, ctx), kcal=kcal(target)),
                 *_plan_lines(absorb, ctx), _totals_line(absorb, target, ctx),
                 *_shortfall_lines(absorb, ctx), *cheat_note, *notes]
        if refusal_text:
            lines.append(refusal_text)
        return ChatReply(kind="proposal", detected=detected, text="\n".join(lines), proposals=[
            Proposal(key="absorb", label=ctx.t("chat.label.apply"), day=day, plan=absorb,
                     snacks=snack_dicts(new_items))])

    proposals: list[Proposal] = []
    lines = [head + ctx.t("chat.too_much", day=_day_name(day, ctx), kcal=kcal(target))]
    # Phương án 1: ăn ít hơn — thu nhỏ các món vừa thêm theo tỉ lệ, kiểm chứng bằng planner (tối đa 4 lần giải)
    for factor in (0.75, 0.5, 0.33, 0.25):
        smaller = []
        for i in new_items:
            st = ctx.catalog.food(i.food_code).step_g
            g = int(i.grams * factor // st * st)
            if g >= st:
                smaller.append(i.model_copy(update={"grams": g}))
        if not smaller:
            break
        alt = plan_fn(day, required, [*existing_snacks, *smaller], None, None)
        if fits(alt):
            desc = ", ".join(f"{int(i.grams)} g {ctx.inline(ctx.food_name(i.food_code))}" for i in smaller)
            proposals.append(Proposal(key="smaller_portion", day=day, plan=alt, snacks=snack_dicts(smaller),
                                      label=ctx.t("chat.label.smaller", desc=desc, kcal=kcal(snack_kcal(smaller)))))
            break

    # Phương án 2: cheat day — bữa chính vẫn đủ, phần vượt bù có giới hạn vào các ngày sau
    e_cheat = cheat_day_energy(target, snack_kcal(all_snacks))
    cheat_plan = plan_fn(day, required, all_snacks, e_cheat, MEAL_FLOOR_SHARE * target)
    overflow = max(cheat_plan.totals.get("energy_kcal", 0.0) - target, 0.0)
    no_comp = ctx.ed_flagged or would_flag(ctx.safety_events, "COMPENSATION", ctx.now)
    if no_comp:
        comp = None
        cheat_label = ctx.t("chat.label.cheat_no_comp", kcal=kcal(overflow))
    else:
        nxt = [DayEnergy(day=day + timedelta(days=i), target_kcal=ctx.energy_target(day + timedelta(days=i)),
                         floor_kcal=ctx.energy_floor) for i in range(1, MAX_DAYS + 1)]
        comp = plan_compensation(overflow, nxt)
        spread = ", ".join(f"{r.day.strftime(ctx.t('chat.date_fmt'))} −{kcal(r.kcal)}" for r in comp.reductions)
        forgiven = ctx.t("chat.forgiven", kcal=kcal(comp.forgiven_kcal)) if comp.forgiven_kcal >= 5 else ""
        cheat_label = ctx.t("chat.label.cheat", kcal=kcal(overflow), spread=spread or ctx.t("chat.none"),
                            forgiven=forgiven)
    if _usable(cheat_plan):
        proposals.append(Proposal(key="cheat_day", label=cheat_label, day=day, plan=cheat_plan, compensation=comp,
                                  snacks=snack_dicts(new_items),
                                  records_compensation_event=comp is not None and bool(comp.reductions)))
        lines += [ctx.t("chat.cheat_head", pct=int(MEAL_FLOOR_SHARE * 100)), *_plan_lines(cheat_plan, ctx)]
        lines.append(ctx.t(SUPPORT_KEY) if no_comp else ctx.t("chat.comp_note"))
    if not proposals:  # không phương án nào xếp được
        names = ", ".join(ctx.inline(sn.name) for sn in snacks)
        return ChatReply(kind="info", detected=detected, text=" ".join(
            [ctx.t("chat.cannot_schedule", foods=names, day=_day_name(day, ctx)), *notes, refusal_text]).strip())
    lines += notes
    if refusal_text:
        lines.append(refusal_text)
    return ChatReply(kind="warning", detected=detected, text="\n".join(x for x in lines if x), proposals=proposals)


# Từ chỉ số lượng/đơn vị/động từ không làm một mention thành "khớp một phần" (tránh gọi LLM thừa: "2 cây kem")
_FILLER = {"cay", "phan", "mon", "chiec", "qua", "trai", "mot", "hai", "ba", "it", "nhieu", "them", "an", "uong",
           "g", "gr", "gram", "kg", "ml", "l", "a", "some", "the", "of", "piece", "pieces", "cup", "glass",
           "bowl", "plate", "serving", *CONTAINER_WORDS}


def _partial(mention: str, ctx: ChatContext) -> bool:
    """Có khớp alias nhưng còn từ có nghĩa chưa được phủ (vd "bún bò huế": "huế" chưa khớp)."""
    keep = has_diacritics(mention)
    norm = normalize(mention, keep)
    ms = find_foods(mention, ctx.catalog_full)
    if not ms:
        return False
    # ≥ 2 alias liền kề, không có từ khác chen giữa ("phở bò", "bánh mì trứng") ⇒ có thể là món ghép
    spans = sorted((x.start, x.end) for x in ms)
    if any(not norm[a[1]:b[0]].strip() for a, b in pairwise(spans)):
        return True
    covered = [False] * len(norm)
    for x in ms:
        covered[x.start:x.end] = [True] * (x.end - x.start)
    i = 0
    for tok in norm.split(" "):
        start = norm.find(tok, i) if tok else i
        i = start + len(tok)
        if not tok or all(covered[start:i]):
            continue
        plain = normalize(tok).strip()
        if plain in _FILLER or plain.replace(".", "").replace(",", "").isdigit():
            continue
        return True
    return False


def _usable(plan: DayPlan | None) -> bool:
    """Thực đơn đề xuất được: không xung đột, có bữa chính có món, tổng năng lượng > 0."""
    return (plan is not None and plan.status != "conflict"
            and any(m.items for m in plan.meals if m.slot != "snack")
            and plan.totals.get("energy_kcal", 0.0) > 0)


def _past_slot(ctx: ChatContext) -> str:
    """Bữa vừa ăn theo giờ hiện tại (câu thì quá khứ)."""
    h = ctx.now.hour
    if h < 11 and "breakfast" in ctx.slots:
        return "breakfast"
    if h < 16 and "lunch" in ctx.slots:
        return "lunch"
    return "dinner" if "dinner" in ctx.slots else ctx.slots[-1]


def _log_grams(m: FoodMatch, f, parsed: ParsedIntent, single: bool) -> float:
    qv, qu = m.qty_value, m.qty_unit
    if qv is None and single:
        qv, qu = parsed.quantity_value, parsed.quantity_unit
    unit = f.portion.grams if f.portion else round((f.min_g + f.max_g) / 2 / f.step_g) * f.step_g
    if qv and qu in ("g", "ml"):
        return float(qv)
    return float(round((qv if qv and qu == "portion" else 1) * unit))


def _log(matches: list[FoodMatch], composites: list[Resolution], unknown: list[str], parsed: ParsedIntent,
         ctx: ChatContext, dish_hint: dict[str, str] | None = None) -> ChatReply:
    """Đã ăn (thì quá khứ) ⇒ đề xuất ghi nhật ký hôm nay + đề xuất cân lại các bữa còn lại. Dị ứng vẫn là ràng
    buộc cứng (không ghi món bị loại). Người dùng bấm Áp dụng mới lưu. Món trong catalog ⇒ ghi cả nguyên liệu
    chính lẫn phần ăn kèm điển hình (`log_sides`), gắn source="estimate" (khẩu phần ước tính, sửa được)."""
    if parsed.past_day:  # "tối qua ăn phở": chưa hỗ trợ ghi nhật ký ngày đã qua
        return ChatReply(kind="info", text=ctx.t("chat.log_past_day"))
    day = ctx.now.date()
    dish_hint = dish_hint or {}
    dish_mains = {c for code in dish_hint.values() for c in ctx.catalog_full.dishes[code].main}
    matches = list(matches)
    for code in dict.fromkeys(dish_hint.values()):  # phần ăn kèm (cơm của cơm tấm, rau sống của bún chả…)
        for side in ctx.catalog_full.dishes[code].log_sides:
            if all(side["food_code"] != x.food_code for x in matches):
                matches.append(FoodMatch(food_code=side["food_code"], alias=code, start=0, end=0,
                                         qty_value=side["grams"], qty_unit="g"))
                dish_mains.add(side["food_code"])
    slot = parsed.slot or _past_slot(ctx)
    items: list[dict] = []
    shown: list[str] = []
    refused: list[str] = []
    for m in matches[:6]:
        full = ctx.catalog_full.food(m.food_code) if m.food_code in ctx.catalog_full.foods else None
        f = ctx.catalog.foods.get(m.food_code)
        if f is None:
            if full is not None:
                refused.append(ctx.t("chat.refusal", food=ctx.inline(name_of(full, ctx.lang)),
                                     reason=reason_msg(exclusion_reason(full, ctx.allergies, ctx.diets))))
            continue
        g = min(_log_grams(m, f, parsed, len(matches) == 1), 3000.0)
        s = "snack" if f.category == "snack" else slot
        items.append({"slot": s, "food_code": f.code, "grams": g,
                      "source": "estimate" if f.code in dish_mains else "chat"})
        est = f" ({ctx.t('chat.estimate_short')})" if f.code in dish_mains else ""
        shown.append(f"{int(g)} g {ctx.inline(name_of(f, ctx.lang))}{est}")
    for r in composites[:2]:
        bad = [c for c, _ in r.components if c not in ctx.catalog.foods]
        if bad:
            f = ctx.catalog_full.food(bad[0])
            refused.append(ctx.t("chat.refusal_component", food=r.mention, component=ctx.inline(name_of(f, ctx.lang)),
                                 reason=reason_msg(exclusion_reason(f, ctx.allergies, ctx.diets))))
            continue
        items += [{"slot": slot, "food_code": c, "grams": float(g), "source": "ai_estimate"} for c, g in r.components]
        shown.append(f"{r.mention} ({ctx.t('chat.ai_estimate_short')})")
    if not items:
        if refused:
            return ChatReply(kind="refusal", text=" ".join(refused))
        what = ctx.t("chat.unknown_named", names=", ".join(unknown)) if unknown else ctx.t("chat.unknown_any")
        return ChatReply(kind="need_label", unknown_mentions=unknown, text=ctx.t("chat.need_label", what=what))
    text = " ".join([ctx.t("chat.log_confirm", slot=ctx.slot_name(slot).lower(), items=", ".join(shown)), *refused])
    return ChatReply(kind="proposal", text=text, proposals=[
        Proposal(key="log", day=day, label=ctx.t("chat.log_label"), intake=items),
        Proposal(key="rebalance", day=day, label=ctx.t("chat.rebalance_label"),
                 plan=ctx.rebalance_preview(items) if ctx.rebalance_preview else None),
    ])


def _picked(mention: str, code: str, ctx: ChatContext) -> Resolution | None:
    """Lựa chọn của người dùng sau "clarify" ("food:x" | "dish:y"); mã phải có trong catalog."""
    kind, _, c = code.partition(":")
    if kind == "food" and c in ctx.catalog_full.foods:
        return Resolution(mention=mention, kind="ingredient", food_code=c)
    if kind == "dish" and c in ctx.catalog_full.dishes:
        return Resolution(mention=mention, kind="dish", dish_code=c)
    return None


def _option_name(code: str, ctx: ChatContext) -> str:
    kind, _, c = code.partition(":")
    obj = ctx.catalog_full.dishes[c] if kind == "dish" else ctx.catalog_full.food(c)
    return name_of(obj, ctx.lang)


def _dislike(matches: list[FoodMatch], ctx: ChatContext, unknown: list[str]) -> ChatReply:
    """Không thích (ràng buộc mềm): đề xuất thêm vào danh sách, người dùng bấm Áp dụng mới lưu."""
    proposals = []
    for m in matches[:5]:
        f = (ctx.catalog if m.food_code in ctx.catalog.foods else ctx.catalog_full).food(m.food_code)
        name = name_of(f, ctx.lang)
        proposals.append(Proposal(key="preference", day=ctx.now.date(), label=ctx.t("chat.dislike_label", food=name),
                                  preference={"kind": "food", "code": f.code}))
    # chưa có trong dữ liệu (vd "hành" chỉ là gia vị): không bịa mã ⇒ lưu dạng chữ, công thức sẽ tránh từ này
    for label in [u.strip()[:TEXT_DISLIKE_MAX] for u in unknown if u.strip()][:3]:
        proposals.append(Proposal(key="preference", day=ctx.now.date(),
                                  label=ctx.t("chat.dislike_text_label", food=label),
                                  preference={"kind": "text", "code": label}))
    if not proposals:
        return ChatReply(kind="info", text=ctx.t("chat.dislike_none"))
    return ChatReply(kind="proposal", text=ctx.t("chat.dislike_confirm"), proposals=proposals)


def _day_name(day: date, ctx: ChatContext) -> str:
    delta = (day - ctx.now.date()).days
    if delta in (0, 1):
        return ctx.t("chat.day.today" if delta == 0 else "chat.day.tomorrow")
    return ctx.t("chat.day.date", date=day.strftime(ctx.t("chat.date_fmt")))


def _totals_line(plan: DayPlan, target: float, ctx: ChatContext) -> str:
    t = plan.totals
    return ctx.t("chat.totals", kcal=kcal(t.get("energy_kcal", 0)), target=kcal(target),
                 protein=round(t.get("protein_g", 0)), carb=round(t.get("carb_g", 0)), fat=round(t.get("fat_g", 0)))


def _shortfall_lines(plan: DayPlan, ctx: ChatContext) -> list[str]:
    out = []
    for d in plan.deviations:
        if d.within:
            continue
        what = Msg(f"nutrient.{d.code}")
        if d.actual < d.target:
            sugg = next((s for s in plan.suggestions if s.nutrient == d.code), None)
            foods = ", ".join(ctx.inline(ctx.food_name(c)) for c in sugg.food_codes) if sugg else ""
            add = ctx.t("chat.short.add", foods=foods) if sugg else ""
            out.append(ctx.t("chat.short.below", what=what, pct=round(abs(d.pct) * 100), add=add))
        else:
            out.append(ctx.t("chat.short.above", what=what, pct=round(d.pct * 100)))
    return out
