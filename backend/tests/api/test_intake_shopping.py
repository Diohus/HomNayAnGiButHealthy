"""Vòng 6: L1 nhật ký đã ăn + cân lại, L2 danh sách đi chợ, L0a/L0b, L3 cache parse."""

from datetime import UTC, date, datetime, timedelta

import pytest

from app.ai import recipes as R
from app.chat.parser import parse, rule_parse
from tests.conftest import BASE_PROFILE, register
from tests.robustness.test_robustness import FakeProvider

DAY = date(2026, 10, 21)
EN = {"Accept-Language": "en"}


def gen(client, h, day=DAY, days=1):
    r = client.post("/api/menu/generate", json={"start": day.isoformat(), "days": days}, headers=h)
    assert r.status_code == 200, r.text
    return r.json()


def meals(menu):
    return {m["slot"]: m for m in menu["plan"]["meals"]}


def kcal_of(catalog, items):
    return sum(catalog.food(i["food_code"]).nutrient("energy_kcal", i["grams"]) for i in items)


# ---------- L1: đánh dấu đã ăn ----------
def test_mark_eaten_and_unmark(client, auth, catalog):
    m = meals(gen(client, auth)[0])
    r = client.post(f"/api/menu/{DAY}/meals/breakfast/eaten", json={"eaten": True}, headers=auth).json()
    assert r["eaten_slots"] == ["breakfast"]
    assert {e["food_code"]: e["grams"] for e in r["intake"]["entries"]} == \
           {i["food_code"]: i["grams"] for i in m["breakfast"]["items"]}
    assert r["intake"]["totals"]["energy_kcal"] == pytest.approx(kcal_of(catalog, m["breakfast"]["items"]))
    # đánh dấu lại không nhân đôi
    r = client.post(f"/api/menu/{DAY}/meals/breakfast/eaten", json={"eaten": True}, headers=auth).json()
    assert len(r["intake"]["entries"]) == len(m["breakfast"]["items"])
    r = client.post(f"/api/menu/{DAY}/meals/breakfast/eaten", json={"eaten": False}, headers=auth).json()
    assert r["eaten_slots"] == [] and r["intake"]["entries"] == []
    assert client.post(f"/api/menu/{DAY}/meals/snack/eaten", json={"eaten": True},
                       headers=auth).json()["code"] == "MEAL_NOT_FOUND"


def test_off_plan_intake_crud_and_totals(client, auth, catalog):
    gen(client, auth)
    r = client.post("/api/intake", json={"day": DAY.isoformat(), "slot": "snack", "food_code": "banana",
                                         "grams": 120}, headers=auth)
    assert r.status_code == 201
    eid = r.json()["id"]
    got = client.get(f"/api/intake?day={DAY}", headers=auth).json()
    assert got["entries"][0]["source"] == "manual"
    assert got["totals"]["energy_kcal"] == pytest.approx(catalog.food("banana").nutrient("energy_kcal", 120))
    for bad, code in [({"grams": 0}, "GRAMS_RANGE"), ({"grams": 5000}, "GRAMS_RANGE"),
                      ({"food_code": "unicorn"}, "FOOD_NOT_FOUND")]:
        body = {"day": DAY.isoformat(), "slot": "snack", "food_code": "banana", "grams": 100, **bad}
        assert client.post("/api/intake", json=body, headers=auth).json()["code"] == code
    other = register(client, email="o@example.com")
    assert client.delete(f"/api/intake/{eid}", headers=other).status_code == 404
    assert client.delete(f"/api/intake/{eid}", headers=auth).status_code == 204


def test_intake_allergy_rejected(client):
    h = register(client, profile={**BASE_PROFILE, "allergies": ["shellfish"]})
    r = client.post("/api/intake", json={"day": DAY.isoformat(), "slot": "lunch", "food_code": "shrimp",
                                         "grams": 100}, headers={**h, **EN})
    assert r.status_code == 422 and r.json()["code"] == "ALLERGEN_CONFLICT"
    assert r.json()["params"] == {"food": "Shrimp", "reason": "shellfish allergy"}


def test_intake_deleted_with_account(client, auth, engine):
    from sqlalchemy import func, select

    from app.db import models as M

    client.post("/api/intake", json={"day": DAY.isoformat(), "slot": "snack", "food_code": "banana", "grams": 100},
                headers=auth)
    client.delete("/api/me", headers=auth)
    with engine.connect() as c:
        assert c.execute(select(func.count()).select_from(M.IntakeEntry)).scalar() == 0


