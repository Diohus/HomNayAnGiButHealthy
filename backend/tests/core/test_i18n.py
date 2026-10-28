"""Vòng 2 (E1/E2/E5/E6/E7): hạ tầng i18n backend + lỗi, validation, notices, nhu cầu, công thức song ngữ."""

import logging
import re
import string
from datetime import date

import pytest

from app.ai import recipes as R
from app.core import i18n
from app.core.i18n import Msg, parse_accept_language, tr
from app.i18n.en import EN
from app.i18n.vi import VI
from tests.conftest import BASE_PROFILE, register
from tests.robustness.test_robustness import FakeProvider

DAY = date(2026, 10, 21)
EN_H = {"Accept-Language": "en-US,en;q=0.9,vi;q=0.8"}
VI_CHARS = re.compile(r"[à-ỹÀ-Ỹđ]")


def _fields(s: str) -> set[str]:
    return {f for _, f, _, _ in string.Formatter().parse(s) if f}


# ---------- catalog ----------
def test_catalogs_same_keys_and_placeholders():
    assert set(EN) == set(VI)
    for k in VI:
        assert _fields(EN[k]) == _fields(VI[k]), k
        assert VI[k].strip() and EN[k].strip(), k


def test_english_catalog_has_no_vietnamese():
    bad = {k: v for k, v in EN.items() if VI_CHARS.search(v.replace("×", ""))}
    assert not bad


@pytest.mark.parametrize(("header", "lang"), [
    (None, "vi"), ("", "vi"), ("en", "en"), ("en-US,en;q=0.9", "en"), ("vi-VN,vi;q=0.9,en;q=0.8", "vi"),
    ("fr-FR,en;q=0.5", "en"), ("fr-FR", "vi"), ("EN-gb", "en"),
])
def test_parse_accept_language(header, lang):
    assert parse_accept_language(header) == lang


def test_missing_en_key_falls_back_to_vi_and_warns(monkeypatch, caplog):
    monkeypatch.setitem(i18n.CATALOGS, "en", {k: v for k, v in EN.items() if k != "error.EMAIL_EXISTS"})
    with caplog.at_level(logging.WARNING, logger="app.core.i18n"):
        assert tr("error.EMAIL_EXISTS", "en") == VI["error.EMAIL_EXISTS"]
    assert "error.EMAIL_EXISTS" in caplog.text


def test_nested_msg_params():
    assert tr("reason.allergy", "en", name=Msg("allergen.fish")) == "fish allergy"
    assert tr("reason.diet", "vi", name=Msg("diet.vegan")) == "chế độ ăn thuần chay"


# ---------- lỗi API ----------
def test_api_errors_bilingual(client):
    register(client, profile=False)
    body = {"email": "a@example.com", "password": "matkhau-an-toan"}
    r = client.post("/api/auth/register", json=body, headers=EN_H)
    assert r.json() == {"code": "EMAIL_EXISTS", "message": "This email is already registered."}
    r = client.post("/api/auth/register", json=body)
    assert r.json()["message"] == "Email đã được đăng ký."
    r = client.get("/api/profile", headers=EN_H)
    assert r.json()["code"] == "UNAUTHENTICATED" and r.json()["message"] == "Please log in."


def test_rate_limited_message_has_seconds(client):
    for _ in range(5):
        client.post("/api/auth/login", json={"email": "x@example.com", "password": "sai-mat-khau"})
    r = client.post("/api/auth/login", json={"email": "x@example.com", "password": "sai-mat-khau"}, headers=EN_H)
    j = r.json()
    assert j["code"] == "RATE_LIMITED" and f"{j['retry_after_s']} seconds" in j["message"]
    assert j["params"] == {"retry_after_s": j["retry_after_s"]}


