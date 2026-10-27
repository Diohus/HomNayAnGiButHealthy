"""Gọi LLM có kiểm soát: validate schema (Pydantic) + validator nghiệp vụ, retry giới hạn, fallback an toàn."""

import logging
import time
from collections.abc import Callable
from typing import TypeVar

from pydantic import BaseModel, ValidationError

from app.ai.providers import LLMError, LLMProvider

log = logging.getLogger(__name__)
T = TypeVar("T", bound=BaseModel)


def strict_schema(model: type[BaseModel]) -> dict:
    """JSON schema chặt (additionalProperties=false, mọi field required) dùng cho structured output."""

    def fix(node):
        if isinstance(node, dict):
            if node.get("type") == "object" and "properties" in node:
                node["additionalProperties"] = False
                node["required"] = list(node["properties"])
            for k in ("title", "default"):
                node.pop(k, None)
            for v in node.values():
                fix(v)
        elif isinstance(node, list):
            for v in node:
                fix(v)
        return node

    return fix(model.model_json_schema())


def call_structured(
    provider: LLMProvider | None,
    system: str,
    user: str,
    model: type[T],
    max_retries: int = 2,
    validate: Callable[[T], list[str]] | None = None,
    image_b64: str | None = None,
) -> tuple[T | None, str]:
    """Trả (kết quả, trạng thái). Trạng thái: ok | disabled | invalid | error. Không bao giờ ném lỗi.
    `image_b64`: ảnh JPEG đã làm sạch metadata (trích xuất giới hạn sức khỏe từ ảnh)."""
    if provider is None:
        return None, "disabled"
    schema = strict_schema(model)
    status = "error"
    for attempt in range(max_retries + 1):
        t0 = time.perf_counter()
        try:
            raw = (provider.complete_json_with_image(system, user, image_b64, schema, model.__name__) if image_b64
                   else provider.complete_json(system, user, schema, model.__name__))
            obj = model.model_validate(raw)
            problems = validate(obj) if validate else []
            if not problems:
                # L3: chỉ thời gian + tên schema, không bao giờ nội dung
                log.debug("llm %s ok attempt=%d timing_ms=%d", model.__name__, attempt + 1,
                          (time.perf_counter() - t0) * 1000)
                return obj, "ok"
            status = "invalid"
            log.info("llm output rejected by validator (attempt %d, %d problems)", attempt + 1, len(problems))
        except ValidationError:
            status = "invalid"
            log.info("llm output failed schema validation (attempt %d)", attempt + 1)
        except LLMError as e:
            status = "error"
            # WARNING: lỗi kết nối/TLS ⇒ app âm thầm chạy dự phòng; chỉ log loại lỗi, không log nội dung
            log.warning("llm call failed (attempt %d): %s", attempt + 1, e)
            if str(e) in ("refusal", "unsupported"):
                break
    return None, status
