"""Mục 3 work.txt — mỗi guardrail có test."""

import logging
from datetime import UTC, date, datetime, timedelta

from app.core.logging import RedactingFilter
from app.guardrails.eating_disorder import SafetyEventIn, assess, detect_text_signals
from tests.conftest import BASE_PROFILE, register

DAY = date(2026, 10, 21)


# ---- Y tế ----
def test_disclaimer_on_needs_and_menu(client, auth):
    assert any(n["code"] == "DISCLAIMER" for n in client.get("/api/needs", headers=auth).json()["notices"])
    m = client.post("/api/menu/generate", json={"start": DAY.isoformat()}, headers=auth).json()[0]
    assert any(n["code"] == "DISCLAIMER" for n in m["notices"])


def test_insulin_reminder_shown(client):
    h = register(client, profile={**BASE_PROFILE, "conditions": ["diabetes_t1"], "uses_insulin_or_glucose_meds": True})
    notices = client.get("/api/needs", headers=h).json()["notices"]
    assert any(n["code"] == "CONSULT_DOCTOR_INSULIN" for n in notices)


def test_diabetes_menu_controls_carbs(client):
    h = register(client, profile={**BASE_PROFILE, "conditions": ["diabetes_t2"]})
    m = client.post("/api/menu/generate", json={"start": DAY.isoformat()}, headers=h).json()[0]
    carb = next(d for d in m["plan"]["deviations"] if d["code"] == "carb_g")
    energy = next(d for d in m["plan"]["deviations"] if d["code"] == "energy_kcal")
    assert carb["actual"] * 4 / energy["actual"] <= 0.45 * 1.06
    assert carb["actual"] >= 130 * 0.95  # không quá thấp (nguy cơ hạ đường huyết)


SENSITIVE = ("kidney", "cardio", "liver", "pregnant", "lactating")


def _self_managed(cond, **kw):
    return {**BASE_PROFILE, "conditions": [cond], "acknowledge_self_managed": True, **kw}


# ---- Vòng 4: tự quản lý thay cho "chuyên gia xác nhận" ----
def test_sensitive_condition_requires_self_managed_ack(client):
    h = register(client, profile=False)
    for cond in SENSITIVE:
        r = client.put("/api/profile", json={**BASE_PROFILE, "conditions": [cond]}, headers=h)
        assert r.status_code == 409 and r.json()["code"] == "SELF_MANAGED_ACK_REQUIRED", cond
        assert r.json()["conditions"] == [cond]
    r = client.put("/api/profile", json={**BASE_PROFILE, "conditions": ["kidney"]},
                   headers={**h, "Accept-Language": "en"})
    assert "kidney disease" in r.json()["message"] and r.json()["params"]["conditions"] == "kidney disease"
    # bệnh nền không nhạy cảm: không cần xác nhận
    assert client.put("/api/profile", json={**BASE_PROFILE, "conditions": ["hypertension"]},
                      headers=h).status_code == 200


def test_self_managed_can_generate_menu_and_chat(client):
    for cond in SENSITIVE:
        h = register(client, email=f"{cond}@ex.com", profile=_self_managed(cond))
        r = client.post("/api/menu/generate", json={"start": DAY.isoformat()}, headers=h)
        assert r.status_code == 200, (cond, r.text)
        assert any(n["code"] == f"NO_LIMITS_{cond.upper()}" for n in r.json()[0]["notices"])
        r = client.post("/api/chat", json={"message": "tôi muốn ăn gà"}, headers=h)
        assert r.json()["kind"] == "proposal" and r.json()["proposals"], cond


def test_no_limits_notice_until_limits_entered(client):
    h = register(client, profile=_self_managed("kidney"))
    needs = client.get("/api/needs", headers=h).json()
    assert needs["conditions_without_limits"] == ["kidney"]
    assert any(n["code"] == "NO_LIMITS_KIDNEY" for n in needs["notices"])
    # mục tiêu chung như người khỏe: không tự đặt giới hạn y khoa nào
    plain = register(client, email="plain@ex.com")
    t = {x["code"]: x["value"] for x in needs["needs"]["targets"]}
    t0 = {x["code"]: x["value"] for x in client.get("/api/needs", headers=plain).json()["needs"]["targets"]}
    assert t == t0 and "potassium_mg" not in t
    r = client.put("/api/health-limits", json={"condition": "kidney", "limits": {"protein_g_max": 50}}, headers=h)
    assert r.status_code == 200
    needs = client.get("/api/needs", headers=h).json()
    assert needs["conditions_without_limits"] == [] and not any(n["code"].startswith("NO_LIMITS")
                                                                for n in needs["notices"])


