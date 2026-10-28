"""(c)+(d) Bộ sinh thực đơn ILP — test độc lập, không DB, không LLM."""

from datetime import date, timedelta

import pytest

from app.foods.catalog import FoodCatalog
from app.nutrition import HealthProfileIn, compute_needs
from app.planner import (
    LockedItem,
    MealStructure,
    PlanRequest,
    Requirement,
    forbidden_mains,
    max_consecutive_run,
    solve_day,
)
from app.services.targets import planner_targets

D0 = date(2026, 10, 21)
MACROS = ("energy_kcal", "protein_g", "carb_g", "fat_g")
PROFILES = [
    dict(sex="male", age=30, height_cm=172, weight_kg=70, activity_level="moderate"),
    dict(sex="female", age=45, height_cm=158, weight_kg=62, activity_level="sedentary", goal="lose",
         conditions=["diabetes_t2"]),
    dict(sex="male", age=25, height_cm=180, weight_kg=80, activity_level="very_active", goal="gain_muscle",
         diets=["vegan"]),
    dict(sex="female", age=60, height_cm=150, weight_kg=48, activity_level="light", allergies=["fish", "shellfish"],
         diets=["halal"]),
]


def setup(profile, catalog):
    p = HealthProfileIn(**profile)
    n = compute_needs(p)
    return p, n, catalog.filtered(p.allergies, p.diets)


def request(n, day=D0, **kw):
    return PlanRequest(day=day, slots=n.meal_slots, targets=planner_targets(n), **kw)


def macro_ok(plan, tol=0.05):
    return all(abs(d.pct) <= tol + 1e-9 for d in plan.deviations if d.code in MACROS)


@pytest.mark.parametrize("profile", PROFILES)
def test_macros_within_5pct_and_allergens_never_used(profile, catalog):
    p, n, cat = setup(profile, catalog)
    plan = solve_day(request(n, prefer_low_gi=bool(p.conditions)), cat)
    assert plan.status == "ok", plan.deviations
    assert macro_ok(plan)
    assert [m.slot for m in plan.meals] == n.meal_slots
    for m in plan.meals:
        assert m.dish_code is not None
        for it in m.items:
            assert it.food_code in cat.foods  # không bao giờ có nguyên liệu bị loại


def test_shared_ingredients_allowed_and_no_same_main_twice(catalog):
    _, n, cat = setup(PROFILES[0], catalog)
    plan = solve_day(request(n), cat)
    dishes = [m.dish_code for m in plan.meals]
    assert len(dishes) == len(set(dishes))


def test_rotation_over_seven_days(catalog):
    _, n, cat = setup(PROFILES[0], catalog)
    mains: dict[date, set[str]] = {}
    for i in range(7):
        day = D0 + timedelta(days=i)
        plan = solve_day(request(n, day=day, forbidden_dishes=forbidden_mains(day, mains, cat.dishes)), cat)
        mains[day] = plan.main_dishes()
    assert max_consecutive_run(mains) <= 3


def test_rotation_forbids_4th_day_both_directions():
    d = D0
    mains = {d - timedelta(days=2): {"x"}, d - timedelta(days=1): {"x"}, d + timedelta(days=1): {"x"}}
    assert forbidden_mains(d, mains, ["x", "y"]) == {"x"}
    assert forbidden_mains(d, {d - timedelta(days=1): {"x"}, d - timedelta(days=2): {"x"}}, ["x"]) == set()


def test_pantry_is_hard_constraint(catalog):
    _, n, cat = setup(PROFILES[0], catalog)
    plan = solve_day(request(n, locked=[LockedItem(food_code="beef_lean", grams=180, origin="pantry")]), cat)
    used = sum(it.grams for m in plan.meals for it in m.items if it.food_code == "beef_lean" and it.origin == "pantry")
    assert used == 180
    assert macro_ok(plan)


def test_locked_allergen_is_reported_and_never_used(catalog):
    _, n, cat = setup({**PROFILES[0], "allergies": ["shellfish"]}, catalog)
    plan = solve_day(request(n, locked=[LockedItem(food_code="shrimp", grams=100, origin="pantry")]), cat)
    assert "FORBIDDEN_LOCKED_ITEM:shrimp" in plan.conflicts
    assert all(it.food_code != "shrimp" for m in plan.meals for it in m.items)


