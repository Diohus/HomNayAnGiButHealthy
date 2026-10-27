"""Mã hóa field-level cho dữ liệu sức khỏe khi lưu (Fernet = AES-128-CBC + HMAC-SHA256)."""

import json

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import get_settings


class HealthDataCipher:
    def __init__(self, key: str):
        if not key:
            raise RuntimeError("HEALTH_DATA_KEY chưa được cấu hình")
        self._f = Fernet(key.encode())

    def encrypt(self, payload: dict) -> bytes:
        return self._f.encrypt(json.dumps(payload, separators=(",", ":")).encode())

    def decrypt(self, token: bytes) -> dict:
        try:
            return json.loads(self._f.decrypt(token))
        except InvalidToken as e:  # không log nội dung
            raise RuntimeError("Không giải mã được hồ sơ sức khỏe") from e


def get_cipher() -> HealthDataCipher:
    return HealthDataCipher(get_settings().health_data_key)
