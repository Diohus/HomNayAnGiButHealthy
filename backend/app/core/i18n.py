"""Song ngữ vi/en cho mọi chuỗi hiển thị cho người dùng. Catalog phẳng: app/i18n/vi.py, app/i18n/en.py.

- `get_lang`: dependency FastAPI đọc header Accept-Language (tag chính `en*` ⇒ "en", còn lại ⇒ "vi").
- `tr(key, lang, **params)`: thiếu khóa ở `en` ⇒ dùng `vi` và log WARNING tên khóa (không log params).
- `Msg`: chuỗi dịch "hoãn" — dùng làm tham số của chuỗi khác (vd tên dị nguyên trong câu lỗi).
"""

import logging
from dataclasses import dataclass, field
from typing import Literal, get_args

from fastapi import Header, Request

from app.i18n.en import EN
from app.i18n.vi import VI

Lang = Literal["vi", "en"]
LANGS: tuple[str, ...] = get_args(Lang)
CATALOGS: dict[str, dict[str, str]] = {"vi": VI, "en": EN}

log = logging.getLogger(__name__)


def parse_accept_language(value: str | None) -> Lang:
    """Lấy ngôn ngữ ưu tiên đầu tiên mà app hỗ trợ; mặc định vi."""
    for part in (value or "").split(","):
        tag = part.split(";")[0].strip().lower()
        if tag.startswith("en"):
            return "en"
        if tag.startswith("vi"):
            return "vi"
    return "vi"


def get_lang(accept_language: str | None = Header(None)) -> Lang:
    return parse_accept_language(accept_language)


def request_lang(request: Request) -> Lang:
    return parse_accept_language(request.headers.get("accept-language"))


@dataclass(frozen=True)
class Msg:
    key: str
    params: dict = field(default_factory=dict)

    def render(self, lang: Lang) -> str:
        return tr(self.key, lang, **self.params)


def resolve(v, lang: Lang):
    """Tham số có thể là Msg, hoặc dict {"vi": ..., "en": ...} (tên nguyên liệu/món)."""
    if isinstance(v, Msg):
        return v.render(lang)
    if isinstance(v, dict) and set(v) <= set(LANGS) and v:
        return v.get(lang) or v.get("vi")
    return v


def has_key(key: str) -> bool:
    return key in VI


def tr(key: str, lang: Lang = "vi", **params) -> str:
    cat = CATALOGS.get(lang, VI)
    tpl = cat.get(key)
    if tpl is None:
        if lang != "vi":
            log.warning("i18n missing key %s for %s", key, lang)
        tpl = VI.get(key)
        if tpl is None:
            log.warning("i18n unknown key %s", key)
            return key
    if not params:
        return tpl
    return tpl.format(**{k: resolve(v, lang) for k, v in params.items()})


def name_of(obj, lang: Lang) -> str:
    """Tên hiển thị theo ngôn ngữ. en: display_en (nguyên liệu) ⇒ name_en (món) ⇒ name_vi."""
    if lang != "en":
        return obj.name_vi
    return getattr(obj, "display_en", None) or getattr(obj, "name_en", None) or obj.name_vi


def names(obj) -> dict[str, str]:
    return {"vi": obj.name_vi, "en": name_of(obj, "en")}
