"""A5 + F1: refresh token bị dùng lại ⇒ thu hồi mọi phiên, trừ trong khoảng ân hạn 30 s sau khi xoay vòng."""

from tests.conftest import register

PW = "matkhau-an-toan"


def _login(client, email="a@example.com"):
    r = client.post("/api/auth/login", json={"email": email, "password": PW})
    assert r.status_code == 200
    return r.json()["refresh_token"]


def test_refresh_rotates(client):
    register(client, profile=False)
    rt = _login(client)
    r = client.post("/api/auth/refresh", json={"refresh_token": rt})
    assert r.status_code == 200 and r.json()["refresh_token"] != rt


def test_refresh_reuse_revokes_all_sessions(client, engine):
    register(client, profile=False)
    other_device = _login(client)
    stolen = _login(client)
    rotated = client.post("/api/auth/refresh", json={"refresh_token": stolen}).json()["refresh_token"]
    _age_rotation(engine, 60)  # ngoài khoảng ân hạn
    # kẻ gian dùng lại token cũ ⇒ bị từ chối và mọi phiên bị thu hồi
    r = client.post("/api/auth/refresh", json={"refresh_token": stolen})
    assert r.status_code == 401 and r.json()["code"] == "INVALID_REFRESH"
    for t in (rotated, other_device):
        assert client.post("/api/auth/refresh", json={"refresh_token": t}).status_code == 401


def test_reuse_does_not_touch_other_users(client, engine):
    register(client, email="a@example.com", profile=False)
    register(client, email="b@example.com", profile=False)
    a = _login(client, "a@example.com")
    b = _login(client, "b@example.com")
    client.post("/api/auth/refresh", json={"refresh_token": a})
    _age_rotation(engine, 60)
    assert client.post("/api/auth/refresh", json={"refresh_token": a}).status_code == 401
    assert client.post("/api/auth/refresh", json={"refresh_token": b}).status_code == 200


def test_unknown_refresh_token_rejected(client):
    r = client.post("/api/auth/refresh", json={"refresh_token": "khong-ton-tai"})
    assert r.status_code == 401 and r.json()["code"] == "INVALID_REFRESH"


# ---- F1: khoảng ân hạn khi refresh song song ----
def _age_rotation(engine, seconds):
    """Giả lập thời gian: lùi rotated_at của mọi token đã xoay vòng."""
    from datetime import UTC, datetime, timedelta

    from sqlalchemy import update

    from app.db import models as M

    with engine.begin() as c:
        c.execute(update(M.RefreshToken).where(M.RefreshToken.rotated_at.is_not(None))
                  .values(rotated_at=datetime.now(UTC) - timedelta(seconds=seconds)))


def test_parallel_refresh_within_grace_keeps_session(client):
    register(client, profile=False)
    rt = _login(client)
    new = client.post("/api/auth/refresh", json={"refresh_token": rt}).json()["refresh_token"]
    # các request song song khác của cùng client gửi lại token cũ ⇒ chỉ bị từ chối
    for _ in range(3):
        r = client.post("/api/auth/refresh", json={"refresh_token": rt})
        assert r.status_code == 401 and r.json()["code"] == "INVALID_REFRESH"
    assert client.post("/api/auth/refresh", json={"refresh_token": new}).status_code == 200


def test_reuse_after_grace_revokes_all(client, engine):
    register(client, profile=False)
    rt = _login(client)
    new = client.post("/api/auth/refresh", json={"refresh_token": rt}).json()["refresh_token"]
    _age_rotation(engine, 31)
    assert client.post("/api/auth/refresh", json={"refresh_token": rt}).status_code == 401
    assert client.post("/api/auth/refresh", json={"refresh_token": new}).status_code == 401


def test_reuse_after_logout_revokes_all(client):
    register(client, profile=False)
    other = _login(client)
    rt = _login(client)
    assert client.post("/api/auth/logout", json={"refresh_token": rt}).status_code == 204
    assert client.post("/api/auth/refresh", json={"refresh_token": rt}).status_code == 401
    assert client.post("/api/auth/refresh", json={"refresh_token": other}).status_code == 401
