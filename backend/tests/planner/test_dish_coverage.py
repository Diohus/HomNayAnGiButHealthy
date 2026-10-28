"""Vòng 8 N0a: mọi món trong catalog, bắt buộc ở MỖI bữa nó được phép, phải xếp được vào thực đơn (hồ sơ chuẩn).
Chặn loại lỗi dữ liệu như "bún chả/phở bò không xếp được" (bữa của món ⊄ bữa của nguyên liệu chính)."""

from datetime import date

import pytest

from app.nutrition import HealthProfileIn, compute_needs
from app.planner import PlanRequest, Requirement, solve_day
from app.services.targets import planner_targets

DAY = date(2026, 10, 21)
PROFILE = HealthProfileIn(sex="female", age=30, height_cm=160, weight_kg=55, activity_level="moderate")


def _cases():
    from app.foods import load_seed_catalog

    cat = load_seed_catalog()
    slots = compute_needs(PROFILE).meal_slots
    return [(d.code, s) for d in sorted(cat.dishes.values(), key=lambda d: d.code) for s in slots if d.allowed_in(s)]


def test_dish_slots_subset_of_main_slots(catalog):
    for d in catalog.dishes.values():
        for m in d.main:
            assert set(d.slots) <= set(catalog.food(m).slots), (d.code, m)


@pytest.mark.slow
@pytest.mark.parametrize(("dish", "slot"), _cases())
def test_every_dish_solvable_in_every_allowed_slot(catalog, dish, slot):
    n = compute_needs(PROFILE)
    plan = solve_day(PlanRequest(day=DAY, slots=n.meal_slots, targets=planner_targets(n, None),
                                 required=[Requirement(kind="dish", code=dish, slot=slot)]), catalog)
    assert plan.status != "conflict", (dish, slot, plan.conflicts)
    assert any(m.slot == slot and m.dish_code == dish for m in plan.meals), (dish, slot)
