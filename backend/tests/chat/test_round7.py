"""Vòng 7: món gọi đúng tên ⇒ dish (không tách nguyên liệu), resolver ưu tiên dish, từ địa phương, M2 đa dạng,
M3 không cảnh báo NO_MAIN_DISH thừa, xem trước khi cân lại."""

from datetime import date

from app.chat.engine import handle
from app.foods import resolve as RS
from app.foods.matching import find_dishes, find_foods
from app.nutrition import HealthProfileIn, compute_needs
from app.planner import LockedItem, PlanRequest, solve_day
from app.services.targets import planner_targets
from tests.chat.conftest import ask
from tests.chat.test_resolve import FakeLLM, parsed, with_llm

DAY = date(2026, 10, 21)


def codes(text, catalog):
    return [m.food_code for m in find_foods(text, catalog)]


def test_regional_and_unaccented_aliases(catalog):
    assert codes("cho tôi ít trái thơm", catalog) == ["pineapple"]
    assert codes("củ sắn", catalog) == ["jicama"] and codes("cu dau", catalog) == ["jicama"]
    assert codes("thịt ba rọi", catalog) == ["pork_belly"]
    # không dấu: "toi" là "tôi" (không phải tỏi), "cua" là "của", "buoi" là "buổi", "ngo" vẫn là bắp
    assert codes("toi muon an thit lon", catalog) == ["pork_tenderloin"]
    assert codes("bua trua cua toi", catalog) == [] and codes("buoi sang an ngo", catalog) == ["corn"]
    assert codes("món này thơm quá", catalog) == []  # "thơm" trơn không phải dứa


def test_find_dishes_longest_name(catalog):
    assert [c for c, _, _ in find_dishes("tôi vừa ăn 1 tô phở bò", catalog)] == ["pho_bo"]
    assert [c for c, _, _ in find_dishes("tối nay ăn canh chua cá lóc nha", catalog)] == ["canh_chua_ca_loc"]
    assert [c for c, _, _ in find_dishes("pho bo", catalog)] == ["pho_bo"]


def test_named_dish_used_without_llm(make_ctx):
    ctx, _ = make_ctx()
    r = ask(ctx, "tối nay ăn canh chua cá lóc")
    assert r.kind == "proposal"
    dinner = next(m for m in r.proposals[0].plan.meals if m.slot == "dinner")
    assert dinner.dish_code == "canh_chua_ca_loc"


def test_log_named_dish_logs_all_mains(make_ctx):
    ctx, _ = make_ctx()
    r = ask(ctx, "tôi vừa ăn 1 tô phở bò")
    assert r.kind == "proposal" and r.proposals[0].key == "log"
    items = r.proposals[0].intake
    # vòng 8 N0d: nguyên liệu chính + phần ăn kèm khai báo trong log_sides (giá thường gặp, nguồn "estimate")
    assert {e["food_code"] for e in items} == {"fresh_rice_noodles", "beef_sirloin", "bean_sprouts"}
    assert {e["source"] for e in items} == {"estimate"}


def test_resolver_prefers_catalog_dish_over_composite(make_ctx):
    RS.cache.clear()
    fake = FakeLLM([{"mention": "cơm tấm", "kind": "composite", "components": [
        {"food_code": "white_rice", "grams": 80}, {"food_code": "pork_ribs", "grams": 120}]}])
    ctx, _ = make_ctx()
    r = handle("trưa nay ăn cơm tấm", parsed(["cơm tấm"], slot="lunch"), with_llm(ctx, fake))
    lunch = next(m for m in r.proposals[0].plan.meals if m.slot == "lunch")
    assert lunch.dish_code == "com_tam_suon" and not any(i.origin == "ai_estimate" for i in lunch.items)


# ---------- M2 ----------
def _req(n, **kw):
    return PlanRequest(day=DAY, slots=n.meal_slots, targets=planner_targets(n, None), **kw)


