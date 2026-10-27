"""Mục 4 work.txt — mỗi trường hợp robustness có test tự động."""

from datetime import date, timedelta

import pytest

from app.ai import recipes as R
from app.ai.providers import LLMError
from app.planner import max_consecutive_run
from tests.conftest import BASE_PROFILE, register

DAY = date(2026, 10, 21)
MACROS = ("energy_kcal", "protein_g", "carb_g", "fat_g")


def gen(client, h, day=DAY, days=1):
    r = client.post("/api/menu/generate", json={"start": day.isoformat(), "days": days}, headers=h)
    assert r.status_code == 200, r.text
    return r.json()


def macro_devs(plan):
    return {d["code"]: d["pct"] for d in plan["deviations"] if d["code"] in MACROS}


# ---------- 4.1 Đầu vào vô lý ----------
@pytest.mark.parametrize("patch", [
    {"weight_kg": 0}, {"weight_kg": -5}, {"height_cm": 300}, {"height_cm": 50}, {"age": -1}, {"age": 0},
    {"age": 17}, {"age": 30.5}, {"weight_kg": 70.123456}, {"height_cm": "abc"}, {"weight_kg": True},
    {"weight_kg": None}, {"sex": "other"}, {"activity_level": "extreme"}, {"allergies": ["unicorn"]},
    {"custom_target_kcal": 100}, {"custom_target_kcal": 99999}, {"unknown_field": 1},
    {"conditions": ["diabetes_t1", "diabetes_t2"]}, {"sex": "male", "conditions": ["pregnant"]},
])
def test_absurd_profile_rejected_cleanly(client, patch):
    h = register(client, profile=False)
    r = client.put("/api/profile", json={**BASE_PROFILE, **patch}, headers=h)
    assert r.status_code == 422, r.text
    body = r.json()
    assert body["code"] == "VALIDATION_ERROR" and body["errors"][0]["message"]
    assert all("input" not in e for e in body["errors"])  # không phản hồi lại dữ liệu sức khỏe thô


def test_nan_and_infinity_rejected(client):
    h = register(client, profile=False)
    r = client.put("/api/profile", content=b'{"sex":"female","age":30,"height_cm":NaN,"weight_kg":55,'
                                            b'"activity_level":"moderate"}', headers={**h, "Content-Type": "application/json"})
    assert r.status_code == 422


@pytest.mark.parametrize("payload", [
    {"slot": "lunch", "food_code": "egg", "delta_g": 0}, {"slot": "lunch", "food_code": "egg", "delta_g": 9999},
    {"slot": "lunch", "food_code": "egg", "delta_g": "nhiều"}, {"slot": "brunch", "food_code": "x", "delta_g": 10},
])
def test_absurd_adjust_rejected(client, auth, payload):
    gen(client, auth)
    r = client.post(f"/api/menu/{DAY}/adjust", json=payload, headers=auth)
    assert r.status_code in (404, 422)


def test_absurd_pantry_rejected(client, auth):
    for grams in (0, -10, 100000):
        r = client.post("/api/pantry", json={"day": DAY.isoformat(), "food_code": "egg", "grams": grams}, headers=auth)
        assert r.status_code == 422
    r = client.post("/api/pantry", json={"day": DAY.isoformat(), "food_code": "khong_ton_tai", "grams": 100},
                    headers=auth)
    assert r.status_code == 404


# ---------- 4.2 Ràng buộc mâu thuẫn ----------
def test_pantry_allergen_conflict_detected(client):
    h = register(client, profile={**BASE_PROFILE, "allergies": ["shellfish"]})
    r = client.post("/api/pantry", json={"day": DAY.isoformat(), "food_code": "shrimp", "grams": 100}, headers=h)
    assert r.status_code == 422 and r.json()["code"] == "ALLERGEN_CONFLICT"
    j = r.json()
    # E10: lý do đã dịch + params cụ thể; mã thô chỉ nằm trong trường `reason` (cho máy đọc)
    assert j["reason"] == "allergy:shellfish" and "allergy:" not in j["message"]
    assert j["params"] == {"food": "Tôm", "reason": "dị ứng hải sản có vỏ"}
    r = client.post("/api/pantry", json={"day": DAY.isoformat(), "food_code": "shrimp", "grams": 100},
                    headers={**h, "Accept-Language": "en-US,en;q=0.9"})
    assert r.json()["params"] == {"food": "Shrimp", "reason": "shellfish allergy"}
    assert r.json()["message"] == "Can't add Shrimp: it conflicts with the shellfish allergy you declared."


def test_pantry_exceeding_energy_detected(client, auth):
    r = client.post("/api/pantry", json={"day": DAY.isoformat(), "food_code": "peanuts", "grams": 600}, headers=auth)
    assert r.status_code == 201 and "PANTRY_EXCEEDS_ENERGY" in r.json()["warnings"]
    plan = gen(client, auth)[0]["plan"]
    assert "LOCKED_EXCEEDS_ENERGY" in plan["conflicts"] and plan["status"] == "conflict"