# ---------- L1: cân lại ----------
def test_rebalance_keeps_eaten_and_floors_rest(client, auth, catalog):
    before = meals(gen(client, auth)[0])
    client.post(f"/api/menu/{DAY}/meals/breakfast/eaten", json={"eaten": True}, headers=auth)
    # ăn ngoài kế hoạch khá nhiều ⇒ các bữa còn lại phải giảm, nhưng không dưới sàn 50 % phần của bữa
    client.post("/api/intake", json={"day": DAY.isoformat(), "slot": "snack", "food_code": "chocolate_cake",
                                     "grams": 256}, headers=auth)
    r = client.post(f"/api/menu/{DAY}/rebalance", headers=auth)
    assert r.status_code == 200, r.text
    after = meals(r.json())
    assert {i["food_code"]: i["grams"] for i in after["breakfast"]["items"]} == \
           {i["food_code"]: i["grams"] for i in before["breakfast"]["items"]}
    target = next(t["value"] for t in r.json()["targets"] if t["code"] == "energy_kcal")
    for slot, share in (("lunch", 0.40), ("dinner", 0.35)):
        assert kcal_of(catalog, after[slot]["items"]) >= 0.5 * share * target - 30
    rest_before = kcal_of(catalog, before["lunch"]["items"] + before["dinner"]["items"])
    rest_after = kcal_of(catalog, after["lunch"]["items"] + after["dinner"]["items"])
    assert rest_after < rest_before


def test_rebalance_over_target_reports_and_no_carry_over(client, auth):
    gen(client, auth)
    client.post("/api/intake", json={"day": DAY.isoformat(), "slot": "snack", "food_code": "cheese_pizza",
                                     "grams": 2000}, headers=auth)
    r = client.post(f"/api/menu/{DAY}/rebalance", headers=auth).json()
    assert any(w.startswith("OVER_TARGET:") for w in r["plan"]["warnings"])
    assert r["energy_adjustment_kcal"] == 0
    nxt = client.get(f"/api/menu?start={DAY + timedelta(days=1)}", headers=auth).json()[0]
    assert nxt is None  # không tự bù sang ngày sau


def test_rebalance_blocked_when_ed_flagged(client, auth, engine):
    from app.db import models as M
    from app.db import session as dbs

    gen(client, auth)
    client.post("/api/intake", json={"day": DAY.isoformat(), "slot": "snack", "food_code": "cheese_pizza",
                                     "grams": 1000}, headers=auth)
    with dbs._SessionLocal() as s:  # gắn cờ: 1 sự kiện DISTRESS
        uid = s.query(M.User).first().id
        s.add(M.SafetyEvent(user_id=uid, kind="DISTRESS", at=datetime.now(UTC)))
        s.commit()
    r = client.post(f"/api/menu/{DAY}/rebalance", headers=auth)
    assert r.status_code == 409 and r.json()["code"] == "ED_SUPPORT"


def test_rebalance_nothing_left(client, auth):
    m = meals(gen(client, auth)[0])
    for slot in m:
        client.post(f"/api/menu/{DAY}/meals/{slot}/eaten", json={"eaten": True}, headers=auth)
    assert client.post(f"/api/menu/{DAY}/rebalance", headers=auth).json()["code"] == "NOTHING_TO_REBALANCE"


# ---------- L1: chat log_food ----------
@pytest.mark.parametrize("text", ["tôi vừa ăn 1 quả chuối", "trưa nay ăn bánh mì rồi", "I just had a banana"])
def test_rule_log_intent(text):
    assert rule_parse(text).intent == "log_food"


def test_chat_log_apply_then_rebalance(client, auth):
    gen(client, auth)
    r = client.post("/api/chat", json={"message": "tôi vừa ăn 2 quả chuối"}, headers=auth).json()
    log_id, reb_id = (p["id"] for p in r["proposals"])
    day = r["proposals"][0]["day"]
    a = client.post(f"/api/chat/proposals/{log_id}/apply", headers=auth)
    assert a.status_code == 200
    got = client.get(f"/api/intake?day={day}", headers=auth).json()
    assert got["entries"][0]["food_code"] == "banana" and got["entries"][0]["source"] == "chat"
    b = client.post(f"/api/chat/proposals/{reb_id}/apply", headers=auth)
    assert b.status_code in (200, 404)  # 404 MENU_NOT_FOUND nếu hôm nay (giờ thật) chưa có thực đơn


# ---------- L2: đi chợ ----------
def test_shopping_list_aggregates_servings_and_pantry(client, auth, catalog):
    days = gen(client, auth, days=2)
    expected: dict[str, float] = {}
    for d in days:
        for m in d["plan"]["meals"]:
            for i in m["items"]:
                expected[i["food_code"]] = expected.get(i["food_code"], 0) + i["grams"]
    r = client.get(f"/api/shopping-list?start={DAY}&days=3&servings=2", headers=auth).json()
    assert r["missing_days"] == [(DAY + timedelta(days=2)).isoformat()]
    got = {i["code"]: i for g in r["groups"] for i in g["items"]}
    assert set(got) == set(expected)
    for code, g in expected.items():
        assert got[code]["grams"] == round(g * 2)
        p = got[code]["purchase"]
        assert p["grams"] >= got[code]["grams"] - 1e-6  # làm tròn LÊN
    assert [g["category"] for g in r["groups"]] == sorted(
        [g["category"] for g in r["groups"]], key=["protein", "carb", "vegetable", "dairy", "fruit", "nut",
                                                    "fat", "snack"].index)
    # trừ đồ có sẵn
    code = next(iter(expected))
    client.post("/api/pantry", json={"day": DAY.isoformat(), "food_code": code, "grams": 30}, headers=auth)
    r2 = client.get(f"/api/shopping-list?start={DAY}&days=3&servings=2", headers=auth).json()
    got2 = {i["code"]: i for g in r2["groups"] for i in g["items"]}
    assert got2.get(code, {"grams": 0})["grams"] == max(0, round(expected[code] * 2 - 30))


