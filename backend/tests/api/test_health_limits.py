"""Vòng 4 (H2/H3): giới hạn sức khỏe do người dùng cung cấp + trích xuất từ ảnh/văn bản bằng LLM (giả lập)."""

import base64
import io

import pytest
from PIL import Image
from sqlalchemy import func, select

from app.core import ratelimit as RL
from app.db import models as M
from app.nutrition import HealthLimits, HealthProfileIn, compute_needs
from tests.conftest import BASE_PROFILE, register

EN = {"Accept-Language": "en"}
URL = "/api/health-limits/extract"


class FakeVision:
    """Provider giả: ghi lại đầu vào (để kiểm tra ảnh đã bỏ metadata), trả kết quả soạn sẵn."""

    name = "fake"

    def __init__(self, out):
        self.out, self.calls, self.images, self.users = out, 0, [], []

    def complete_json(self, system, user, schema, schema_name):
        self.calls += 1
        self.users.append(user)
        return self.out

    def complete_json_with_image(self, system, user, image_b64, schema, schema_name):
        self.images.append(image_b64)
        return self.complete_json(system, user, schema, schema_name)


def _fake(monkeypatch, out):
    fp = FakeVision(out)
    monkeypatch.setattr("app.api.routes.get_provider", lambda s: fp)
    return fp


def _png(w=40, h=20, exif=True) -> bytes:
    im = Image.new("RGB", (w, h), "white")
    buf = io.BytesIO()
    if exif:
        ex = Image.Exif()
        ex[0x0112] = 6  # Orientation: xoay 90°
        ex[0x010F] = "PhoneMaker"  # Make
        ex[0x8825] = {2: (10.0, 46.0, 0.0)}  # GPSInfo
        im.save(buf, "JPEG", exif=ex.tobytes())
    else:
        im.save(buf, "PNG")
    return buf.getvalue()


def _count(engine, model) -> int:
    with engine.connect() as c:
        return c.execute(select(func.count()).select_from(model)).scalar()


# ---------- CRUD ----------
def test_health_limits_crud_and_encrypted(client, auth, engine):
    r = client.put("/api/health-limits", json={"condition": None, "limits": {"sodium_mg_max": 2000}}, headers=auth)
    assert r.status_code == 200 and r.json()["condition"] is None and r.json()["source"] == "manual"
    r = client.put("/api/health-limits", json={"condition": "kidney", "limits": {"protein_g_max": 60}},
                   headers=auth)
    kid = r.json()["id"]
    # upsert theo (user, condition)
    client.put("/api/health-limits", json={"condition": "kidney", "limits": {"protein_g_max": 50},
                                           "source": "document"}, headers=auth)
    client.put("/api/health-limits", json={"condition": None, "limits": {"sodium_mg_max": 1800}}, headers=auth)
    rows = client.get("/api/health-limits", headers=auth).json()
    assert len(rows) == 2
    by = {x["condition"]: x for x in rows}
    assert by["kidney"]["limits"]["protein_g_max"] == 50 and by["kidney"]["source"] == "document"
    assert by[None]["limits"]["sodium_mg_max"] == 1800
    with engine.connect() as c:
        raw = c.execute(select(M.HealthLimit.encrypted_payload)).scalars().all()
    assert all(b"protein" not in x and b"sodium" not in x for x in raw)
    # người khác không xóa được
    other = register(client, email="o@example.com")
    assert client.delete(f"/api/health-limits/{kid}", headers=other).status_code == 404
    assert client.delete(f"/api/health-limits/{kid}", headers=auth).status_code == 204
    assert len(client.get("/api/health-limits", headers=auth).json()) == 1


@pytest.mark.parametrize("limits", [{}, {"carb_g_max": None}])
def test_health_limits_requires_a_value(client, auth, limits):
    r = client.put("/api/health-limits", json={"limits": limits}, headers=auth)
    assert r.status_code == 422 and r.json()["code"] == "LIMITS_REQUIRED"


