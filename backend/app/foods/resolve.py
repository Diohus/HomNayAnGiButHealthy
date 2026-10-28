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
from app.ai.service import DATA_NOT_INSTRUCTIONS, call_structured
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
    top_dishes = [d.code for d in dishes[:TOP_K_DISHES]]
    top_foods = [f.code for f in foods[:TOP_K_FOODS]]
    # nguyên liệu chính của các món ứng viên luôn có mặt (vd "cơm tấm" ⇒ sườn heo) để LLM dựng được món ghép
    extra = [c for code in top_dishes for c in catalog.dishes[code].main if c not in top_foods]
    return top_foods + list(dict.fromkeys(extra)), top_dishes


MAX_NGRAM = 4
MAX_WORDS = 30  # câu dài: chỉ xét 30 từ đầu (giới hạn chi phí chấm điểm)
_name_index: dict[str, tuple[list, list]] = {}
# Từ chức năng (đã bỏ dấu): n-gram CHỈ gồm các từ này bị bỏ qua, để không chiếm chỗ của tên món thật
STOPWORDS = set("""
toi minh tui em anh chi ban muon thich them cho xin an uong vua da moi roi xong dang se nay hom ngay mai qua
sang trua chieu toi bua buoi nha nhe nhi a o voi va hoac la co khong ko k duoc it nhieu mot hai ba 1 2 3 cai
to bat dia ly coc chen phan suat chut thi ma de lam gi nao day kia di thoi cung con
i im me my we want wanna would like to eat ate eating had have drink some a an the for and or with just today
tonight tomorrow yesterday this morning lunch dinner breakfast please can could of in on at no not don t dont
""".split())  # noqa: SIM905 — dễ đọc hơn list literal 120 phần tử


def _index(catalog: FoodCatalog):
    """Tên đã chuẩn hóa của mọi nguyên liệu/món (tính một lần cho mỗi phiên bản catalog)."""
    v = catalog_version(catalog)
    if v not in _name_index:
        def prep(names):
            return [(nn, set(nn.split())) for n in names if n and (nn := normalize(n).strip())]
        _name_index.clear()
        _name_index[v] = ([(f.code, prep(_names_food(f))) for f in catalog.foods.values()],
                          [(d.code, prep(_names_dish(d))) for d in catalog.dishes.values()])
    return _name_index[v]


def ngrams(text: str) -> list[str]:
    """Cụm 1–4 từ liên tiếp của câu (bỏ dấu, chuẩn hóa), trừ cụm chỉ gồm từ chức năng."""
    words = normalize(text).split()[:MAX_WORDS]
    return list(dict.fromkeys(" ".join(words[i:i + n]) for n in range(1, MAX_NGRAM + 1)
                              for i in range(len(words) - n + 1)
                              if not all(w in STOPWORDS for w in words[i:i + n])))


def text_candidates(text: str, catalog: FoodCatalog) -> tuple[list[str], list[str]]:
    """N1: ứng viên cho CẢ CÂU (chưa tách mention): điểm của mỗi mã = điểm cao nhất trên mọi n-gram (1–4 từ).
    Cùng quy tắc với `candidates`: top-25 nguyên liệu + top-10 món + nguyên liệu chính của các món đó."""
    grams = [(g, set(g.split())) for g in ngrams(text)]
    foods_idx, dishes_idx = _index(catalog)

    def best(names) -> float:
        top = 0.0
        for nn, nt in names:
            sm = SequenceMatcher(None, "", nn)
            for g, gt in grams:
                sm.set_seq1(g)
                if sm.real_quick_ratio() > top and sm.quick_ratio() > top:
                    top = max(top, sm.ratio())
                if nt:
                    top = max(top, 0.9 * len(gt & nt) / len(nt))
        return top

    foods = sorted(((-best(n), c) for c, n in foods_idx))
    dishes = sorted(((-best(n), c) for c, n in dishes_idx))
    top_dishes = [c for _, c in dishes[:TOP_K_DISHES]]
    top_foods = [c for _, c in foods[:TOP_K_FOODS]]
    extra = [c for code in top_dishes for c in catalog.dishes[code].main if c not in top_foods]
    return top_foods + list(dict.fromkeys(extra)), top_dishes


