"""Hiểu tên món người dùng nói bằng LLM (sai chính tả, không dấu, từ địa phương, tiếng Anh, món ghép).

1. Xác định: `find_foods` khớp alias chính xác ⇒ confidence 1.0, không gọi LLM (bên gọi lo).
2. Ứng viên: top-k từ catalog ĐẦY ĐỦ (chưa lọc dị ứng — để còn giải thích từ chối), chấm điểm bằng difflib +
   tỉ lệ token trùng trên tên vi (bỏ dấu), alias vi/en, display_en.
3. LLM: schema dựng ĐỘNG mỗi lần gọi; food_code / dish_code / alternatives là enum đúng các mã ứng viên ⇒ không bịa mã.
4. Hậu kiểm bằng code: mã phải thuộc ứng viên, gram của thành phần món ghép kẹp trong [min_g, 2×max_g],
   tối đa 6 thành phần, confidence kẹp [0, 1].
5. Cache LRU in-memory: khóa (mention đã chuẩn hóa, lang, phiên bản catalog) — KHÔNG chứa user_id hay dị ứng;
   kết quả là ánh xạ ngôn ngữ thuần, lọc dị ứng làm SAU cache (chat engine).
LLM tắt/lỗi ⇒ trả None cho mention đó (bên gọi giữ hành vi cũ: need_label).
"""

import hashlib
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from typing import Literal

from pydantic import BaseModel, Field, create_model

from app.ai.providers import LLMProvider
from app.ai.service import call_structured
from app.core.cache import LRU
from app.foods.catalog import FoodCatalog
from app.foods.matching import en_alias, normalize

TOP_K_FOODS = 25
TOP_K_DISHES = 10
MAX_COMPONENTS = 6
CLARIFY_BELOW = 0.6
CACHE_SIZE = 2000

Kind = Literal["ingredient", "dish", "composite", "not_food", "unknown"]


@dataclass
class Resolution:
    mention: str
    kind: str  # ingredient | dish | composite | not_food | unknown | clarify
    food_code: str | None = None
    dish_code: str | None = None
    components: list[tuple[str, float]] = field(default_factory=list)  # (food_code, grams) — món ghép
    confidence: float = 1.0
    options: list[str] = field(default_factory=list)  # "food:x" | "dish:y" — khi cần hỏi lại
    warnings: list[str] = field(default_factory=list)


# ---------------- ứng viên ----------------
def _names_food(f) -> list[str]:
    return [f.name_vi, *f.aliases, en_alias(f.name_en), en_alias(getattr(f, "display_en", None))]


def _names_dish(d) -> list[str]:
    return [d.name_vi, d.name_en or ""]


def _score(m_norm: str, m_tokens: set[str], names: list[str]) -> float:
    best = 0.0
    for n in names:
        nn = normalize(n).strip()
        if not nn:
            continue
        ratio = SequenceMatcher(None, m_norm, nn).ratio()
        nt = set(nn.split())
        overlap = len(m_tokens & nt) / len(nt) if nt else 0.0
        best = max(best, ratio, 0.9 * overlap)
    return best


def candidates(mention: str, catalog: FoodCatalog) -> tuple[list[str], list[str]]:
    """(mã nguyên liệu top-k, mã món top-k) theo độ giống, ổn định (hòa điểm ⇒ theo mã)."""
    m = normalize(mention).strip()
    tokens = set(m.split())
    foods = sorted(catalog.foods.values(), key=lambda f: (-_score(m, tokens, _names_food(f)), f.code))
    dishes = sorted(catalog.dishes.values(), key=lambda d: (-_score(m, tokens, _names_dish(d)), d.code))
    return [f.code for f in foods[:TOP_K_FOODS]], [d.code for d in dishes[:TOP_K_DISHES]]


def catalog_version(catalog: FoodCatalog) -> str:
    h = hashlib.sha256()
    for code in sorted(catalog.foods):
        h.update(code.encode() + b"\0")
    for code in sorted(catalog.dishes):
        h.update(b"d:" + code.encode() + b"\0")
    return h.hexdigest()[:16]


# ---------------- schema động ----------------
def build_model(food_codes: list[str], dish_codes: list[str], n: int) -> type[BaseModel]:
    """Schema chỉ cho phép đúng các mã ứng viên (enum dựng mỗi lần gọi)."""
    food_lit = Literal[tuple(food_codes)]  # type: ignore[valid-type]
    dish_lit = Literal[tuple(dish_codes)] if dish_codes else Literal["__none__"]  # type: ignore[valid-type]
    opt_lit = Literal[tuple([f"food:{c}" for c in food_codes] + [f"dish:{c}" for c in dish_codes])]  # type: ignore
    component = create_model("Component", food_code=(food_lit, ...), grams=(float, ...))
    item = create_model(
        "MentionResult",
        mention=(str, ...),
        kind=(Kind, ...),
        food_code=(food_lit | None, Field(description="Single ingredient (kind=ingredient)")),
        dish_code=(dish_lit | None, Field(description="Known dish (kind=dish)")),
        components=(list[component], Field(max_length=MAX_COMPONENTS,
                                           description="Only for kind=composite: ingredients + estimated grams")),
        confidence=(float, Field(description="0 to 1")),
        alternatives=(list[opt_lit], Field(max_length=3, description="Other plausible matches")),
    )
    return create_model("FoodResolution", results=(list[item], Field(max_length=max(n, 1))))


