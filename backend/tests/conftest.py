import os

from cryptography.fernet import Fernet

# Cấu hình test trước khi import app (settings được cache)
os.environ.setdefault("HEALTH_DATA_KEY", Fernet.generate_key().decode())
os.environ.setdefault("JWT_SECRET", "test-secret-test-secret-test-secret-123")
os.environ["LLM_API_KEY"] = ""  # mặc định: không gọi LLM thật
os.environ.setdefault("DATABASE_URL", "sqlite://")

from app.core import config  # noqa: E402

config.Settings.model_config["env_file"] = None  # test độc lập với .env thật (có API key)

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from app.core.ratelimit import limiter  # noqa: E402
from app.db import foods_repo  # noqa: E402
from app.db import session as dbs  # noqa: E402
from app.db.session import Base  # noqa: E402
from app.foods import load_seed_catalog  # noqa: E402

BASE_PROFILE = {
    "sex": "female", "age": 30, "height_cm": 160, "weight_kg": 55, "activity_level": "moderate", "goal": "maintain",
}


@pytest.fixture(scope="session")
def catalog():
    return load_seed_catalog()


@pytest.fixture(autouse=True)
def _reset_rate_limits():
    from app.chat import parser
    from app.foods import resolve

    limiter.reset()
    parser._cache.clear()  # cache LLM in-memory không được rò giữa các test
    resolve.cache.clear()
    yield
    limiter.reset()


@pytest.fixture()
def engine():
    # init_engine tự bật PRAGMA foreign_keys cho SQLite (như khi chạy app thật)
    eng = dbs.init_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)

    import app.db.models  # noqa: F401

    Base.metadata.create_all(eng)
    with dbs._SessionLocal() as s:
        foods_repo.seed(s)
    yield eng
    eng.dispose()


@pytest.fixture()
def client(engine):
    from app.main import app

    return TestClient(app)


def register(client, email="a@example.com", profile=None):
    r = client.post("/api/auth/register", json={"email": email, "password": "matkhau-an-toan"})
    assert r.status_code == 201, r.text
    h = {"Authorization": f"Bearer {r.json()['access_token']}"}
    if profile is not False:
        r = client.put("/api/profile", json=profile or BASE_PROFILE, headers=h)
        assert r.status_code == 200, r.text
    return h


@pytest.fixture()
def auth(client):
    return register(client)


def log_intake(client, h, day, slot, food_code, grams):
    """Ghi MỘT mục nhật ký qua POST /intake/batch (lô 1 mục)."""
    d = day if isinstance(day, str) else day.isoformat()
    return client.post("/api/intake/batch", json={"day": d, "entries": [
        {"slot": slot, "food_code": food_code, "grams": grams}]}, headers=h)


def intake_rows(engine, day) -> list[dict]:
    """Nhật ký của một ngày đọc thẳng từ DB (ngày có thể chưa có thực đơn nên không đọc qua GET /menu)."""
    from datetime import date

    from sqlalchemy import select

    from app.db import models as M

    d = date.fromisoformat(day) if isinstance(day, str) else day
    with engine.connect() as c:
        rows = c.execute(select(M.IntakeEntry).where(M.IntakeEntry.day == d).order_by(M.IntakeEntry.id)).all()
    return [{"id": r.id, "slot": r.slot, "food_code": r.food_code, "grams": r.grams, "source": r.source} for r in rows]