@pytest.mark.parametrize("limits", [{"carb_g_max": 10}, {"carb_g_max": 700}, {"fat_g_max": 5}, {"fat_g_max": 400},
                                    {"sodium_mg_max": 0}, {"unknown_max": 1}])
def test_health_limits_ranges(client, auth, limits):
    assert client.put("/api/health-limits", json={"limits": limits}, headers=auth).status_code == 422


def test_limits_deleted_with_account(client, auth, engine):
    client.put("/api/health-limits", json={"limits": {"sodium_mg_max": 2000}}, headers=auth)
    client.delete("/api/me", headers=auth)
    assert _count(engine, M.HealthLimit) == 0


# ---------- carb/béo + LIMITS_REDUCE_ENERGY ----------
def test_carb_fat_caps_reduce_energy_with_warning():
    p = HealthProfileIn(**BASE_PROFILE)
    base = compute_needs(p)
    n = compute_needs(p, HealthLimits(carb_g_max=100, fat_g_max=40), limit_sources={"carb_g_max": "document"})
    t = {x.code: x for x in n.targets}
    assert t["carb_g"].value <= 100 + 1e-6 and t["fat_g"].value <= 40 + 1e-6
    assert "LIMITS_REDUCE_ENERGY" in n.warnings and t["energy_kcal"].value < base.get("energy_kcal").value
    macro_kcal = 4 * t["protein_g"].value + 4 * t["carb_g"].value + 9 * t["fat_g"].value
    assert macro_kcal == pytest.approx(t["energy_kcal"].value, rel=0.01)
    # không bù ngoài AMDR: đạm ≤ 35% năng lượng gốc
    assert 4 * t["protein_g"].value <= 0.35 * base.get("energy_kcal").value + 1e-6
    assert t["carb_g"].adjusted_for[-1] == "user_limit" and "tài liệu" in t["carb_g"].reference.source


def test_small_carb_cap_absorbed_by_fat_without_warning():
    p = HealthProfileIn(**BASE_PROFILE)
    base = {x.code: x.value for x in compute_needs(p).targets}
    n = compute_needs(p, HealthLimits(carb_g_max=round(base["carb_g"] - 10)))
    t = {x.code: x.value for x in n.targets}
    assert "LIMITS_REDUCE_ENERGY" not in n.warnings and t["energy_kcal"] == pytest.approx(base["energy_kcal"])
    assert t["fat_g"] > base["fat_g"]


# ---------- trích xuất ----------
TEXT = ("Chỉ định: Natri < 87 mmol/ngày. Đạm tối đa 50 g/ngày. Kali 2000mg/ngày. Năng lượng 1800 kcal. "
        "Hạn chế đồ chiên rán.")
OUT = {
    "items": [
        {"field": "sodium_mg_max", "value": 87, "unit": "mmol", "quote": "Natri < 87 mmol/ngày"},
        {"field": "protein_g_max", "value": 50, "unit": "g", "quote": "đạm tối đa 50 g/ngày"},  # khác hoa/thường
        {"field": "potassium_mg_max", "value": 20000, "unit": "mg", "quote": "Kali 2000mg/ngày"},  # đọc sai
        {"field": "phosphorus_mg_max", "value": 800, "unit": "mg", "quote": "Phốt pho 800 mg"},  # không có thật
        {"field": "energy_kcal_max", "value": 1800, "unit": "g", "quote": "Năng lượng 1800 kcal"},  # sai đơn vị
    ],
    "other_instructions": ["Hạn chế đồ chiên rán.", "  "],
    "language": "vi",
}


