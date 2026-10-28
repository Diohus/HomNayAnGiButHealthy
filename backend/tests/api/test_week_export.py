"""Vòng 9 P1 (tổng quan tuần) + P2 (tải dữ liệu của tôi)."""

import json
from datetime import date, timedelta

import pytest

from app.core import ratelimit as RL
from app.foods import load_seed_catalog
from tests.conftest import BASE_PROFILE, log_intake, register

DAY = date(2026, 10, 21)
PW = "matkhau-an-toan"


def _week(client, h, end):
    r = client.get(f"/api/summary/week?end={end}", headers=h)
    assert r.status_code == 200, r.text
    return r.json()


def _log(client, h, day, food="white_rice", grams=50, slot="lunch"):
    r = log_intake(client, h, day, slot, food, grams)
    assert r.status_code == 201, r.text


# ---------- P1 ----------
def test_week_planned_basis_and_missing_days(client, auth):
    client.post("/api/menu/generate", json={"start": DAY.isoformat(), "days": 5}, headers=auth)
    w = _week(client, auth, DAY + timedelta(days=6))  # 2 ngày cuối cửa sổ không có thực đơn
    assert w["basis"] == "planned" and len(w["days"]) == 7 and w["days_counted"] == 5
    assert [d["planned"] is not None for d in w["days"]] == [True, True, True, True, True, False, False]
    assert not any(d["logged"] or d["eaten"] for d in w["days"])
    target = w["days"][0]["target"]["energy_kcal"]
    assert abs(w["average"]["energy_kcal"] - target) <= 0.1 * target and w["energy_within_days"] == 5
    assert w["low_nutrients"] == [] or all(x["days_low"] >= 4 for x in w["low_nutrients"])


def test_week_empty(client, auth):
    w = _week(client, auth, DAY)
    assert w["basis"] == "planned" and w["days_counted"] == 0 and w["average"] == {} and w["low_nutrients"] == []


def test_week_eaten_basis_only_logged_days(client, auth):
    client.post("/api/menu/generate", json={"start": DAY.isoformat(), "days": 7}, headers=auth)
    _log(client, auth, DAY, grams=100)
    _log(client, auth, DAY + timedelta(days=2), grams=300)
    w = _week(client, auth, DAY + timedelta(days=6))
    assert w["basis"] == "eaten" and w["days_counted"] == 2
    logged = [d for d in w["days"] if d["logged"]]
    assert [d["day"] for d in logged] == [DAY.isoformat(), (DAY + timedelta(days=2)).isoformat()]
    kcal = [d["eaten"]["energy_kcal"] for d in logged]
    assert kcal[1] == pytest.approx(3 * kcal[0]) and w["average"]["energy_kcal"] == pytest.approx(sum(kcal) / 2)
    assert w["energy_within_days"] == 0  # chỉ ăn ít cơm ⇒ xa mục tiêu
    assert w["low_nutrients"] == []  # mới 2 ngày ghi ⇒ chưa đủ 4/7 ngày


def test_week_low_nutrients_suggestions_respect_allergy_and_dislikes(client):
    h = register(client, profile={**BASE_PROFILE, "allergies": ["shellfish", "fish"]})
    for i in range(4):
        _log(client, h, DAY + timedelta(days=i))
    w = _week(client, h, DAY + timedelta(days=6))
    low = {x["nutrient"]: x for x in w["low_nutrients"]}
    assert {"fiber_g", "calcium_mg", "iron_mg", "zinc_mg", "vitamin_d_ug"} <= set(low)
    cat = load_seed_catalog()
    for x in low.values():
        assert x["days_low"] == 4 and len(x["suggestions"]) == 3
        for sgg in x["suggestions"]:
            f = cat.food(sgg["food_code"])
            assert not {"shellfish", "fish"} & set(f.tags) and f.category != "snack" and f.slots
    first = low["iron_mg"]["suggestions"][0]["food_code"]
    assert client.post("/api/preferences/dislikes", json={"kind": "food", "code": first}, headers=h).status_code == 201
    again = {x["nutrient"]: x for x in _week(client, h, DAY + timedelta(days=6))["low_nutrients"]}
    assert first not in {sgg["food_code"] for sgg in again["iron_mg"]["suggestions"]}


def test_week_english_names(client, auth):
    for i in range(4):
        _log(client, auth, DAY + timedelta(days=i))
    w = client.get(f"/api/summary/week?end={DAY + timedelta(days=6)}", headers={**auth, "Accept-Language": "en"})
    names = [sgg["name"] for x in w.json()["low_nutrients"] for sgg in x["suggestions"]]
    assert names and all(n.isascii() for n in names)


# ---------- P2 ----------
def _export(client, h, pw=PW):
    return client.post("/api/me/export", json={"password": pw}, headers=h)


def test_export_complete_and_no_secrets(client, auth):
    client.post("/api/menu/generate", json={"start": DAY.isoformat(), "days": 2}, headers=auth)
    _log(client, auth, DAY)
    client.post("/api/pantry", json={"day": DAY.isoformat(), "food_code": "egg", "grams": 100}, headers=auth)
    client.put("/api/health-limits", json={"condition": None, "limits": {"sodium_mg_max": 1800}}, headers=auth)
    client.post("/api/preferences/dislikes", json={"kind": "food", "code": "bitter_melon"}, headers=auth)
    client.post("/api/chat", json={"message": "tôi muốn ăn chuối"}, headers=auth)
    r = _export(client, auth)
    assert r.status_code == 200 and "attachment" in r.headers["content-disposition"]
    assert r.headers["cache-control"] == "no-store"
    d = r.json()
    for k in ("schema_version", "exported_at", "account", "profile", "health_limits", "dislikes", "menus", "intake",
              "pantry", "chat_history", "custom_foods", "safety_event_counts"):
        assert k in d, k
    assert d["profile"]["weight_kg"] == BASE_PROFILE["weight_kg"]
    assert d["health_limits"][0]["limits"]["sodium_mg_max"] == 1800
    assert len(d["menus"]) == 2 and d["intake"][0]["food_code"] == "white_rice" and d["pantry"][0]["grams"] == 100
    assert [m["text"] for m in d["chat_history"] if m["role"] == "user"] == ["tôi muốn ăn chuối"]
    assert d["dislikes"][0]["code"] == "bitter_melon"
    raw = json.dumps(d).lower()
    for secret in ("password", "hash", "argon", "refresh", "token", PW):
        assert secret not in raw, secret


def test_export_other_users_data_not_included(client, auth):
    other = register(client, email="b@example.com", profile={**BASE_PROFILE, "weight_kg": 77})
    _log(client, other, DAY, food="banana", grams=120)
    client.post("/api/chat", json={"message": "tôi muốn ăn gà"}, headers=other)
    d = _export(client, auth).json()
    assert d["account"]["email"] == "a@example.com" and d["intake"] == [] and d["chat_history"] == []
    assert "b@example.com" not in json.dumps(d) and d["profile"]["weight_kg"] != 77


def test_export_wrong_password_and_rate_limit(client, auth):
    r = _export(client, auth, pw="sai-mat-khau")
    assert r.status_code == 401 and r.json()["code"] == "BAD_PASSWORD"
    n, _ = RL.EXPORT
    for _ in range(n - 1):
        assert _export(client, auth).status_code == 200
    r = _export(client, auth)
    assert r.status_code == 429 and r.json()["code"] == "RATE_LIMITED"


def test_export_requires_login(client):
    assert client.post("/api/me/export", json={"password": PW}).status_code == 401
