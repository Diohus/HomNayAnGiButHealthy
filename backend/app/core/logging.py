"""Logging không chứa dữ liệu sức khỏe.

- Không bao giờ log request body.
- RedactingFilter xóa các khóa nhạy cảm nếu lỡ được truyền vào `extra` hoặc message dạng dict.
"""

import logging
import re

SENSITIVE_KEYS = {
    "weight_kg", "height_cm", "age", "sex", "conditions", "allergies", "diets", "goal",
    "activity_level", "custom_target_kcal", "limits", "health", "profile", "password",
}
_KV = re.compile(r"(" + "|".join(sorted(SENSITIVE_KEYS)) + r")(['\"]?\s*[:=]\s*)([^,}\s]+)", re.IGNORECASE)


class RedactingFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        for key in list(record.__dict__):
            if key in SENSITIVE_KEYS:
                setattr(record, key, "[REDACTED]")
        if isinstance(record.msg, str):
            record.msg = _KV.sub(r"\1\2[REDACTED]", record.msg)
        if isinstance(record.args, tuple):
            record.args = tuple(_KV.sub(r"\1\2[REDACTED]", a) if isinstance(a, str) else a for a in record.args)
        return True


def setup_logging() -> None:
    handler = logging.StreamHandler()
    handler.addFilter(RedactingFilter())
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(logging.INFO)
    # uvicorn access log chỉ có method + path, không có body.
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        lg = logging.getLogger(name)
        lg.handlers = [handler]
        lg.propagate = False