def test_locked_exceeding_energy_detected(catalog):
    _, n, cat = setup(PROFILES[1], catalog)
    plan = solve_day(request(n, locked=[LockedItem(food_code="peanuts", grams=400, origin="pantry")]), cat)
    assert "LOCKED_EXCEEDS_ENERGY" in plan.conflicts
    assert plan.status == "conflict" and plan.meals  # vẫn trả phương án, không rỗng


def test_insufficient_database_returns_best_effort_with_shortfalls(catalog):
    _, n, _ = setup(PROFILES[0], catalog)
    tiny = FoodCatalog([catalog.food("cucumber"), catalog.food("lettuce"), catalog.food("white_rice")], [])
    plan = solve_day(request(n), tiny)
    assert plan.status == "partial"
    assert plan.meals and "protein_g" in plan.shortfalls
    assert any(d.code == "protein_g" and not d.within for d in plan.deviations)
    assert any(s.nutrient == "protein_g" for s in plan.suggestions)  # báo rõ thiếu gì + gợi ý


def test_shortfall_suggestions_never_snacks(catalog):
    _, n, cat = setup(PROFILES[0], catalog)
    plan = solve_day(request(n), cat)
    for s in plan.suggestions:
        assert all(cat.food(c).category != "snack" for c in s.food_codes)


def test_required_dish_in_slot(catalog):
    _, n, cat = setup(PROFILES[0], catalog)
    plan = solve_day(request(n, required=[Requirement(kind="dish", code="ga_ap_chao", slot="dinner")]), cat)
    dinner = next(m for m in plan.meals if m.slot == "dinner")
    assert dinner.dish_code == "ga_ap_chao"
    chicken = sum(i.grams for i in dinner.items if i.food_code == "chicken_breast")
    assert chicken >= 100  # món "xoay quanh" gà phải có lượng gà đáng kể
    assert macro_ok(plan)


def test_required_dish_forbidden_by_rotation_reported(catalog):
    _, n, cat = setup(PROFILES[0], catalog)
    plan = solve_day(request(n, forbidden_dishes={"ga_ap_chao"},
                             required=[Requirement(kind="dish", code="ga_ap_chao", slot="dinner")]), cat)
    assert "REQUIRED_DISH_ROTATION:ga_ap_chao" in plan.conflicts
    assert "ga_ap_chao" not in plan.main_dishes()


def test_snack_absorbed_into_day(catalog):
    _, n, cat = setup(PROFILES[0], catalog)
    plan = solve_day(request(n, locked=[LockedItem(food_code="ice_cream_vanilla", grams=132, slot="snack",
                                                   origin="snack")]), cat)
    assert plan.meals[-1].slot == "snack"
    assert macro_ok(plan)


def test_rebalance_keeps_structure_and_target(catalog):
    _, n, cat = setup(PROFILES[0], catalog)
    base = solve_day(request(n), cat)
    structure = {m.slot: MealStructure(dish_code=m.dish_code, food_codes=[i.food_code for i in m.items])
                 for m in base.meals}
    lunch = next(m for m in base.meals if m.slot == "lunch")
    # +50 g nguyên liệu ít béo nhất của bữa (thịt ba chỉ ~53 % béo: +50 g tự nó đã vượt mục tiêu chất béo)
    main = min(lunch.items, key=lambda i: cat.food(i.food_code).per_100g.get("fat_g") or 0)
    locked = [LockedItem(food_code=main.food_code, grams=main.grams + 50, slot="lunch")]
    st = {k: MealStructure(dish_code=v.dish_code, food_codes=[c for c in v.food_codes
                                                             if not (k == "lunch" and c == main.food_code)])
          for k, v in structure.items()}
    plan = solve_day(request(n, locked=locked, structure=st), cat)
    assert [m.dish_code for m in plan.meals] == [m.dish_code for m in base.meals]
    assert macro_ok(plan)


def test_deterministic(catalog):
    _, n, cat = setup(PROFILES[0], catalog)
    a = solve_day(request(n), cat)
    b = solve_day(request(n), cat)
    assert a.model_dump() == b.model_dump()