def test_shopping_purchase_units():
    from app.services.shopping import _purchase

    class F:
        def __init__(self, code, category, portion=None):
            self.code, self.category, self.portion = code, category, portion

    class Pn:
        description, grams = "1 cup", 66

    assert _purchase(F("egg", "protein"), 120) == {"kind": "count", "count": 3, "unit_key": "egg", "grams": 150}
    assert _purchase(F("x", "snack", Pn()), 100)["count"] == 2
    assert _purchase(F("rice", "carb"), 30) == {"kind": "weight", "grams": 100}
    assert _purchase(F("rice", "carb"), 260) == {"kind": "weight", "grams": 300}
    assert _purchase(F("oil", "fat"), 23) == {"kind": "weight", "grams": 30}


def test_shopping_list_validation_and_lang(client, auth):
    gen(client, auth)
    assert client.get(f"/api/shopping-list?start={DAY}&days=8", headers=auth).status_code == 422
    assert client.get(f"/api/shopping-list?start={DAY}&servings=11", headers=auth).json()["code"] == "SERVINGS_RANGE"
    r = client.get(f"/api/shopping-list?start={DAY}", headers={**auth, **EN}).json()
    assert r["groups"][0]["label"] in ("Meat, fish, eggs, beans", "Starches")


# ---------- L0a: alias liền kề ⇒ món ghép ----------


# ---------- L0b: không thích dạng chữ ----------
def test_text_dislike_api_and_recipe_avoids(client, auth, monkeypatch):
    r = client.post("/api/preferences/dislikes", json={"kind": "text", "code": "  Hành "}, headers=auth)
    assert r.status_code == 201 and r.json()["name"] == "hành"
    r41 = client.post("/api/preferences/dislikes", json={"kind": "text", "code": "x" * 41}, headers=auth)
    assert r41.status_code == 422 and r41.json()["code"] == "TEXT_TOO_LONG"
    gen(client, auth)
    bad = {"steps": ["Phi hành cho thơm rồi áp chảo"], "seasonings": [{"name": "Hành lá", "note": "rắc"}], "tip": ""}
    fp = FakeProvider([bad, bad, bad])
    monkeypatch.setattr("app.api.routes.get_provider", lambda s: fp)
    out = client.post(f"/api/menu/{DAY}/meals/lunch/recipe", headers=auth).json()
    assert fp.calls == 3 and out["source"] == "template"
    text = " ".join([*out["steps"], *(f"{s['name']} {s['note']}" for s in out["seasonings"]), out["tip"]])
    assert "hành" not in text.lower()


def test_violations_avoid_word_boundaries():
    assert R.violations("Rắc hành lá", [], [], avoid=["hành"]) == ["avoid:hành"]
    assert R.violations("Rac hanh la", [], [], avoid=["hanh"]) == ["avoid:hanh"]
    assert not R.violations("Thêm hạnh nhân", [], [], avoid=["hành"])  # có dấu ⇒ so khớp giữ dấu
    assert not R.violations("Xào nhanh rau", [], [], avoid=["hanh"])
    t = R.template_recipe("Gà", ["Ức gà"], [], [], False, "vi", avoid=["hành", "tiêu"])
    names = [s.name for s in t.seasonings]
    assert "Hành lá" not in names and "Tiêu" not in names and "Tỏi" in names


def test_chat_dislike_text_apply(client, auth):
    r = client.post("/api/chat", json={"message": "tôi không ăn được rau răm"}, headers=auth).json()
    p = r["proposals"][0]
    assert p["preference"] == {"kind": "text", "code": "rau răm"}
    client.post(f"/api/chat/proposals/{p['id']}/apply", headers=auth)
    assert client.get("/api/preferences/dislikes", headers=auth).json()[0]["kind"] == "text"


# ---------- L3: cache parse ----------
def test_parse_cache_skips_second_llm_call():
    out = {"intent": "want_food", "mentions": ["gà"], "quantity_value": None, "quantity_unit": None, "slot": None,
           "day": None, "cheat_day": False}
    fp = FakeProvider([out, out])
    a, src = parse("Tôi muốn ăn gà", fp)
    b, _ = parse("  tôi   muốn ăn GÀ ", fp)
    assert src == "llm" and fp.calls == 1 and a == b
    parse("Tôi muốn ăn gà", fp, lang="en")  # khóa gồm ngôn ngữ
    assert fp.calls == 2


def test_parse_cache_never_stores_ed_signals():
    out = {"intent": "restrict", "mentions": [], "quantity_value": None, "quantity_unit": None, "slot": None,
           "day": None, "cheat_day": False}
    fp = FakeProvider([out, out])
    parse("mai tôi nhịn ăn", fp)
    parse("mai tôi nhịn ăn", fp)
    assert fp.calls == 2
