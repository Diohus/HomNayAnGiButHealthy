"""Vòng 8 N2: ảnh bữa ăn ⇒ bản nháp nhật ký (LLM vision giả lập) + ghi theo lô."""

import base64
import io

from PIL import Image
from sqlalchemy import func, select

from app.core import ratelimit as RL
from app.db import models as M
from app.foods import resolve as RS
from tests.api.test_health_limits import _png
from tests.conftest import BASE_PROFILE, intake_rows, register

DAY = "2026-10-21"
URL = "/api/intake/photo"
RES = {"food_code": None, "dish_code": None, "components": [], "confidence": 0.9, "alternatives": []}


class FakeVision:
    """Ảnh ⇒ `photo`; lượt resolver K1 (văn bản) ⇒ `resolved`. Ghi lại ảnh đã gửi để kiểm tra metadata."""
    name = "fake"

    def __init__(self, photo, resolved=()):
        self.photo, self.resolved, self.images, self.calls = photo, list(resolved), [], 0

    def complete_json(self, system, user, schema, schema_name):
        self.calls += 1
        return {"results": [{**RES, **r} for r in self.resolved]}

    def complete_json_with_image(self, system, user, image_b64, schema, schema_name):
        self.calls += 1
        self.images.append(image_b64)
        return self.photo


COM_TAM = {"is_food_photo": True, "items": [
    {"name": "cơm trắng", "estimated_grams": 200, "confidence": 0.8},
    {"name": "sườn nướng", "estimated_grams": 120, "confidence": 0.7},
    {"name": "dưa leo", "estimated_grams": 9000, "confidence": 0.9},  # bịa khối lượng ⇒ bị kẹp
    {"name": "tôm chiên", "estimated_grams": 50, "confidence": 0.6},
    {"name": "thứ gì đó", "estimated_grams": 30, "confidence": 0.2},
]}
RESOLVED = [{"mention": "sườn nướng", "kind": "ingredient", "food_code": "pork_ribs"},
            {"mention": "tôm chiên", "kind": "ingredient", "food_code": "shrimp"},
            {"mention": "thứ gì đó", "kind": "unknown", "confidence": 0.1}]


def _fake(monkeypatch, photo, resolved=RESOLVED):
    RS.cache.clear()
    fp = FakeVision(photo, resolved)
    monkeypatch.setattr("app.api.routes.get_provider", lambda s: fp)
    return fp


def _post(client, h, img=None, consent="true", **form):
    return client.post(URL, files={"file": ("m.jpg", img or _png(), "image/jpeg")},
                       data={"day": DAY, "consent_ai_processing": consent, **form}, headers=h)


def _count(engine) -> int:
    with engine.connect() as c:
        return c.execute(select(func.count()).select_from(M.IntakeEntry)).scalar()


def test_photo_draft_allergy_rejected_and_nothing_saved(client, engine, monkeypatch):
    h = register(client, profile={**BASE_PROFILE, "allergies": ["shellfish"]})
    _fake(monkeypatch, COM_TAM)
    r = _post(client, h, slot="lunch")
    assert r.status_code == 200, r.text
    j = r.json()
    by = {e["food_code"]: e for e in j["entries"]}
    assert set(by) == {"white_rice", "pork_ribs", "cucumber"}
    assert all(e["source"] == "ai_estimate" for e in j["entries"]) and j["slot"] == "lunch" and j["is_food_photo"]
    assert by["cucumber"]["grams"] <= 2 * 300 and by["white_rice"]["grams"] == 200  # kẹp khối lượng
    assert [x["food_code"] for x in j["rejected"]] == ["shrimp"] and j["rejected"][0]["reason"]
    assert j["unresolved"] == ["thứ gì đó"]
    assert _count(engine) == 0  # phân tích KHÔNG ghi gì


def test_photo_component_vs_dish(client, auth, monkeypatch):
    _fake(monkeypatch, {"is_food_photo": True, "items": [
        {"name": "cơm tấm", "estimated_grams": 180, "confidence": 0.8},  # phần cơm của đĩa cơm tấm
        {"name": "phở bò", "estimated_grams": 400, "confidence": 0.8}]}, resolved=[])
    by = {e["food_code"]: e["grams"] for e in _post(client, auth).json()["entries"]}
    assert by["white_rice"] == 180 and "pork_ribs" not in by
    assert by["fresh_rice_noodles"] == 200 and by["beef_sirloin"] == 200  # món: nguyên liệu chính chia đều


def test_not_food_photo_422(client, auth, monkeypatch):
    _fake(monkeypatch, {"is_food_photo": False, "items": []})
    r = _post(client, auth)
    assert r.status_code == 422 and r.json()["code"] == "NOT_FOOD_PHOTO"


def test_consent_required_and_invalid_image(client, auth, monkeypatch):
    fp = _fake(monkeypatch, COM_TAM)
    assert _post(client, auth, consent="false").json()["code"] == "AI_CONSENT_REQUIRED"
    assert _post(client, auth, img=b"not an image").json()["code"] == "INVALID_IMAGE"
    assert fp.calls == 0


def test_exif_stripped(client, auth, monkeypatch):
    fp = _fake(monkeypatch, COM_TAM)
    assert _post(client, auth).status_code == 200
    im = Image.open(io.BytesIO(base64.b64decode(fp.images[0])))
    assert im.format == "JPEG" and not im.getexif() and "exif" not in im.info


def test_photo_rate_limit(client, auth, monkeypatch):
    _fake(monkeypatch, COM_TAM)
    n, _ = RL.PHOTO
    for _ in range(n):
        assert _post(client, auth).status_code == 200
    r = _post(client, auth)
    assert r.status_code == 429 and r.json()["code"] == "RATE_LIMITED"


def test_batch_writes_all(client, auth, engine):
    body = {"day": DAY, "entries": [
        {"slot": "lunch", "food_code": "white_rice", "grams": 200, "source": "ai_estimate"},
        {"slot": "lunch", "food_code": "pork_ribs", "grams": 120, "source": "ai_estimate"}]}
    r = client.post("/api/intake/batch", json=body, headers=auth)
    assert r.status_code == 201 and len(r.json()["ids"]) == 2
    entries = intake_rows(engine, DAY)
    assert {e["source"] for e in entries} == {"ai_estimate"} and _count(engine) == 2


def test_batch_allergen_writes_nothing(client, engine):
    h = register(client, profile={**BASE_PROFILE, "allergies": ["shellfish"]})
    body = {"day": DAY, "entries": [
        {"slot": "lunch", "food_code": "white_rice", "grams": 200, "source": "ai_estimate"},
        {"slot": "lunch", "food_code": "shrimp", "grams": 50, "source": "ai_estimate"}]}
    r = client.post("/api/intake/batch", json=body, headers=h)
    assert r.status_code == 422 and r.json()["code"] == "ALLERGEN_CONFLICT"
    assert _count(engine) == 0


def test_batch_size_limit(client, auth):
    one = {"slot": "lunch", "food_code": "white_rice", "grams": 100}
    r = client.post("/api/intake/batch", json={"day": DAY, "entries": [one] * 21}, headers=auth)
    assert r.status_code == 422 and r.json()["code"] == "INTAKE_BATCH_SIZE"
    assert client.post("/api/intake/batch", json={"day": DAY, "entries": []}, headers=auth).status_code == 422