# ---------- 4.3 Không đủ nguyên liệu ----------
def test_insufficient_foods_best_effort(client):
    # vegan + dị ứng đậu nành/đậu phộng/hạt/gluten ⇒ rất ít nguồn đạm
    h = register(client, profile={**BASE_PROFILE, "diets": ["vegan", "gluten_free"],
                                  "allergies": ["soy", "peanut", "tree_nut"], "goal": "gain_muscle"})
    plan = gen(client, h)[0]["plan"]
    assert plan["meals"], "không được trả rỗng"
    if plan["status"] != "ok":
        assert plan["shortfalls"] and plan["suggestions"] is not None


# ---------- 4.4 +/- liên tục ----------
def test_repeated_adjustments_stay_consistent(client, auth):
    m = gen(client, auth)[0]
    lunch = next(x for x in m["plan"]["meals"] if x["slot"] == "lunch")
    food = next(i["food_code"] for i in lunch["items"] if i["origin"] == "optimizer")
    for delta in (10, 10, -10, 20, -30, 10):
        r = client.post(f"/api/menu/{DAY}/adjust", json={"slot": "lunch", "food_code": food, "delta_g": delta},
                        headers=auth)
        assert r.status_code == 200, r.text
        plan = r.json()["plan"]
        devs = macro_devs(plan)
        if plan["status"] == "ok":
            assert all(abs(v) <= 0.05 + 1e-9 for v in devs.values()), devs
        else:  # không đạt được thì phải báo rõ, không âm thầm bỏ qua
            assert plan["shortfalls"]
        # khối lượng người dùng đặt được giữ đúng
        item = next(i for x in plan["meals"] if x["slot"] == "lunch" for i in x["items"] if i["food_code"] == food)
        assert item["locked"]


def test_adjust_total_matches_ingredients(client, auth, catalog):
    m = gen(client, auth)[0]
    meal = m["plan"]["meals"][0]
    food = meal["items"][0]["food_code"]
    plan = client.post(f"/api/menu/{DAY}/adjust", json={"slot": meal["slot"], "food_code": food, "delta_g": 10},
                       headers=auth).json()["plan"]
    total = sum(catalog.food(i["food_code"]).nutrient("energy_kcal", i["grams"]) for x in plan["meals"]
                for i in x["items"])
    assert total == pytest.approx(plan["totals"]["energy_kcal"])


# ---------- 4.5 Lặp món ----------
def test_rotation_seven_days_and_after_edits(client, auth):
    days = gen(client, auth, days=7)
    mains = {date.fromisoformat(d["day"]): {m["dish_code"] for m in d["plan"]["meals"] if m["dish_code"]}
             for d in days}
    assert max_consecutive_run(mains) <= 3
    # sửa ngày giữa tuần (sinh lại + chỉnh +/-) vẫn giữ ràng buộc
    client.post("/api/menu/generate", json={"start": (DAY + timedelta(days=3)).isoformat()}, headers=auth)
    d3 = client.get(f"/api/menu?start={DAY + timedelta(days=3)}", headers=auth).json()[0]
    meal = d3["plan"]["meals"][1]
    client.post(f"/api/menu/{DAY + timedelta(days=3)}/adjust",
                json={"slot": meal["slot"], "food_code": meal["items"][0]["food_code"], "delta_g": 10}, headers=auth)
    all_days = client.get(f"/api/menu?start={DAY}&days=7", headers=auth).json()
    mains = {date.fromisoformat(d["day"]): {m["dish_code"] for m in d["plan"]["meals"] if m["dish_code"]}
             for d in all_days}
    assert max_consecutive_run(mains) <= 3


def test_chat_cannot_break_rotation(client, auth):
    """Món chính do chatbot yêu cầu vẫn bị chặn ở ngày thứ 4 liên tiếp, kể cả khi áp dụng đề xuất."""
    from app.db import session as dbs
    from app.planner import Requirement
    from app.services import menu as MS

    with dbs._SessionLocal() as s:
        import uuid as _u

        uid = s.execute(__import__("sqlalchemy").text("select id from users")).scalar()
        uid = uid if isinstance(uid, _u.UUID) else _u.UUID(str(uid))
        c = MS.Ctx(s, uid)
        for i in range(3):
            plan, t = c.solve(DAY + timedelta(days=i), required=[Requirement(kind="dish", code="ga_ap_chao",
                                                                             slot="lunch")])
            MS.save_plan(s, uid, plan, t)
            s.commit()
        plan, _ = c.solve(DAY + timedelta(days=3), required=[Requirement(kind="dish", code="ga_ap_chao",
                                                                         slot="lunch")])
        assert "ga_ap_chao" not in plan.main_dishes()
        assert "REQUIRED_DISH_ROTATION:ga_ap_chao" in plan.conflicts
        from app.core.errors import AppError

        bad = plan.model_copy(deep=True)
        bad.meals[1].dish_code = "ga_ap_chao"
        with pytest.raises(AppError) as e:
            MS.apply_plan(s, uid, bad)
        assert e.value.code == "ROTATION_VIOLATION"


