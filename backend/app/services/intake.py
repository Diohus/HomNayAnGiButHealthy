"""Nhật ký "đã ăn" và cân lại các bữa CHƯA ăn theo thực tế.

- Đánh dấu bữa đã ăn ⇒ chép item kế hoạch vào nhật ký (source="plan").
- Ăn ngoài kế hoạch ⇒ bản ghi riêng (manual | chat | ai_estimate); vẫn tôn trọng dị ứng/chế độ ăn (ràng buộc cứng).
- Cân lại: bữa đã ăn giữ nguyên (theo nhật ký), đồ ngoài kế hoạch khóa như ăn vặt; mỗi bữa còn lại giữ ≥ 50 %
  phần năng lượng của nó (không bỏ bữa); đã bị gắn cờ rối loạn ăn uống thì KHÔNG cắt giảm; vượt mục tiêu thì
  các bữa còn lại về mức sàn và báo, KHÔNG tự bù sang ngày sau.
"""

import uuid
from collections import defaultdict
from datetime import date

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.core.i18n import names
from app.db import foods_repo
from app.db import models as M
from app.foods.catalog import NUTRIENT_CODES
from app.foods.restrictions import exclusion_reason, reason_msg
from app.nutrition.compensation import MEAL_FLOOR_SHARE
from app.planner import DayPlan, LockedItem, MealPlan, PlanRequest, forbidden_mains, solve_day
from app.planner.solver import MEAL_SHARE, finalize, totals_of
from app.services import menu as MS
from app.services import profile as P

SLOTS = ("breakfast", "lunch", "dinner", "snack")
SOURCES = ("plan", "chat", "manual", "ai_estimate")


def entries(s: Session, user_id: uuid.UUID, day: date) -> list[M.IntakeEntry]:
    return list(s.scalars(select(M.IntakeEntry).where(M.IntakeEntry.user_id == user_id, M.IntakeEntry.day == day)
                          .order_by(M.IntakeEntry.id)))


def eaten_slots(rows: list[M.IntakeEntry]) -> list[str]:
    return [sl for sl in SLOTS if any(r.slot == sl and r.source == "plan" for r in rows)]


def summary(s: Session, user_id: uuid.UUID, day: date, catalog) -> dict:
    rows = entries(s, user_id, day)
    known = [r for r in rows if r.food_code in catalog.foods]
    totals = {c: 0.0 for c in NUTRIENT_CODES}
    for r in known:
        f = catalog.food(r.food_code)
        for c in NUTRIENT_CODES:
            totals[c] += f.nutrient(c, r.grams)
    return {"entries": [{"id": r.id, "slot": r.slot, "food_code": r.food_code, "grams": r.grams, "source": r.source}
                        for r in rows],
            "totals": totals, "eaten_slots": eaten_slots(rows)}


def mark_eaten(s: Session, user_id: uuid.UUID, day: date, slot: str, eaten: bool) -> None:
    md = MS.get_day(s, user_id, day)
    meal = next((m for m in md.meals if m.slot == slot and m.active), None) if md else None
    if meal is None:
        raise AppError(404, "MEAL_NOT_FOUND")
    s.execute(delete(M.IntakeEntry).where(M.IntakeEntry.user_id == user_id, M.IntakeEntry.day == day,
                                          M.IntakeEntry.slot == slot, M.IntakeEntry.source == "plan"))
    if eaten:
        for it in meal.items:
            s.add(M.IntakeEntry(user_id=user_id, day=day, slot=slot, food_code=it.ingredient_code, grams=it.grams,
                                source="plan"))
    s.commit()


def add_entry(s: Session, user_id: uuid.UUID, day: date, slot: str, food_code: str, grams: float,
              source: str = "manual", commit: bool = True) -> int:
    if slot not in SLOTS:
        raise AppError(422, "SLOT_INVALID")
    if not (1 <= grams <= 3000):
        raise AppError(422, "GRAMS_RANGE")
    ing = foods_repo.visible_ingredient(s, user_id, food_code)
    if ing is None:
        raise AppError(404, "FOOD_NOT_FOUND")
    p = P.require_profile(s, user_id)
    _, allowed = MS.catalogs(s, user_id, p)
    if food_code not in allowed.foods:  # dị ứng/chế độ ăn là ràng buộc cứng, kể cả khi ghi nhật ký
        reason = exclusion_reason(ing, p.allergies, p.diets) or ""
        raise AppError(422, "ALLERGEN_CONFLICT", key="error.ALLERGEN_CONFLICT.item",
                       params={"food": names(ing), "reason": reason_msg(reason)}, reason=reason)
    row = M.IntakeEntry(user_id=user_id, day=day, slot=slot, food_code=food_code, grams=grams,
                        source=source if source in SOURCES else "manual")
    s.add(row)
    s.flush()
    if commit:
        s.commit()
    return row.id


def delete_entry(s: Session, user_id: uuid.UUID, entry_id: int) -> None:
    row = s.get(M.IntakeEntry, entry_id)
    if row is None or row.user_id != user_id:
        raise AppError(404, "INTAKE_NOT_FOUND")
    s.delete(row)
    s.commit()