def test_eggs_at_most_one_meal(catalog):
    n = compute_needs(HealthProfileIn(sex="female", age=30, height_cm=160, weight_kg=55, activity_level="moderate"))
    # trứng đã khóa ở bữa sáng ⇒ bữa khác tránh trứng (gà và vịt)
    plan = solve_day(_req(n, locked=[LockedItem(food_code="egg", grams=100, slot="breakfast")]), catalog)
    egg_meals = [m.slot for m in plan.meals if any("egg" in catalog.food(i.food_code).tags for i in m.items)]
    assert egg_meals == ["breakfast"]


def test_recent_protein_penalized(catalog):
    n = compute_needs(HealthProfileIn(sex="female", age=30, height_cm=160, weight_kg=55, activity_level="moderate"))
    base = solve_day(_req(n), catalog)
    prot = {i.food_code for m in base.meals for i in m.items if catalog.food(i.food_code).category == "protein"}
    again = solve_day(_req(n, recent_foods={c: 2 for c in prot}), catalog)
    prot2 = {i.food_code for m in again.meals for i in m.items if catalog.food(i.food_code).category == "protein"}
    assert not prot & prot2


def test_seven_day_diversity(client, auth, catalog):
    days = client.post("/api/menu/generate", json={"start": DAY.isoformat(), "days": 7}, headers=auth).json()
    dishes, proteins = set(), set()
    for d in days:
        egg_meals = 0
        for m in d["plan"]["meals"]:
            if m["slot"] == "snack":
                continue
            dishes |= {m["dish_code"]} - {None}
            proteins |= {i["food_code"] for i in m["items"] if catalog.food(i["food_code"]).category == "protein"}
            egg_meals += any("egg" in catalog.food(i["food_code"]).tags for i in m["items"])
        assert egg_meals <= 1, d["day"]
        assert all(x["within"] for x in d["plan"]["deviations"] if x["code"] in ("energy_kcal", "protein_g"))
    assert len(dishes) >= 5 and len(proteins) >= 4


# ---------- M3 ----------
def test_no_main_dish_warning_not_for_eaten_meals(client, auth):
    client.post("/api/menu/generate", json={"start": DAY.isoformat()}, headers=auth)
    client.post(f"/api/menu/{DAY}/meals/breakfast/eaten", json={"eaten": True}, headers=auth)
    client.post("/api/intake", json={"day": DAY.isoformat(), "slot": "snack", "food_code": "banana", "grams": 120},
                headers=auth)
    r = client.post(f"/api/menu/{DAY}/rebalance", headers=auth).json()
    assert not any(w.startswith("NO_MAIN_DISH") for w in r["plan"]["warnings"])


def test_solver_no_main_dish_skips_frozen(catalog):
    n = compute_needs(HealthProfileIn(sex="female", age=30, height_cm=160, weight_kg=55, activity_level="moderate"))
    plan = solve_day(_req(n, frozen_slots={"breakfast"},
                          locked=[LockedItem(food_code="oats", grams=60, slot="breakfast", origin="frozen")]), catalog)
    assert "NO_MAIN_DISH:breakfast" not in plan.warnings


def test_chat_rebalance_proposal_has_preview(make_ctx):
    ctx, _ = make_ctx()
    seen = []
    ctx.rebalance_preview = lambda items: seen.append(items) or ctx.plan_fn(DAY, [], [], None, None)
    r = ask(ctx, "tôi vừa ăn 2 quả chuối")
    reb = next(p for p in r.proposals if p.key == "rebalance")
    assert reb.plan is not None and seen and seen[0][0]["food_code"] == "banana"


def test_chat_rebalance_preview_api(client, auth):
    from datetime import datetime

    today = datetime.now().date()
    client.post("/api/menu/generate", json={"start": today.isoformat()}, headers=auth)
    r = client.post("/api/chat", json={"message": "tôi vừa ăn 2 quả chuối"}, headers=auth).json()
    reb = next(p for p in r["proposals"] if p["key"] == "rebalance")
    assert reb["plan"] is not None and reb["plan"]["meals"]
    before = client.get(f"/api/menu?start={today}", headers=auth).json()[0]
    assert before["version"] == 1  # xem trước không lưu gì