# ---------- 4.6 Đổi mức hoạt động: số bữa đổi, giữ dữ liệu ----------
def test_meal_count_change_keeps_data(client, auth):
    m = gen(client, auth)[0]
    bf = next(x for x in m["plan"]["meals"] if x["slot"] == "breakfast")
    food = bf["items"][0]["food_code"]
    r = client.post(f"/api/menu/{DAY}/adjust", json={"slot": "breakfast", "food_code": food, "delta_g": 50},
                    headers=auth)
    chosen = next(i["grams"] for x in r.json()["plan"]["meals"] if x["slot"] == "breakfast" for i in x["items"]
                  if i["food_code"] == food)
    client.put("/api/profile", json={**BASE_PROFILE, "activity_level": "sedentary"}, headers=auth)
    m2 = gen(client, auth)[0]
    assert [x["slot"] for x in m2["plan"]["meals"]] == ["lunch", "dinner"]
    assert "breakfast" in m2["inactive_meals"]
    total = sum(i["grams"] for x in m2["plan"]["meals"] for i in x["items"] if i["food_code"] == food and i["locked"])
    assert total == pytest.approx(chosen)  # nguyên liệu đã chọn không mất, được chuyển sang bữa khác
    client.put("/api/profile", json=BASE_PROFILE, headers=auth)
    m3 = gen(client, auth)[0]
    assert [x["slot"] for x in m3["plan"]["meals"]] == ["breakfast", "lunch", "dinner"]


# ---------- 4.7 LLM trả sai định dạng ----------
class FakeProvider:
    name = "fake"

    def __init__(self, outputs):
        self.outputs, self.calls = list(outputs), 0

    def complete_json(self, system, user, schema, schema_name):
        self.calls += 1
        o = self.outputs.pop(0) if self.outputs else {"bad": True}
        if isinstance(o, Exception):
            raise o
        return o


def test_llm_bad_format_retries_then_fallback():
    fp = FakeProvider([{"steps": "không phải list"}, {"foo": 1}, "rác"])
    r = R.generate_recipe(fp, "Ức gà áp chảo", ["Ức gà"], [], [], False, max_retries=2)
    assert fp.calls == 3 and r.source == "template" and r.steps


def test_llm_output_with_allergen_rejected():
    bad = {"steps": ["Ướp gà với nước mắm"], "seasonings": [{"name": "Nước mắm", "note": "nêm"}], "tip": "ok"}
    r = R.generate_recipe(FakeProvider([bad, bad, bad]), "Ức gà", ["Ức gà"], ["fish"], [], False)
    assert r.source == "template"
    assert all("mắm" not in s.name.lower() for s in r.seasonings)


def test_llm_output_with_numbers_rejected():
    bad = {"steps": ["Dùng 200g ức gà, khoảng 300 kcal"], "seasonings": [], "tip": ""}
    good = {"steps": ["Áp chảo ức gà đến khi vàng"], "seasonings": [{"name": "Tiêu", "note": "rắc"}], "tip": "ít dầu"}
    fp = FakeProvider([bad, good])
    r = R.generate_recipe(fp, "Ức gà", ["Ức gà"], [], [], False)
    assert r.source == "llm" and fp.calls == 2


# ---------- 4.8 Mất kết nối / timeout AI ----------
def test_llm_timeout_keeps_existing_recipe(client, auth, monkeypatch):
    gen(client, auth)
    good = {"steps": ["Hấp chín"], "seasonings": [{"name": "Gừng", "note": "thái sợi"}], "tip": "Ăn nóng"}
    monkeypatch.setattr("app.api.routes.get_provider", lambda s: FakeProvider([good]))
    r1 = client.post(f"/api/menu/{DAY}/meals/lunch/recipe", headers=auth).json()
    assert r1["source"] == "llm"
    before = client.get(f"/api/menu?start={DAY}", headers=auth).json()[0]
    monkeypatch.setattr("app.api.routes.get_provider", lambda s: FakeProvider([LLMError("timeout")] * 3))
    r2 = client.post(f"/api/menu/{DAY}/meals/lunch/recipe", headers=auth)
    assert r2.status_code == 200 and r2.json()["kept_previous"] and r2.json()["steps"] == ["Hấp chín"]
    after = client.get(f"/api/menu?start={DAY}", headers=auth).json()[0]
    assert after["plan"] == before["plan"] and after["version"] == before["version"]


def test_chat_works_when_llm_down(client, auth, monkeypatch):
    monkeypatch.setattr("app.services.chat.get_provider", lambda s: FakeProvider([LLMError("timeout")] * 5))
    r = client.post("/api/chat", json={"message": "tôi muốn ăn kem"}, headers=auth)
    assert r.status_code == 200 and r.json()["parser"] == "rules" and r.json()["proposals"]