def test_menu_operations_not_blocked_for_self_managed(client, auth):
    """Trước vòng 4: unlock/adjust bị 403 khi khai bệnh nền sau khi đã có thực đơn. Giờ chạy bình thường."""
    m = client.post("/api/menu/generate", json={"start": DAY.isoformat()}, headers=auth).json()[0]
    meal = m["plan"]["meals"][0]
    food = meal["items"][0]["food_code"]
    assert client.put("/api/profile", json=_self_managed("kidney"), headers=auth).status_code == 200
    r = client.post(f"/api/menu/{DAY}/adjust", json={"slot": meal["slot"], "food_code": food, "delta_g": 10},
                    headers=auth)
    assert r.status_code == 200
    r = client.post(f"/api/menu/{DAY}/unlock", json={"slot": meal["slot"], "food_code": food}, headers=auth)
    assert r.status_code == 200


def test_user_limits_applied_with_source(client):
    h = register(client, profile=_self_managed("kidney"))
    r = client.put("/api/health-limits", json={"condition": "kidney", "source": "document",
                                               "limits": {"protein_g_max": 50, "sodium_mg_max": 1500,
                                                          "potassium_mg_max": 2000}}, headers=h)
    assert r.status_code == 200 and r.json()["source"] == "document"
    needs = client.get("/api/needs", headers=h).json()
    t = {x["code"]: x for x in needs["needs"]["targets"]}
    assert t["protein_g"]["value"] <= 50 and t["potassium_mg"]["kind"] == "max"
    assert t["sodium_mg"]["reference"]["source"] == "Do người dùng cung cấp (trích từ tài liệu)"
    assert t["sodium_mg"]["adjusted_for"] == ["user_limit"]
    assert client.post("/api/menu/generate", json={"start": DAY.isoformat()}, headers=h).status_code == 200


def test_energy_floor_requires_explicit_ack(client):
    h = register(client, profile=False)
    r = client.put("/api/profile", json={**BASE_PROFILE, "custom_target_kcal": 1000}, headers=h)
    assert r.status_code == 409 and r.json()["code"] == "LOW_ENERGY_ACK_REQUIRED" and r.json()["floor_kcal"] >= 1200
    r = client.put("/api/profile", json={**BASE_PROFILE, "custom_target_kcal": 1000, "acknowledge_low_energy": True},
                   headers=h)
    assert r.status_code == 200


def test_never_proposes_below_floor(client):
    h = register(client, profile={**BASE_PROFILE, "weight_kg": 45, "height_cm": 150, "age": 60,
                                  "activity_level": "sedentary", "goal": "lose"})
    e = next(t for t in client.get("/api/needs", headers=h).json()["needs"]["targets"] if t["code"] == "energy_kcal")
    assert e["value"] >= 1200


# ---- Rối loạn ăn uống ----
def test_repeated_low_targets_trigger_support(client):
    h = register(client, profile=False)
    body = {**BASE_PROFILE, "custom_target_kcal": 900, "acknowledge_low_energy": True}
    codes = [client.put("/api/profile", json=body, headers=h).json().get("code") for _ in range(3)]
    assert codes[-1] == "ED_SUPPORT"


def test_repeated_decrease_after_target_met_stops_cutting(client, auth, catalog):
    m = client.post("/api/menu/generate", json={"start": DAY.isoformat()}, headers=auth).json()[0]
    meal = m["plan"]["meals"][1]
    # nguyên liệu ít năng lượng nhất của bữa: cân lại bù được ⇒ ngày vẫn "đã đủ" sau mỗi lần giảm
    # (giảm món rất béo như thịt ba chỉ thì cân lại theo cấu trúc không bù nổi ⇒ không còn là "giảm khi đã đủ")
    food = min(meal["items"], key=lambda i: catalog.food(i["food_code"]).per_100g["energy_kcal"])["food_code"]
    last = None
    for _ in range(6):
        last = client.post(f"/api/menu/{DAY}/adjust", json={"slot": meal["slot"], "food_code": food, "delta_g": -10},
                           headers=auth)
        if last.status_code == 409:
            break
    assert last.status_code == 409 and last.json()["code"] == "ED_SUPPORT"


def test_ed_assessment_rules():
    now = datetime.now(UTC)
    ev = [SafetyEventIn(kind="COMPENSATION", at=now - timedelta(days=i)) for i in range(3)]
    assert assess(ev, now).flagged
    assert not assess(ev[:2], now).flagged
    assert not assess([SafetyEventIn(kind="LOW_TARGET_ATTEMPT", at=now - timedelta(days=40))] * 5, now).flagged
    assert "DISTRESS" in detect_text_signals("ăn xong em tự gây nôn")
    assert "RESTRICT_INTENT" in detect_text_signals("mai tôi nhịn ăn")


