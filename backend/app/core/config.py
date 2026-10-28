from functools import lru_cache

from cryptography.fernet import Fernet
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Chạy từ gốc repo (.env) hoặc từ backend/ (../.env). File sau ghi đè file trước.
    model_config = SettingsConfigDict(env_file=(".env", "../.env"), extra="ignore")

    database_url: str = "postgresql+psycopg://homnayangi:homnayangi@localhost:5432/homnayangi"
    jwt_secret: str = ""  # bắt buộc, xem validate_settings()
    access_token_minutes: int = 15
    refresh_token_days: int = 7
    # Khóa Fernet (base64 32 byte) để mã hóa hồ sơ sức khỏe khi lưu.
    health_data_key: str = ""
    cors_origins: str = "http://localhost:5173"

    # LLM: chỉ "openai" (OpenAI-compatible) được bật mặc định.
    # Các provider khác (anthropic, ...) ẩn sau cờ llm_experimental_providers.
    llm_provider: str = "openai"
    llm_experimental_providers: bool = False
    llm_model: str = "gpt-6-luna"
    llm_base_url: str = "https://api.openai.com/v1"
    llm_api_key: str = ""
    llm_timeout_s: float = 15.0
    llm_max_retries: int = 2
    # N1: hiểu câu chat bằng 1 lượt LLM (ý định + món). TẮT mặc định: đo thật (scripts/bench_chat.py) cho thấy
    # đường 2 bước cũ nhanh hơn (đa số câu chỉ cần 1 lượt parse; prompt gộp lớn hơn, hay phải thử lại). Bật: CHAT_SINGLE_PASS=true
    chat_single_pass: bool = False
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-opus-5-5"

    planner_tolerance: float = 0.05


@lru_cache
def get_settings() -> Settings:
    return Settings()


_WEAK_SECRETS = {"change-me", "changeme", "secret"}
MIN_JWT_SECRET_LEN = 32


def validate_settings(s: Settings) -> None:
    """Chặn khởi động khi cấu hình bảo mật yếu/sai. Không in giá trị bí mật trong thông báo."""
    problems = []
    if len(s.jwt_secret) < MIN_JWT_SECRET_LEN or s.jwt_secret.lower() in _WEAK_SECRETS:
        problems.append(f"JWT_SECRET phải là chuỗi ngẫu nhiên ≥ {MIN_JWT_SECRET_LEN} ký tự và không phải giá trị mẫu "
                        '(tạo: python -c "import secrets;print(secrets.token_urlsafe(48))")')
    try:
        Fernet(s.health_data_key)
    except (ValueError, TypeError):
        problems.append("HEALTH_DATA_KEY phải là khóa Fernet hợp lệ "
                        '(tạo: python -c "from cryptography.fernet import Fernet;print(Fernet.generate_key().decode())")')
    if problems:
        raise RuntimeError("Cấu hình không hợp lệ: " + "; ".join(problems))
