"""Vòng 5: K2 đổi một bữa, K3 món/nguyên liệu không thích (API + planner), K0 muối ⇒ natri, chat `resolved`."""

from datetime import date, timedelta

import pytest

from app.core import ratelimit as RL
from app.planner import PlanRequest, Requirement, max_consecutive_run, solve_day
from app.services.targets import planner_targets
from tests.conftest import BASE_PROFILE, register

DAY = date(2026, 10, 21)
EN = {"Accept-Language": "en"}


def gen(client, h, day=DAY, days=1):
    r = client.post("/api/menu/generate", json={"start": day.isoformat(), "days": days}, headers=h)
    assert r.status_code == 200, r.text
    return r.json()


def meals(menu):
    return {m["slot"]: m for m in menu["plan"]["meals"]}


# ---------- K2: đổi một bữa ----------
def test_swap_changes_only_that_meal(client, auth):
    before = meals(gen(client, auth)[0])
    r = client.post(f"/api/menu/{DAY}/meals/lunch/swap", headers=auth)
    assert r.status_code == 200, r.text
    after = meals(r.json())
    assert after["lunch"]["dish_code"] and after["lunch"]["dish_code"] != before["lunch"]["dish_code"]
    for slot in ("breakfast", "dinner"):
        assert after[slot]["dish_code"] == before[slot]["dish_code"]
        assert {i["food_code"]: i["grams"] for i in after[slot]["items"]} == \
               {i["food_code"]: i["grams"] for i in before[slot]["items"]}
    assert after["lunch"]["dish_code"] not in {after["breakfast"]["dish_code"], after["dinner"]["dish_code"]}
    assert r.json()["version"] == 2
    energy = next(d for d in r.json()["plan"]["deviations"] if d["code"] == "energy_kcal")
    assert abs(energy["pct"]) <= 0.05 + 1e-9  # tổng ngày vẫn nhắm ±5%


def test_swap_clears_only_that_recipe(client, auth):
    gen(client, auth)
    client.post(f"/api/menu/{DAY}/meals/lunch/recipe", headers=auth)
    client.post(f"/api/menu/{DAY}/meals/dinner/recipe", headers=auth)
    m = client.post(f"/api/menu/{DAY}/meals/lunch/swap", headers=auth).json()
    assert set(m["recipes"]) == {"dinner"}


def test_swap_respects_allergy_and_rotation(client):
    h = register(client, profile={**BASE_PROFILE, "allergies": ["fish", "shellfish"]})
    gen(client, h, days=4)
    m = client.post(f"/api/menu/{DAY + timedelta(days=3)}/meals/lunch/swap", headers=h).json()
    lunch = meals(m)["lunch"]
    assert not {"salmon", "tuna", "catfish", "tilapia", "mackerel", "shrimp", "squid"} & {
        i["food_code"] for i in lunch["items"]}
    days = client.get(f"/api/menu?start={DAY}&days=4", headers=h).json()
    run = max_consecutive_run({date.fromisoformat(d["day"]): {x["dish_code"] for x in d["plan"]["meals"]
                                                              if x["dish_code"]} for d in days})
    assert run <= 3


def test_swap_keeps_pantry_total(client, auth):
    client.post("/api/pantry", json={"day": DAY.isoformat(), "food_code": "egg", "grams": 100}, headers=auth)
    gen(client, auth)
    m = client.post(f"/api/menu/{DAY}/meals/lunch/swap", headers=auth).json()
    eggs = sum(i["grams"] for x in m["plan"]["meals"] for i in x["items"] if i["food_code"] == "egg"
               and i["origin"] == "pantry")
    assert eggs == pytest.approx(100)


