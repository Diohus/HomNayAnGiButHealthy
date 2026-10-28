"""Vòng 10: dọn code — ghi nhật ký theo lô nạp catalog một lần, Ctx dựng một lần, slot kiểu Slot, hạn mức +/−."""

from datetime import date

from app.core import ratelimit as RL
from app.services import menu as MS
from tests.conftest import BASE_PROFILE, intake_rows, register

DAY = date(2026, 10, 21)


def test_batch_of_three_loads_catalogs_once(client, auth, engine, monkeypatch):
    calls = []
    real = MS.catalogs
    monkeypatch.setattr(MS, "catalogs", lambda *a, **k: calls.append(1) or real(*a, **k))
    body = {"day": DAY.isoformat(), "entries": [
        {"slot": "lunch", "food_code": "white_rice", "grams": 200},
        {"slot": "lunch", "food_code": "pork_ribs", "grams": 120},
        {"slot": "snack", "food_code": "banana", "grams": 100}]}
    r = client.post("/api/intake/batch", json=body, headers=auth)
    assert r.status_code == 201, r.text
    assert len(r.json()["ids"]) == 3 and len(calls) == 1
    assert [e["source"] for e in intake_rows(engine, DAY)] == ["manual"] * 3


def test_batch_rejects_chat_source(client, auth):
    body = {"day": DAY.isoformat(), "entries": [{"slot": "lunch", "food_code": "banana", "grams": 100,
                                                 "source": "chat"}]}
    assert client.post("/api/intake/batch", json=body, headers=auth).status_code == 422


def test_single_intake_routes_removed(client, auth):
    body = {"day": DAY.isoformat(), "slot": "snack", "food_code": "banana", "grams": 100}
    assert client.post("/api/intake", json=body, headers=auth).status_code in (404, 405)
    assert client.get(f"/api/intake?day={DAY}", headers=auth).status_code in (404, 405)


def test_get_menu_week_builds_ctx_once(client, auth, monkeypatch):
    assert client.post("/api/menu/generate", json={"start": DAY.isoformat(), "days": 7}, headers=auth).status_code == 200
    n = []

    class Counting(MS.Ctx):
        def __init__(self, *a, **k):
            n.append(1)
            super().__init__(*a, **k)

    monkeypatch.setattr(MS, "Ctx", Counting)
    r = client.get(f"/api/menu?start={DAY}&days=7", headers=auth)
    assert r.status_code == 200 and all(r.json()) and len(n) == 1


def test_get_menu_without_profile_or_menu_needs_no_ctx(client):
    h = register(client, profile=False)
    assert client.get(f"/api/menu?start={DAY}&days=3", headers=h).json() == [None, None, None]


def test_invalid_slot_is_422(client, auth):
    client.post("/api/menu/generate", json={"start": DAY.isoformat()}, headers=auth)
    for path in ("eaten", "swap", "recipe"):
        body = {"eaten": True} if path == "eaten" else None
        r = client.post(f"/api/menu/{DAY}/meals/brunch/{path}", json=body, headers=auth)
        assert r.status_code == 422, path
    r = client.post(f"/api/menu/{DAY}/adjust", json={"slot": "brunch", "food_code": "x", "delta_g": 10},
                    headers=auth)
    assert r.status_code == 422


def test_adjust_and_unlock_rate_limited(client, auth):
    client.post("/api/menu/generate", json={"start": DAY.isoformat()}, headers=auth)
    n, _ = RL.ADJUST
    assert n >= RL.SWAP[0]
    body = {"slot": "lunch", "food_code": "nope", "delta_g": 10}
    for _ in range(n - 1):  # món không có trong bữa ⇒ 404, vẫn tính lượt (chặn trước khi chạy solver)
        assert client.post(f"/api/menu/{DAY}/adjust", json=body, headers=auth).status_code == 404
    assert client.post(f"/api/menu/{DAY}/unlock", json={"slot": "lunch", "food_code": "nope"},
                       headers=auth).status_code == 404
    r = client.post(f"/api/menu/{DAY}/adjust", json=body, headers=auth)
    assert r.status_code == 429 and r.json()["code"] == "RATE_LIMITED"


def test_pantry_list_and_delete_via_service(client, auth):
    assert client.post("/api/pantry", json={"day": DAY.isoformat(), "food_code": "banana", "grams": 100},
                       headers=auth).status_code == 201
    rows = client.get(f"/api/pantry?day={DAY}", headers=auth).json()
    assert [(r["food_code"], r["grams"]) for r in rows] == [("banana", 100)]
    other = register(client, email="o@example.com")
    assert client.delete(f"/api/pantry/{rows[0]['id']}", headers=other).status_code == 204
    assert len(client.get(f"/api/pantry?day={DAY}", headers=auth).json()) == 1  # không xóa được đồ của người khác
    assert client.delete(f"/api/pantry/{rows[0]['id']}", headers=auth).status_code == 204
    assert client.get(f"/api/pantry?day={DAY}", headers=auth).json() == []


def test_pantry_allergen_message_unchanged(client):
    h = register(client, profile={**BASE_PROFILE, "allergies": ["shellfish"]})
    r = client.post("/api/pantry", json={"day": DAY.isoformat(), "food_code": "shrimp", "grams": 100},
                    headers={**h, "Accept-Language": "en"})
    assert r.status_code == 422 and r.json()["code"] == "ALLERGEN_CONFLICT"
    assert r.json()["params"] == {"food": "Shrimp", "reason": "shellfish allergy"}
    assert r.json()["reason"] == "allergy:shellfish"


def test_logout_revokes_refresh_token(client):
    r = client.post("/api/auth/register", json={"email": "lo@example.com", "password": "matkhau-an-toan"})
    rt = r.json()["refresh_token"]
    assert client.post("/api/auth/logout", json={"refresh_token": rt}).status_code == 204
    assert client.post("/api/auth/refresh", json={"refresh_token": rt}).status_code == 401