SYSTEM = (
    "You map food mentions from a meal-planning chat to a fixed catalog. Users may misspell, omit Vietnamese "
    "diacritics, use regional words (e.g. 'trái thơm' = pineapple, 'củ sắn' = jicama) or English. For each mention "
    "return one result: kind=ingredient with food_code if it is one catalog ingredient; kind=dish with dish_code "
    "if it is one catalog dish; kind=composite with components (catalog ingredients + estimated raw grams for ONE "
    "serving) if it is a mixed dish not in the catalog (e.g. 'bún bò huế' = rice noodles + beef + vegetables); "
    "kind=not_food if it is not food; kind=unknown if nothing in the catalog fits. Use ONLY codes from the enums; "
    "never invent codes. confidence is 0-1; give up to 3 alternatives when unsure. Do not output nutrition values."
)


def _catalog_lines(catalog: FoodCatalog, foods: list[str], dishes: list[str]) -> str:
    lines = [f"- {c}: {catalog.food(c).name_vi} / {getattr(catalog.food(c), 'display_en', None) or catalog.food(c).name_en}"
             for c in foods]
    lines += [f"- dish {c}: {catalog.dishes[c].name_vi} / {catalog.dishes[c].name_en or ''}" for c in dishes]
    return "\n".join(lines)


# ---------------- hậu kiểm ----------------
def review(raw, mention: str, catalog: FoodCatalog, foods: set[str], dishes: set[str]) -> Resolution:
    conf = min(max(float(raw.confidence), 0.0), 1.0)
    alts = [a for a in raw.alternatives
            if (a.startswith("food:") and a[5:] in foods) or (a.startswith("dish:") and a[5:] in dishes)]
    kind = raw.kind
    r = Resolution(mention=mention, kind=kind, confidence=conf)
    if kind == "ingredient" and raw.food_code in foods:
        r.food_code = raw.food_code
        primary = f"food:{raw.food_code}"
    elif kind == "dish" and raw.dish_code in dishes:
        r.dish_code = raw.dish_code
        primary = f"dish:{raw.dish_code}"
    elif kind == "composite":
        for c in raw.components[:MAX_COMPONENTS]:
            if c.food_code not in foods:
                continue
            f = catalog.food(c.food_code)
            g = min(max(float(c.grams), f.min_g), 2 * f.max_g)
            if g != c.grams:
                r.warnings.append(f"GRAMS_CLAMPED:{c.food_code}")
            r.components.append((c.food_code, round(g)))
        if not r.components:
            return Resolution(mention=mention, kind="unknown", confidence=conf)
        primary = None
    elif kind in ("not_food", "unknown"):
        return Resolution(mention=mention, kind=kind, confidence=conf, options=alts if conf < CLARIFY_BELOW else [])
    else:  # kind ingredient/dish nhưng mã không hợp lệ
        return Resolution(mention=mention, kind="unknown", confidence=0.0)
    if conf < CLARIFY_BELOW:
        opts = ([primary] if primary else []) + [a for a in alts if a != primary]
        if len(opts) >= 1:
            return Resolution(mention=mention, kind="clarify", confidence=conf, options=opts[:4])
    return r


# ---------------- cache + API ----------------
cache = LRU(CACHE_SIZE)


def resolve_mentions(provider: LLMProvider | None, mentions: list[str], catalog: FoodCatalog, lang: str,
                     max_retries: int = 2) -> dict[str, Resolution]:
    """mention → Resolution cho các mention LLM xử lý được. Mention thiếu trong kết quả ⇒ bên gọi dùng fallback."""
    if provider is None or not mentions:
        return {}
    version = catalog_version(catalog)
    out: dict[str, Resolution] = {}
    todo: list[str] = []
    for m in dict.fromkeys(x.strip() for x in mentions if x.strip()):
        hit = cache.get((normalize(m).strip(), lang, version))
        if hit is not None:
            out[m] = hit
        else:
            todo.append(m)
    if not todo:
        return out
    cand_foods: list[str] = []
    cand_dishes: list[str] = []
    for m in todo:  # gộp ứng viên của mọi mention trong câu (≤ 5 mention)
        f, d = candidates(m, catalog)
        cand_foods += [c for c in f if c not in cand_foods]
        cand_dishes += [c for c in d if c not in cand_dishes]
    model = build_model(cand_foods, cand_dishes, len(todo))
    user = ("Catalog candidates:\n" + _catalog_lines(catalog, cand_foods, cand_dishes)
            + "\n\nMentions:\n" + "\n".join(f"- {m}" for m in todo))
    res, _ = call_structured(provider, SYSTEM, user, model, max_retries)
    if res is None:
        return out
    fset, dset = set(cand_foods), set(cand_dishes)
    for raw in res.results:
        m = next((x for x in todo if x == raw.mention or normalize(x) == normalize(raw.mention)), None)
        if m is None or m in out:
            continue
        r = review(raw, m, catalog, fset, dset)
        out[m] = r
        cache.put((normalize(m).strip(), lang, version), r)
    return out
