"""A1: cấu hình bảo mật yếu/sai ⇒ app không khởi động."""

import pytest
from cryptography.fernet import Fernet

from app.core.config import Settings, validate_settings

GOOD_SECRET = "x" * 48
GOOD_KEY = Fernet.generate_key().decode()


def _settings(**kw) -> Settings:
    return Settings(_env_file=None, **{"jwt_secret": GOOD_SECRET, "health_data_key": GOOD_KEY, **kw})


def test_valid_settings_ok():
    validate_settings(_settings())


def test_default_jwt_secret_is_empty():
    assert Settings(_env_file=None, jwt_secret="").jwt_secret == ""
    assert Settings.model_fields["jwt_secret"].default == ""


@pytest.mark.parametrize("secret", ["", "change-me", "short-secret", "x" * 31, "CHANGE-ME"])
def test_weak_jwt_secret_rejected(secret):
    with pytest.raises(RuntimeError, match="JWT_SECRET"):
        validate_settings(_settings(jwt_secret=secret))


@pytest.mark.parametrize("key", ["", "not-a-fernet-key", "a" * 44, Fernet.generate_key().decode()[:-4]])
def test_bad_fernet_key_rejected(key):
    with pytest.raises(RuntimeError, match="HEALTH_DATA_KEY") as e:
        validate_settings(_settings(health_data_key=key))
    assert "JWT_SECRET" not in str(e.value)


def test_error_lists_both_and_hides_values():
    with pytest.raises(RuntimeError) as e:
        validate_settings(_settings(jwt_secret="change-me", health_data_key="sai-khoa-bi-mat"))
    msg = str(e.value)
    assert "JWT_SECRET" in msg and "HEALTH_DATA_KEY" in msg
    assert "sai-khoa-bi-mat" not in msg


def test_create_app_refuses_to_start(monkeypatch):
    from app import main
    from app.core import config

    monkeypatch.setattr(config, "get_settings", lambda: _settings(jwt_secret="change-me"))
    monkeypatch.setattr(main, "get_settings", config.get_settings)
    with pytest.raises(RuntimeError, match="JWT_SECRET"):
        main.create_app()