def catalog_version(catalog: FoodCatalog) -> str:
    h = hashlib.sha256()
    for code in sorted(catalog.foods):
        h.update(code.encode() + b"\0")
    for code in sorted(catalog.dishes):
        h.update(b"d:" + code.encode() + b"\0")
    return h.hexdigest()[:16]


# ---------------- schema động ----------------
def mention_model(food_codes: list[str], dish_codes: list[str], key: str = "mention") -> type[BaseModel]:
    """Kết quả cho MỘT mention; chỉ cho phép đúng các mã ứng viên (enum dựng mỗi lần gọi)."""
    food_lit = Literal[tuple(food_codes)]  # type: ignore[valid-type]
    dish_lit = Literal[tuple(dish_codes)] if dish_codes else Literal["__none__"]  # type: ignore[valid-type]
    opt_lit = Literal[tuple([f"food:{c}" for c in food_codes] + [f"dish:{c}" for c in dish_codes])]  # type: ignore
    component = create_model("Component", food_code=(food_lit, ...), grams=(float, ...))
    return create_model(
        "MentionResult",
        **{key: (str, ...)},
        kind=(Kind, ...),
        food_code=(food_lit | None, Field(description="Single ingredient (kind=ingredient)")),
        dish_code=(dish_lit | None, Field(description="Known dish (kind=dish)")),
        components=(list[component], Field(max_length=MAX_COMPONENTS,
                                           description="Only for kind=composite: ingredients + estimated grams")),
        confidence=(float, Field(description="0 to 1")),
        alternatives=(list[opt_lit], Field(max_length=3, description="Other plausible matches")),
    )


def build_model(food_codes: list[str], dish_codes: list[str], n: int) -> type[BaseModel]:
    item = mention_model(food_codes, dish_codes)
    return create_model("FoodResolution", results=(list[item], Field(max_length=max(n, 1))))


SYSTEM = (
    "You map food mentions from a meal-planning chat to a fixed catalog. Users may misspell, omit Vietnamese "
    "diacritics, use regional words (e.g. 'trái thơm' = pineapple, 'củ sắn' = jicama) or English. For each mention "
    "return one result: kind=ingredient with food_code if it is one catalog ingredient; kind=dish with dish_code "
    "if it is one catalog dish (ALWAYS prefer an existing catalog dish over composite); kind=composite with components (catalog ingredients + estimated raw grams for ONE "
    "serving) if it is a mixed dish not in the catalog (e.g. 'bún bò huế' = rice noodles + beef + vegetables); "
    "kind=not_food if it is not food; kind=unknown if nothing in the catalog fits. Use ONLY codes from the enums; "
    "never invent codes. confidence is 0-1; give up to 3 alternatives when unsure. Do not output nutrition values."
) + DATA_NOT_INSTRUCTIONS


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
        # Catalog đã có món trùng tên ("cơm tấm" ⊂ "Cơm tấm sườn") ⇒ ưu tiên dish (số liệu theo nguyên liệu DB,
        # không phải khối lượng AI ước tính)
        if (d := _dish_by_name(mention, catalog, dishes)) is not None:
            return Resolution(mention=mention, kind="dish", dish_code=d, confidence=conf)
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


def _dish_by_name(mention: str, catalog: FoodCatalog, dishes: set[str]) -> str | None:
    m = normalize(mention).strip()
    if not m:
        return None
    hits = sorted(c for c in dishes for n in (catalog.dishes[c].name_vi, catalog.dishes[c].name_en or "")
                  if n and (normalize(n).strip() == m or f" {m} " in normalize(n)))
    return hits[0] if hits else None


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