def rebalance(s: Session, user_id: uuid.UUID, day: date) -> DayPlan:
    c = MS.Ctx(s, user_id)
    md = MS.get_day(s, user_id, day)
    if md is None:
        raise AppError(404, "MENU_NOT_FOUND")
    rows = entries(s, user_id, day)
    eaten = set(eaten_slots(rows))
    current = MS.to_plan(md, c.catalog, c.tol)
    main_slots = [m.slot for m in current.meals if m.slot != "snack"]
    remaining = [sl for sl in main_slots if sl not in eaten]
    if not remaining:
        raise AppError(409, "NOTHING_TO_REBALANCE")
    targets = MS.targets_for(s, user_id, c.needs, day)
    target = next(t.value for t in targets if t.code == "energy_kcal")

    # Bữa đã ăn: khóa theo nhật ký thực tế. Ngoài kế hoạch (và bữa ăn vặt đã đánh dấu): khóa như ăn vặt.
    locked = [LockedItem(food_code=r.food_code, grams=r.grams, slot=r.slot, origin="frozen")
              for r in rows if r.source == "plan" and r.slot in eaten and r.slot != "snack"]
    off = [r for r in rows if r.source != "plan" or r.slot == "snack"]
    locked += [LockedItem(food_code=r.food_code, grams=r.grams, slot="snack", origin="snack") for r in off]
    snack_meal = [m for m in current.meals if m.slot == "snack"]
    if "snack" not in eaten:  # đồ ăn vặt đã lên kế hoạch nhưng chưa ghi ăn: vẫn tính
        locked += [LockedItem(food_code=i.food_code, grams=i.grams, slot="snack", origin="snack")
                   for m in snack_meal for i in m.items]
    # đồ có sẵn chưa dùng ở bữa đã ăn ⇒ phân bổ vào các bữa còn lại
    used = defaultdict(float)
    for m in current.meals:
        if m.slot in eaten:
            for i in m.items:
                if i.origin == "pantry":
                    used[i.food_code] += i.grams
    for pi in s.scalars(select(M.PantryItem).where(M.PantryItem.user_id == user_id, M.PantryItem.day == day)):
        left = pi.grams - used[pi.ingredient_code]
        if left > 0:
            locked.append(LockedItem(food_code=pi.ingredient_code, grams=left, slot=None, origin="pantry"))
            used[pi.ingredient_code] = max(0.0, used[pi.ingredient_code] - pi.grams)

    known = [x for x in locked if x.food_code in c.catalog.foods]
    fixed_kcal = sum(c.catalog.food(x.food_code).nutrient("energy_kcal", x.grams) for x in known)
    planned_rest = sum(m.totals.get("energy_kcal", 0.0) for m in current.meals if m.slot in remaining)
    # Guardrail: rebalance sẽ CẮT phần còn lại ⇒ không làm khi đã có tín hiệu rối loạn ăn uống
    if fixed_kcal + planned_rest > target * (1 + c.tol) and P.ed_status(s, user_id).flagged:
        raise AppError(409, "ED_SUPPORT")
    shares = MEAL_SHARE.get(len(main_slots), {})
    eaten_kcal = sum(c.catalog.food(x.food_code).nutrient("energy_kcal", x.grams) for x in known
                     if x.slot in eaten and x.slot != "snack")
    floor_rest = MEAL_FLOOR_SHARE * target * sum(shares.get(sl, 1 / len(main_slots)) for sl in remaining)
    mains = MS.mains_by_date(s, user_id, day)
    forbidden = forbidden_mains(day, mains, c.catalog.dishes) | {m.dish_code for m in current.meals
                                                                 if m.slot in eaten and m.dish_code}
    slot_floor = {sl: MEAL_FLOOR_SHARE * target * shares.get(sl, 1 / len(main_slots)) for sl in remaining}
    req = c.request(day, targets, locked, forbidden, recent_dishes=c._recent(day, mains),
                    frozen_slots=set(main_slots) - set(remaining), min_meal_energy_kcal=eaten_kcal + floor_rest,
                    min_slot_energy_kcal=slot_floor)
    plan = solve_day(req, c.catalog)
    new = {m.slot: m for m in plan.meals if m.slot in remaining}
    meals = [new.get(m.slot, m) if m.slot in remaining else m for m in current.meals]
    warnings = list(plan.warnings)
    # Báo cáo so mục tiêu gồm cả đồ ngoài kế hoạch (bữa ăn vặt giả, không lưu)
    off_items = [MealPlan(slot="snack", dish_code=None, items=[], totals={})]
    off_items[0].items = [i for i in (MS.PlanItem(food_code=r.food_code, grams=r.grams, locked=True, origin="intake")
                                      for r in off) if i.food_code in c.catalog.foods]
    off_items[0].totals = totals_of(off_items[0].items, c.catalog)
    report = finalize(PlanRequest(day=day, slots=c.needs.meal_slots, targets=targets, tolerance=c.tol), c.catalog,
                      [*meals, *off_items], plan.conflicts, warnings)
    total = report.totals.get("energy_kcal", 0.0)
    if total > target * (1 + c.tol):
        report.warnings.append(f"OVER_TARGET:{round((total - target) / 10) * 10}")
    report.meals = meals
    MS.save_plan(s, user_id, report, targets)
    s.commit()
    return report