def test_validation_bilingual_and_no_input_echo(client):
    h = register(client, profile=False)
    bad = {**BASE_PROFILE, "age": 17, "height_cm": 300, "weight_kg": 70.123}
    r = client.put("/api/profile", json=bad, headers={**h, **EN_H})
    j = r.json()
    assert r.status_code == 422 and j["code"] == "VALIDATION_ERROR" and j["message"] == "Invalid data."
    msgs = {e["field"]: e["message"] for e in j["errors"]}
    assert msgs["age"].startswith("Age must be between 18 and 100")
    assert msgs["height_cm"] == "Height must be between 120 and 230 cm."
    assert msgs["weight_kg"] == "Weight can have at most 1 decimal place(s)."
    assert "input" not in str(j) and "70.123" not in str(j)
    r = client.put("/api/profile", json=bad, headers=h)
    msgs = {e["field"]: e["message"] for e in r.json()["errors"]}
    assert msgs["age"].startswith("Tuổi phải trong khoảng 18–100")
    assert msgs["weight_kg"] == "Cân nặng chỉ được có tối đa 1 chữ số thập phân."


def test_pydantic_builtin_validation_translated(client):
    r = client.post("/api/auth/register", json={"email": "a@example.com", "password": "short"}, headers=EN_H)
    assert r.json()["errors"][0]["message"] == "Must be at least 8 characters."
    r = client.post("/api/auth/register", json={"email": "a@example.com"})
    assert r.json()["errors"][0]["message"] == "Thiếu thông tin bắt buộc."


def test_low_energy_params(client):
    h = register(client, profile=False)
    r = client.put("/api/profile", json={**BASE_PROFILE, "custom_target_kcal": 900}, headers={**h, **EN_H})
    j = r.json()
    assert j["code"] == "LOW_ENERGY_ACK_REQUIRED" and j["params"]["requested_kcal"] == 900
    assert "900 kcal is below the safe minimum" in j["message"] and "floor_kcal" in j


# ---------- notices + nhu cầu + món ----------
def test_notices_and_needs_bilingual(client):
    h = register(client, profile={**BASE_PROFILE, "conditions": ["hypertension"]})
    en = client.get("/api/needs", headers={**h, **EN_H}).json()
    vi = client.get("/api/needs", headers=h).json()
    en_n = {n["code"]: n["text"] for n in en["notices"]}
    vi_n = {n["code"]: n["text"] for n in vi["notices"]}
    assert set(en_n) == set(vi_n) == {"DISCLAIMER", "SODIUM_SEASONING"}
    assert en_n["DISCLAIMER"].startswith("This app does not diagnose") and vi_n["DISCLAIMER"].startswith("Ứng dụng")
    iron = next(t for t in en["needs"]["targets"] if t["code"] == "iron_mg")
    assert iron["reference"]["applies_to"] == "female, 30 years"
    assert en["needs"]["targets"] and all(t["value"] == v["value"] for t, v in
                                          zip(en["needs"]["targets"], vi["needs"]["targets"], strict=True))
    m = client.post("/api/menu/generate", json={"start": DAY.isoformat()}, headers={**h, **EN_H}).json()[0]
    assert any(n["text"].startswith("Sodium from added salt") for n in m["notices"])


def test_dishes_have_english_names(client, auth):
    dishes = client.get("/api/dishes", headers=auth).json()
    assert len(dishes) >= 65 and all(d["name_en"] and not VI_CHARS.search(d["name_en"]) for d in dishes)
    assert next(d for d in dishes if d["code"] == "ca_hoi_ap_chao")["name_en"] == "Pan-seared salmon"


# ---------- công thức (E5): bộ lọc dị ứng tiếng Anh ----------
def test_violations_checks_both_languages_regardless_of_lang():
    assert R.violations("Marinate with fish sauce", ["fish"], [])
    assert R.violations("Ướp với nước mắm", ["fish"], [])
    assert R.violations("Spread some peanut butter", ["peanut"], [])
    assert R.violations("Add shrimp paste", ["shellfish"], [])
    assert R.violations("Finish with a splash of rice wine", [], ["halal"])
    assert R.violations("Add 2 tbsp of oil", [], []) == ["NUMERIC_CLAIM"]
    assert not R.violations("Steam the catfish fillet", [], [], ["Channel catfish"])
    assert not R.violations("Steam the eggplant", ["egg"], [])  # so khớp theo từ