def test_extract_text_post_checks(client, auth, engine, monkeypatch):
    fp = _fake(monkeypatch, OUT)
    r = client.post(URL, data={"text": TEXT, "consent_ai_processing": "true"}, headers=auth)
    assert r.status_code == 200, r.text
    j = r.json()
    assert j["limits"] == {"sodium_mg_max": 2001.0, "protein_g_max": 50.0}  # 87 mmol × 23
    sodium = next(i for i in j["items"] if i["field"] == "sodium_mg_max")
    assert sodium["original_unit"] == "mmol" and sodium["unit"] == "mg" and sodium["quote"] == "Natri < 87 mmol/ngày"
    reasons = {x["field"]: x["reason"] for x in j["rejected"]}
    assert reasons == {"potassium_mg_max": "out_of_range", "phosphorus_mg_max": "quote_not_found",
                       "energy_kcal_max": "unit_mismatch"}
    assert j["other_instructions"] == ["Hạn chế đồ chiên rán."]
    assert fp.calls == 1 and TEXT in fp.users[0] and not fp.images
    assert _count(engine, M.HealthLimit) == 0  # chỉ là bản nháp


def test_extract_unit_conversions(client, auth, monkeypatch):
    out = {"items": [
        {"field": "potassium_mg_max", "value": 50, "unit": "mmol", "quote": "K 50 mmol"},
        {"field": "phosphorus_mg_max", "value": 0.8, "unit": "g", "quote": "P 0.8 g"},
        {"field": "sodium_mg_max", "value": 2, "unit": "g", "quote": "Na 2 g"},
        {"field": "protein_g_max", "value": 40, "unit": "mmol", "quote": "protein 40"},
    ], "other_instructions": [], "language": "en"}
    _fake(monkeypatch, out)
    r = client.post(URL, data={"text": "K 50 mmol; P 0.8 g; Na 2 g; protein 40", "consent_ai_processing": "true"},
                    headers={**auth, **EN})
    j = r.json()
    assert j["limits"] == {"potassium_mg_max": 1955.0, "phosphorus_mg_max": 800.0, "sodium_mg_max": 2000.0}
    assert j["rejected"][0]["reason"] == "unit_mismatch"
    assert j["rejected"][0]["reason_text"] == "The unit doesn't match this limit."


def test_extract_requires_consent(client, auth, monkeypatch):
    fp = _fake(monkeypatch, OUT)
    r = client.post(URL, data={"text": TEXT}, headers=auth)
    assert r.status_code == 422 and r.json()["code"] == "AI_CONSENT_REQUIRED"
    r = client.post(URL, data={"text": TEXT, "consent_ai_processing": "false"}, headers=auth)
    assert r.json()["code"] == "AI_CONSENT_REQUIRED" and fp.calls == 0


def test_extract_needs_exactly_one_input(client, auth, monkeypatch):
    _fake(monkeypatch, OUT)
    r = client.post(URL, data={"consent_ai_processing": "true"}, headers=auth)
    assert r.json()["code"] == "EXTRACT_INPUT_REQUIRED"
    r = client.post(URL, data={"text": "abc", "consent_ai_processing": "true"},
                    files={"file": ("a.png", _png(exif=False), "image/png")}, headers=auth)
    assert r.json()["code"] == "EXTRACT_INPUT_REQUIRED"
    r = client.post(URL, data={"text": "x" * 5001, "consent_ai_processing": "true"}, headers=auth)
    assert r.json()["code"] == "TEXT_TOO_LONG"


def test_extract_rejects_fake_image(client, auth, monkeypatch):
    fp = _fake(monkeypatch, OUT)
    pdf = b"%PDF-1.4\n1 0 obj << /Type /Catalog >> endobj\ntrailer<<>>\n%%EOF"
    r = client.post(URL, data={"consent_ai_processing": "true"}, files={"file": ("don.png", pdf, "image/png")},
                    headers=auth)
    assert r.status_code == 422 and r.json()["code"] == "INVALID_IMAGE" and fp.calls == 0
    gif = io.BytesIO()
    Image.new("RGB", (10, 10)).save(gif, "GIF")
    r = client.post(URL, data={"consent_ai_processing": "true"}, files={"file": ("a.jpg", gif.getvalue(), "image/jpeg")},
                    headers=auth)
    assert r.json()["code"] == "INVALID_IMAGE"