def test_chat_restrict_gets_support_message(client, auth):
    r = client.post("/api/chat", json={"message": "tôi muốn nhịn ăn cả ngày"}, headers=auth).json()
    assert r["kind"] == "support" and not r["proposals"]


# ---- Dị ứng / chế độ ăn ----
def test_allergen_never_in_menu_even_if_added(client):
    h = register(client, profile={**BASE_PROFILE, "allergies": ["peanut", "fish"], "diets": ["vegetarian"]})
    assert client.post("/api/pantry", json={"day": DAY.isoformat(), "food_code": "peanuts", "grams": 30},
                       headers=h).status_code == 422
    m = client.post("/api/menu/generate", json={"start": DAY.isoformat(), "days": 3}, headers=h).json()
    foods = client.get("/api/foods", headers=h).json()
    excluded = {f["code"] for f in foods if f["excluded_reason"]}
    used = {i["food_code"] for d in m for x in d["plan"]["meals"] for i in x["items"]}
    assert "peanuts" in excluded and "salmon" in excluded and "chicken_breast" in excluded
    assert not used & excluded


def test_custom_label_food_with_allergen_rejected(client):
    h = register(client, profile={**BASE_PROFILE, "allergies": ["milk"]})
    body = {"name_vi": "Trà sữa", "per_100g": {"energy_kcal": 80, "protein_g": 1, "carb_g": 15, "fat_g": 2},
            "portion_g": 500, "contains_allergens": ["milk"]}
    r = client.post("/api/foods/custom", json=body, headers=h)
    assert r.status_code == 422 and r.json()["code"] == "ALLERGEN_CONFLICT"


def test_custom_label_inconsistent_rejected(client, auth):
    body = {"name_vi": "Bánh lạ", "per_100g": {"energy_kcal": 50, "protein_g": 20, "carb_g": 50, "fat_g": 20},
            "portion_g": 50}
    assert client.post("/api/foods/custom", json=body, headers=auth).status_code == 422


# ---- Trung thực / độ chính xác ----
def test_shortfalls_explicit_with_suggestions(client):
    h = register(client, profile={**BASE_PROFILE, "diets": ["vegan"], "allergies": ["soy", "peanut", "tree_nut"]})
    m = client.post("/api/menu/generate", json={"start": DAY.isoformat()}, headers=h).json()[0]["plan"]
    for d in m["deviations"]:
        if not d["within"] and d["actual"] < d["target"] and d["kind"] != "max":
            assert d["code"] in m["shortfalls"]


# ---- Bảo mật / quyền riêng tư ----
def test_health_data_encrypted_at_rest(client, auth, engine):
    from sqlalchemy import text

    with engine.connect() as c:
        blob = c.execute(text("select encrypted_payload from health_profiles")).scalar()
    assert b"female" not in blob and b"weight" not in blob


def test_logs_do_not_contain_health_data(client, caplog):
    h = register(client, profile=False)
    with caplog.at_level(logging.DEBUG):
        client.put("/api/profile", json={**BASE_PROFILE, "weight_kg": 300.5, "conditions": ["kidney"]}, headers=h)
        client.put("/api/profile", json={**BASE_PROFILE, "weight_kg": "xx"}, headers=h)
        client.post("/api/chat", json={"message": "tôi bị tiểu đường muốn ăn kem"}, headers=h)
    text_ = caplog.text
    for secret in ("300.5", "kidney", "tiểu đường", "xx"):
        assert secret not in text_


def test_redacting_filter():
    rec = logging.LogRecord("x", logging.INFO, "", 0, "profile weight_kg=72 conditions: diabetes", (), None)
    RedactingFilter().filter(rec)
    assert "72" not in rec.getMessage() and "diabetes" not in rec.getMessage()


def test_user_isolation(client, auth):
    client.post("/api/menu/generate", json={"start": DAY.isoformat()}, headers=auth)
    other = register(client, email="b@example.com")
    assert client.get(f"/api/menu?start={DAY}", headers=other).json() == [None]
    r = client.post("/api/chat", json={"message": "tôi muốn ăn kem"}, headers=auth).json()
    pid = r["proposals"][0]["id"]
    assert client.post(f"/api/chat/proposals/{pid}/apply", headers=other).status_code == 404


def test_requires_auth(client):
    assert client.get("/api/needs").status_code == 401
    assert client.get("/api/needs", headers={"Authorization": "Bearer abc"}).status_code == 401