def test_swap_no_alternative(client):
    h = register(client, profile={**BASE_PROFILE, "diets": ["vegan"]})
    menu = meals(gen(client, h)[0])
    others = {d["code"] for d in client.get("/api/dishes", headers=h).json()} - {
        menu["lunch"]["dish_code"], menu["dinner"]["dish_code"]}
    for code in others:  # không thích mọi món còn lại ⇒ không còn lựa chọn
        client.post("/api/preferences/dislikes", json={"kind": "dish", "code": code}, headers=h)
    r = client.post(f"/api/menu/{DAY}/meals/lunch/swap", headers={**h, **EN})
    assert r.status_code == 409 and r.json()["code"] == "NO_ALTERNATIVE" and "No other suitable dish" in r.json()["message"]


def test_swap_errors_and_rate_limit(client, auth):
    assert client.post(f"/api/menu/{DAY}/meals/lunch/swap", headers=auth).json()["code"] == "MENU_NOT_FOUND"
    gen(client, auth)
    assert client.post(f"/api/menu/{DAY}/meals/snack/swap", headers=auth).json()["code"] == "MEAL_NOT_FOUND"
    for _ in range(RL.SWAP[0] - 1):
        client.post(f"/api/menu/{DAY}/meals/lunch/swap", headers=auth)
    assert client.post(f"/api/menu/{DAY}/meals/lunch/swap", headers=auth).status_code == 429


# ---------- K3: không thích ----------
def test_dislikes_crud(client, auth):
    r = client.post("/api/preferences/dislikes", json={"kind": "food", "code": "salmon"}, headers={**auth, **EN})
    assert r.status_code == 201 and r.json()["name"] == "Salmon"
    again = client.post("/api/preferences/dislikes", json={"kind": "food", "code": "salmon"}, headers=auth)
    assert again.json()["id"] == r.json()["id"]  # thêm trùng ⇒ giữ một
    client.post("/api/preferences/dislikes", json={"kind": "dish", "code": "bo_xao"}, headers=auth)
    rows = client.get("/api/preferences/dislikes", headers=auth).json()
    assert [(x["kind"], x["code"], x["name"]) for x in rows] == [("food", "salmon", "Cá hồi"), ("dish", "bo_xao", "Bò xào")]
    assert client.post("/api/preferences/dislikes", json={"kind": "food", "code": "unicorn"},
                       headers=auth).status_code == 404
    assert client.post("/api/preferences/dislikes", json={"kind": "drink", "code": "cola"},
                       headers=auth).status_code == 422
    other = register(client, email="o@example.com")
    assert client.delete(f"/api/preferences/dislikes/{r.json()['id']}", headers=other).status_code == 404
    assert client.delete(f"/api/preferences/dislikes/{r.json()['id']}", headers=auth).status_code == 204
    assert len(client.get("/api/preferences/dislikes", headers=auth).json()) == 1


def test_cannot_dislike_other_users_custom_food(client, auth):
    body = {"name_vi": "Bánh riêng", "portion_g": 50,
            "per_100g": {"energy_kcal": 400, "protein_g": 5, "carb_g": 60, "fat_g": 15}}
    code = client.post("/api/foods/custom", json=body, headers=auth).json()["code"]
    other = register(client, email="o@example.com")
    assert client.post("/api/preferences/dislikes", json={"kind": "food", "code": code},
                       headers=other).status_code == 404
    assert client.post("/api/preferences/dislikes", json={"kind": "food", "code": code},
                       headers=auth).status_code == 201


def test_disliked_dish_avoided_when_regenerating(client, auth):
    first = meals(gen(client, auth)[0])
    disliked = {first[s]["dish_code"] for s in ("lunch", "dinner")}
    for code in disliked:
        client.post("/api/preferences/dislikes", json={"kind": "dish", "code": code}, headers=auth)
    again = meals(gen(client, auth)[0])
    assert not disliked & {again[s]["dish_code"] for s in ("lunch", "dinner")}