def test_english_recipe_with_fish_sauce_rejected_falls_back_to_template():
    bad = {"steps": ["Marinate the chicken with fish sauce and garlic"],
           "seasonings": [{"name": "Fish sauce", "note": "a splash"}], "tip": "Serve hot"}
    fp = FakeProvider([bad, bad, bad])
    r = R.generate_recipe(fp, "Pan-seared chicken breast", ["Chicken breast"], ["fish"], [], False,
                          lang="en")
    assert fp.calls == 3 and r.source == "template"
    text = " ".join([*r.steps, *(f"{s.name} {s.note}" for s in r.seasonings), r.tip])
    assert not R.violations(text, ["fish"], []) and not VI_CHARS.search(text)
    assert r.steps[1].startswith("Cook the main part of pan-seared chicken breast")


def test_english_recipe_ok_when_safe():
    good = {"steps": ["Pan-sear the chicken until golden"], "seasonings": [{"name": "Garlic", "note": "minced"}],
            "tip": "Use little oil"}
    r = R.generate_recipe(FakeProvider([good]), "Chicken", ["Chicken breast"], ["fish"], [], False,
                          lang="en")
    assert r.source == "llm"


def test_english_template_filters_by_allergy_and_low_sodium():
    r = R.template_recipe("Steamed egg", ["Whole egg"], ["fish"], ["vegan"], True, lang="en")
    names = [s.name for s in r.seasonings]
    assert "Fish sauce" not in names and "Ginger" not in names  # ghi chú gừng nhắc "fish"
    assert next(s for s in r.seasonings if s.name == "Salt").note == "Use very little"
    assert "Go easy on salt" in r.tip


def test_recipe_api_english(client, auth):
    client.post("/api/menu/generate", json={"start": DAY.isoformat()}, headers=auth)
    r = client.post(f"/api/menu/{DAY}/meals/lunch/recipe", headers={**auth, **EN_H}).json()
    assert r["source"] == "template" and r["steps"][0] == "Prepare and wash all ingredients, then drain."


# ---------- Vòng 3 G1: tạo lại công thức cho cùng một bữa ----------
def test_recipe_regenerate_same_meal_updates_in_place(client, auth, engine, monkeypatch):
    from sqlalchemy import func, select

    from app.db import models as M

    client.post("/api/menu/generate", json={"start": DAY.isoformat()}, headers=auth)
    vi_out = {"steps": ["Áp chảo ức gà"], "seasonings": [{"name": "Tiêu", "note": "rắc"}], "tip": "Ít dầu"}
    en_out = {"steps": ["Pan-sear the chicken"], "seasonings": [{"name": "Pepper", "note": "sprinkle"}],
              "tip": "Little oil"}
    url = f"/api/menu/{DAY}/meals/lunch/recipe"
    monkeypatch.setattr("app.api.routes.get_provider", lambda s: FakeProvider([vi_out]))
    r1 = client.post(url, headers=auth)
    monkeypatch.setattr("app.api.routes.get_provider", lambda s: FakeProvider([en_out]))
    r2 = client.post(url, headers={**auth, **EN_H})
    assert r1.status_code == 200 and r2.status_code == 200, r2.text
    assert r2.json()["steps"] == ["Pan-sear the chicken"] and r2.json()["source"] == "llm"
    menu = client.get(f"/api/menu?start={DAY}", headers=auth).json()[0]
    assert menu["recipes"]["lunch"]["steps"] == ["Pan-sear the chicken"]
    with engine.connect() as c:
        lunch_id = c.execute(select(M.Meal.id).join(M.MenuDay).where(M.Meal.slot == "lunch")).scalar_one()
        assert c.execute(select(func.count()).select_from(M.Recipe).where(M.Recipe.meal_id == lunch_id)
                         ).scalar() == 1
    # lần 3 (vi) vẫn 200
    monkeypatch.setattr("app.api.routes.get_provider", lambda s: FakeProvider([vi_out]))
    assert client.post(url, headers=auth).status_code == 200
