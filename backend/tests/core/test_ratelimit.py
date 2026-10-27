"""A3: giới hạn tần suất (cửa sổ trượt) cho đăng nhập, đăng ký, chat, công thức."""

import threading
from datetime import date

import pytest

from app.core import ratelimit as RL
from app.core.errors import AppError
from app.core.ratelimit import RateLimiter, limiter
from tests.conftest import register

DAY = date(2026, 10, 21)
PW = "matkhau-an-toan"


class FakeClock:
    def __init__(self):
        self.t = 1000.0

    def __call__(self):
        return self.t


# ---- đơn vị ----
def test_sliding_window_blocks_then_recovers():
    clk = FakeClock()
    rl = RateLimiter(clock=clk)
    for _ in range(3):
        rl.hit("k", 3, 60)
    with pytest.raises(AppError) as e:
        rl.hit("k", 3, 60)
    assert e.value.status == 429 and e.value.code == "RATE_LIMITED" and e.value.extra["retry_after_s"] == 60
    clk.t += 30
    with pytest.raises(AppError) as e:
        rl.hit("k", 3, 60)
    assert e.value.extra["retry_after_s"] == 30
    clk.t += 30  # lượt đầu trượt ra khỏi cửa sổ
    rl.hit("k", 3, 60)
    rl.hit("other", 3, 60)  # khóa khác độc lập


def test_retry_after_and_record_and_clear():
    clk = FakeClock()
    rl = RateLimiter(clock=clk)
    assert rl.retry_after("k", 2, 10) is None
    rl.record("k")
    rl.record("k")
    assert rl.retry_after("k", 2, 10) == 10
    rl.clear("k")
    assert rl.retry_after("k", 2, 10) is None


def test_thread_safe():
    rl = RateLimiter()
    ok = []

    def worker():
        for _ in range(50):
            try:
                rl.hit("k", 100, 60)
                ok.append(1)
            except AppError:
                pass

    threads = [threading.Thread(target=worker) for _ in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert len(ok) == 100


def test_sweep_drops_stale_keys(monkeypatch):
    monkeypatch.setattr(RL, "MAX_KEYS", 3)
    clk = FakeClock()
    rl = RateLimiter(clock=clk)
    for k in "abc":
        rl.hit(k, 5, 60)
    clk.t += RL.MAX_WINDOW_S + 1
    rl.hit("d", 5, 60)
    assert set(rl._hits) == {"d"}


# ---- API ----
def test_login_locked_after_5_failures(client):
    register(client, email="u@example.com", profile=False)
    bad = {"email": "u@example.com", "password": "sai-mat-khau"}
    for _ in range(RL.LOGIN_FAILURES[0]):
        assert client.post("/api/auth/login", json=bad).status_code == 401
    r = client.post("/api/auth/login", json=bad)
    assert r.status_code == 429 and r.json()["code"] == "RATE_LIMITED" and r.json()["retry_after_s"] > 0
    # đúng mật khẩu cũng bị chặn trong lúc khóa (không để lộ mật khẩu đúng qua mã trả về)
    assert client.post("/api/auth/login", json={"email": "u@example.com", "password": PW}).status_code == 429
    # email khác cùng IP không bị ảnh hưởng
    register(client, email="v@example.com", profile=False)
    assert client.post("/api/auth/login", json={"email": "v@example.com", "password": PW}).status_code == 200


def test_login_limited_per_ip_across_emails(client):
    """F2: dò nhiều email từ cùng một IP (credential stuffing)."""
    register(client, email="u@example.com", profile=False)
    n = RL.LOGIN_FAILURES_IP[0]
    for i in range(n):  # mỗi email chỉ sai 1 lần ⇒ không chạm ngưỡng theo (email, IP)
        assert client.post("/api/auth/login", json={"email": f"x{i}@example.com", "password": "sai-mat-khau"}
                           ).status_code == 401
    r = client.post("/api/auth/login", json={"email": "new@example.com", "password": "sai-mat-khau"})
    assert r.status_code == 429 and r.json()["code"] == "RATE_LIMITED"
    assert client.post("/api/auth/login", json={"email": "u@example.com", "password": PW}).status_code == 429


def test_login_success_does_not_reset_ip_counter(client):
    register(client, email="u@example.com", profile=False)
    for i in range(RL.LOGIN_FAILURES_IP[0] - 1):
        client.post("/api/auth/login", json={"email": f"x{i}@example.com", "password": "sai-mat-khau"})
    assert client.post("/api/auth/login", json={"email": "u@example.com", "password": PW}).status_code == 200
    client.post("/api/auth/login", json={"email": "y@example.com", "password": "sai-mat-khau"})
    assert client.post("/api/auth/login", json={"email": "z@example.com", "password": "sai-mat-khau"}
                       ).status_code == 429


def test_login_success_resets_failures(client):
    register(client, email="u@example.com", profile=False)
    bad = {"email": "u@example.com", "password": "sai-mat-khau"}
    for _ in range(RL.LOGIN_FAILURES[0] - 1):
        client.post("/api/auth/login", json=bad)
    assert client.post("/api/auth/login", json={"email": "u@example.com", "password": PW}).status_code == 200
    assert client.post("/api/auth/login", json=bad).status_code == 401


def test_register_limited_per_ip(client):
    for i in range(RL.REGISTER[0]):
        assert client.post("/api/auth/register", json={"email": f"r{i}@example.com", "password": PW}).status_code == 201
    r = client.post("/api/auth/register", json={"email": "late@example.com", "password": PW})
    assert r.status_code == 429 and r.json()["code"] == "RATE_LIMITED"


def test_chat_limited_per_user(client, auth):
    for _ in range(RL.CHAT[0]):
        assert client.post("/api/chat", json={"message": "xin chào"}, headers=auth).status_code == 200
    r = client.post("/api/chat", json={"message": "xin chào"}, headers=auth)
    assert r.status_code == 429 and r.json()["code"] == "RATE_LIMITED"
    limiter.reset()  # tránh giới hạn đăng ký khi tạo user thứ hai
    other = register(client, email="other@example.com")
    assert client.post("/api/chat", json={"message": "xin chào"}, headers=other).status_code == 200


def test_recipe_limited_per_user(client, auth):
    m = client.post("/api/menu/generate", json={"start": DAY.isoformat()}, headers=auth).json()[0]
    slot = m["plan"]["meals"][0]["slot"]
    url = f"/api/menu/{DAY}/meals/{slot}/recipe"
    for _ in range(RL.RECIPE[0]):
        assert client.post(url, headers=auth).status_code == 200
    r = client.post(url, headers=auth)
    assert r.status_code == 429 and r.json()["code"] == "RATE_LIMITED"