def test_planner_uses_disliked_only_when_forced(catalog):
    from app.nutrition import HealthProfileIn, compute_needs

    n = compute_needs(HealthProfileIn(**BASE_PROFILE))
    base = {"day": DAY, "slots": n.meal_slots, "targets": planner_targets(n, None)}
    plan = solve_day(PlanRequest(**base, disliked_dishes={"bo_xao"},
                                 required=[Requirement(kind="dish", code="bo_xao", slot="lunch")]), catalog)
    assert "USED_DISLIKED:bo_xao" in plan.warnings and plan.status != "conflict"
    free = solve_day(PlanRequest(**base, disliked_foods={"white_rice"}), catalog)
    assert "white_rice" not in {i.food_code for m in free.meals for i in m.items}


def test_dislikes_deleted_with_account(client, auth, engine):
    from sqlalchemy import func, select

    from app.db import models as M

    client.post("/api/preferences/dislikes", json={"kind": "food", "code": "salmon"}, headers=auth)
    client.delete("/api/me", headers=auth)
    with engine.connect() as c:
        assert c.execute(select(func.count()).select_from(M.FoodPreference)).scalar() == 0


def test_chat_dislike_proposal_apply(client, auth):
    r = client.post("/api/chat", json={"message": "tôi không thích cá hồi"}, headers=auth).json()
    assert r["kind"] == "proposal" and r["proposals"][0]["key"] == "preference"
    assert r["proposals"][0]["plan"] is None and r["proposals"][0]["preference"] == {"kind": "food", "code": "salmon"}
    a = client.post(f"/api/chat/proposals/{r['proposals'][0]['id']}/apply", headers=auth)
    assert a.status_code == 200 and a.json()["menu"] is None
    assert [x["code"] for x in client.get("/api/preferences/dislikes", headers=auth).json()] == ["salmon"]


def test_chat_allergy_statement_api(client, auth):
    r = client.post("/api/chat", json={"message": "tôi bị dị ứng tôm"}, headers=auth).json()
    assert r["kind"] == "allergy_redirect" and r["proposals"] == []
    assert client.get("/api/profile", headers=auth).json()["profile"]["allergies"] == []  # không tự sửa hồ sơ


def test_chat_resolved_param(client, auth, monkeypatch):
    # LLM tắt trong test: lựa chọn của người dùng vẫn được dùng (mã phải có trong catalog)
    from app.chat.schemas import ParsedIntent

    monkeypatch.setattr("app.services.chat.parse", lambda text, provider, retries, lang="vi", now=None: (ParsedIntent(
        intent="want_food", mentions=["thịt"], quantity_value=None, quantity_unit=None, slot=None, day=None,
        cheat_day=False), "llm"))
    r = client.post("/api/chat", json={"message": "tôi muốn ăn thịt", "resolved": {"thịt": "food:beef_lean"}},
                    headers=auth).json()
    assert r["kind"] == "proposal" and r["detected"][0]["food_code"] == "beef_lean"
    bad = client.post("/api/chat", json={"message": "x", "resolved": {str(i): "food:egg" for i in range(6)}},
                      headers=auth)
    assert bad.status_code == 422


# ---------- K0: muối ⇒ natri ----------
def test_extract_salt_converted_to_sodium(client, auth, monkeypatch):
    from tests.api.test_health_limits import FakeVision

    out = {"items": [{"field": "sodium_mg_max", "value": 5, "unit": "g_salt", "quote": "Muối < 5 g/ngày"},
                     {"field": "protein_g_max", "value": 5, "unit": "g_salt", "quote": "Muối < 5 g/ngày"}],
           "other_instructions": [], "language": "vi"}
    monkeypatch.setattr("app.api.routes.get_provider", lambda s: FakeVision(out))
    j = client.post("/api/health-limits/extract", data={"text": "Muối < 5 g/ngày.", "consent_ai_processing": "true"},
                    headers=auth).json()
    assert j["limits"] == {"sodium_mg_max": 1965.0}  # 5 g × 393 mg/g
    assert j["items"][0]["converted_from"] == "salt" and j["items"][0]["original_unit"] == "g_salt"
    assert j["rejected"][0]["reason"] == "unit_mismatch"  # g_salt chỉ dành cho natri
