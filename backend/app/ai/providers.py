"""Provider LLM. Mặc định: OpenAI-compatible (LLM_MODEL, mặc định gpt-6-luna).
Provider khác (anthropic) ẩn sau cờ LLM_EXPERIMENTAL_PROVIDERS=true.

Không bao giờ log prompt/đầu ra (có thể chứa dữ liệu sức khỏe).
"""

import json
import logging
from typing import Protocol

import httpx

from app.core.config import Settings

log = logging.getLogger(__name__)


class LLMError(Exception):
    pass


class LLMProvider(Protocol):
    name: str

    def complete_json(self, system: str, user: str, schema: dict, schema_name: str) -> dict: ...

    # Ảnh JPEG base64 (đã bỏ metadata). Provider không hỗ trợ ⇒ LLMError("unsupported").
    def complete_json_with_image(self, system: str, user: str, image_b64: str, schema: dict,
                                 schema_name: str) -> dict: ...


class OpenAICompatibleProvider:
    name = "openai"

    def __init__(self, s: Settings):
        self._url = s.llm_base_url.rstrip("/") + "/chat/completions"
        self._key = s.llm_api_key
        self._model = s.llm_model
        self._timeout = s.llm_timeout_s

    def complete_json(self, system: str, user: str, schema: dict, schema_name: str) -> dict:
        return self._complete(system, user, schema, schema_name)

    def complete_json_with_image(self, system: str, user: str, image_b64: str, schema: dict,
                                 schema_name: str) -> dict:
        content = [{"type": "text", "text": user},
                   {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"}}]
        return self._complete(system, content, schema, schema_name)

    def _complete(self, system: str, user_content, schema: dict, schema_name: str) -> dict:
        body = {
            "model": self._model,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user_content}],
            "response_format": {"type": "json_schema",
                                "json_schema": {"name": schema_name, "schema": schema, "strict": True}},
        }
        try:
            r = httpx.post(self._url, json=body, timeout=self._timeout,
                           headers={"Authorization": f"Bearer {self._key}"})
            r.raise_for_status()
            content = r.json()["choices"][0]["message"]["content"]
            return json.loads(content)
        except httpx.TimeoutException as e:
            raise LLMError("timeout") from e
        except (httpx.HTTPError, KeyError, IndexError, TypeError, json.JSONDecodeError) as e:
            raise LLMError(type(e).__name__) from e


class AnthropicProvider:
    """Ẩn — chỉ bật khi LLM_EXPERIMENTAL_PROVIDERS=true và LLM_PROVIDER=anthropic. Cần `pip install .[claude]`."""

    name = "anthropic"

    def __init__(self, s: Settings):
        import anthropic  # import trễ: dependency tùy chọn

        self._anthropic = anthropic
        self._client = anthropic.Anthropic(api_key=s.anthropic_api_key or None, timeout=s.llm_timeout_s,
                                           max_retries=0)  # retry do service.call_structured quản lý
        self._model = s.anthropic_model

    def complete_json(self, system: str, user: str, schema: dict, schema_name: str) -> dict:
        return self._complete(system, user, schema)

    def complete_json_with_image(self, system: str, user: str, image_b64: str, schema: dict,
                                 schema_name: str) -> dict:
        content = [{"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": image_b64}},
                   {"type": "text", "text": user}]
        return self._complete(system, content, schema)

    def _complete(self, system: str, user_content, schema: dict) -> dict:
        a = self._anthropic
        try:
            resp = self._client.beta.messages.create(
                model=self._model,
                max_tokens=16000,
                system=system,
                messages=[{"role": "user", "content": user_content}],
                output_config={"effort": "low", "format": {"type": "json_schema", "schema": schema}},
                betas=["server-side-fallback-2026-07-01"],
                fallbacks="default",
            )
        except a.APITimeoutError as e:
            raise LLMError("timeout") from e
        except a.APIConnectionError as e:
            raise LLMError("connection") from e
        except a.APIStatusError as e:
            raise LLMError(f"status_{e.status_code}") from e
        if resp.stop_reason == "refusal":
            raise LLMError("refusal")
        if resp.stop_reason == "max_tokens":
            raise LLMError("max_tokens")
        text = next((b.text for b in resp.content if b.type == "text"), None)
        if text is None:
            raise LLMError("no_text")
        try:
            return json.loads(text)
        except json.JSONDecodeError as e:
            raise LLMError("invalid_json") from e


def get_provider(s: Settings) -> LLMProvider | None:
    """None ⇒ chạy chế độ fallback (template + parser quy tắc)."""
    name = s.llm_provider
    if name != "openai" and not s.llm_experimental_providers:
        log.warning("LLM provider %s is hidden behind LLM_EXPERIMENTAL_PROVIDERS; using openai", name)
        name = "openai"
    if name == "anthropic":
        try:
            return AnthropicProvider(s)
        except ImportError:
            log.warning("anthropic SDK not installed; LLM disabled")
            return None
    if not s.llm_api_key:
        return None
    return OpenAICompatibleProvider(s)