def test_extract_image_too_large(client, auth, monkeypatch):
    _fake(monkeypatch, OUT)
    big = b"\xff\xd8" + b"0" * (5 * 1024 * 1024)
    r = client.post(URL, data={"consent_ai_processing": "true"}, files={"file": ("a.jpg", big, "image/jpeg")},
                    headers=auth)
    assert r.status_code == 413 and r.json()["code"] == "FILE_TOO_LARGE"


def test_extract_image_strips_exif_and_rotates(client, auth, engine, monkeypatch):
    out = {"items": [{"field": "sodium_mg_max", "value": 1500, "unit": "mg", "quote": "Natri ≤ 1500 mg"}],
           "other_instructions": [], "language": "vi"}
    fp = _fake(monkeypatch, out)
    src = _png(40, 20, exif=True)
    assert Image.open(io.BytesIO(src)).getexif()  # ảnh gốc có EXIF (hãng máy, GPS, hướng)
    r = client.post(URL, data={"consent_ai_processing": "true"}, files={"file": ("don.jpg", src, "image/jpeg")},
                    headers=auth)
    assert r.status_code == 200, r.text
    assert r.json()["limits"] == {"sodium_mg_max": 1500.0}  # ảnh: không đối chiếu được trích dẫn với văn bản
    sent = base64.b64decode(fp.images[0])
    im = Image.open(io.BytesIO(sent))
    assert im.format == "JPEG" and not im.getexif() and "exif" not in im.info
    assert b"PhoneMaker" not in sent and b"Exif" not in sent
    assert im.size == (20, 40)  # đã xoay theo EXIF trước khi bỏ metadata
    assert _count(engine, M.HealthLimit) == 0


def test_extract_large_image_downscaled(client, auth, monkeypatch):
    fp = _fake(monkeypatch, {"items": [], "other_instructions": [], "language": "other"})
    buf = io.BytesIO()
    Image.new("RGBA", (3000, 1500), (255, 0, 0, 128)).save(buf, "PNG")
    r = client.post(URL, data={"consent_ai_processing": "true"}, files={"file": ("a.png", buf.getvalue(), "image/png")},
                    headers=auth)
    assert r.status_code == 200 and r.json() == {"limits": {}, "items": [], "rejected": [],
                                                 "other_instructions": [], "language": "other"}
    assert max(Image.open(io.BytesIO(base64.b64decode(fp.images[0]))).size) == 2000


def test_extract_llm_unavailable(client, auth):
    # LLM_API_KEY trống trong test ⇒ provider None
    r = client.post(URL, data={"text": TEXT, "consent_ai_processing": "true"}, headers={**auth, **EN})
    assert r.status_code == 503 and r.json()["code"] == "EXTRACTION_UNAVAILABLE"
    assert "enter limits by hand" in r.json()["message"]


def test_extract_rate_limited(client, auth, monkeypatch):
    _fake(monkeypatch, OUT)
    for _ in range(RL.EXTRACT[0]):
        assert client.post(URL, data={"text": TEXT, "consent_ai_processing": "true"}, headers=auth).status_code == 200
    r = client.post(URL, data={"text": TEXT, "consent_ai_processing": "true"}, headers=auth)
    assert r.status_code == 429 and r.json()["code"] == "RATE_LIMITED"


def test_extract_then_save_as_document(client, auth, monkeypatch):
    _fake(monkeypatch, OUT)
    draft = client.post(URL, data={"text": TEXT, "consent_ai_processing": "true"}, headers=auth).json()
    r = client.put("/api/health-limits", json={"condition": None, "limits": draft["limits"], "source": "document"},
                   headers=auth)
    assert r.status_code == 200 and r.json()["limits"]["sodium_mg_max"] == 2001.0
