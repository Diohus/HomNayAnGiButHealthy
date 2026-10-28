"""So khớp tên món người dùng nói với nguyên liệu trong catalog — xác định, không dùng LLM.

- Ưu tiên cụm dài nhất ("gà rán" thắng "gà", "bánh kem" thắng "kem").
- Giữ dấu tiếng Việt khi người dùng gõ có dấu (tránh "lon" ≡ "lợn"); chỉ bỏ dấu khi câu gõ không dấu.
- Số lượng đứng ngay trước tên món ("2 cái bánh kem", "200g kem", "1 lon coca") gắn với món đó.
- Tiếng Anh: alias tay (seed/catalog.py ALIASES_EN, đã gộp vào `aliases`) + alias sinh từ `name_en`
  (phần trước dấu phẩy, bỏ ngoặc, viết thường: "Chicken breast, skinless" ⇒ "chicken breast").
"""

import re
import unicodedata

from pydantic import BaseModel

# Món ghép chứa tên nguyên liệu nhưng là món khác, CHƯA có dữ liệu xác minh (vd "trà sữa" ≠ "sữa").
# Khớp các cụm này sẽ "chiếm chỗ" để không bị hiểu nhầm, và được báo là chưa có dữ liệu.
UNKNOWN_COMPOUNDS = [
    "trà sữa", "cà phê sữa", "sinh tố", "nước ép", "bánh flan", "bánh bao", "bánh cuốn", "bánh xèo",
    "bánh tráng trộn", "chè", "bánh mì que", "kem đánh răng", "kem chống nắng", "kem dưỡng",
    # ("xôi", "sữa đặc" đã có dữ liệu từ vòng 7)
]
# Alias chỉ khớp khi người dùng GÕ CÓ DẤU: bỏ dấu thì trùng một từ rất thông dụng
# (tỏi/tôi, cua/của, măng/mang, bưởi/buổi, ngò/ngô — "ngô" là bắp đã có sẵn).
DIACRITIC_ONLY = {"tỏi", "cua", "măng", "bưởi", "ngò"}
# Tên gọi tắt của món trong catalog (chỉ khi KHÔNG mơ hồ: "phở" trơn có thể là phở bò hoặc phở gà ⇒ không thêm)
DISH_ALIASES = {"cơm tấm": "com_tam_suon", "broken rice": "com_tam_suon"}
_UNIT_TOKEN = re.compile(r"^(\d+(?:[.,]\d+)?)(kg|g|gr|gram|ml|l)?$")
CONTAINER_WORDS = {"lon", "hop", "ly", "coc", "chai", "goi", "cai", "mieng", "bat", "to", "dia"}
_UNITS = {"g": "g", "gr": "g", "gram": "g", "kg": "kg", "ml": "ml", "l": "l", "lít": "l", "lit": "l"}


def has_diacritics(text: str) -> bool:
    return any(unicodedata.decomposition(c) for c in text.lower() if c.isalpha()) or "đ" in text.lower()


def normalize(text: str, keep_diacritics: bool = False) -> str:
    text = unicodedata.normalize("NFC", text.lower())
    if not keep_diacritics:
        text = text.replace("đ", "d")
        text = unicodedata.normalize("NFD", text)
        text = "".join(c for c in text if unicodedata.category(c) != "Mn")
        text = re.sub(r"[^a-z0-9.,]+", " ", text)
    else:
        text = re.sub(r"[^\w.,]+", " ", text)
    text = re.sub(r"(?<!\d)[.,]|[.,](?!\d)", " ", text)  # giữ dấu thập phân trong số
    return f" {' '.join(text.split())} "


class FoodMatch(BaseModel):
    food_code: str
    alias: str
    start: int
    end: int
    qty_value: float | None = None
    qty_unit: str | None = None  # portion | g | ml


def en_alias(name_en: str | None) -> str:
    """Alias tiếng Anh sinh từ name_en: phần trước dấu phẩy, bỏ phần trong ngoặc, viết thường."""
    return re.sub(r"\(.*?\)", " ", (name_en or "").split(",")[0]).strip().lower()


def _alias_index(catalog, keep: bool) -> list[tuple[str, str | None]]:
    pairs: list[tuple[str, str | None]] = []
    for f in catalog.foods.values():
        for a in {*f.aliases, f.name_vi, en_alias(f.name_en), en_alias(f.display_en)}:
            if not keep and normalize(a, True).strip() in DIACRITIC_ONLY:
                continue  # câu không dấu: "toi" là "tôi", không phải "tỏi"
            na = normalize(a, keep).strip()
            if na:
                pairs.append((na, f.code))
    pairs += [(normalize(c, keep).strip(), None) for c in UNKNOWN_COMPOUNDS]
    pairs.sort(key=lambda p: (-len(p[0]), p[1] is None, p[1] or ""))  # dài trước; trùng độ dài: nguyên liệu trước
    return pairs


def _quantity_before(norm: str, start: int) -> tuple[float | None, str | None]:
    tokens = norm[:start].split()[-3:]
    for i in range(len(tokens) - 1, -1, -1):
        m = _UNIT_TOKEN.match(tokens[i])
        if not m:
            continue
        v = float(m.group(1).replace(",", "."))
        unit = m.group(2) or (_UNITS.get(tokens[i + 1]) if i + 1 < len(tokens) else None)
        if unit == "kg":
            return v * 1000, "g"
        if unit == "l":
            return v * 1000, "ml"
        if unit in ("g", "gr", "gram"):
            return v, "g"
        if unit == "ml":
            return v, "ml"
        return v, "portion"
    return None, None


def find_dishes(text: str, catalog) -> list[tuple[str, int, int]]:
    """Món trong catalog được gọi đúng tên (vi/en), không chồng lấn, cụm dài nhất trước: [(dish_code, start, end)]
    trên chuỗi đã chuẩn hóa như find_foods. Vd "tôi vừa ăn 1 tô phở bò" ⇒ pho_bo (không tách "phở" + "bò")."""
    keep = has_diacritics(text)
    norm = normalize(text, keep)
    pairs = [(n, d.code) for d in catalog.dishes.values() for n in (d.name_vi, d.name_en or "")]
    pairs += [(n, c) for n, c in DISH_ALIASES.items() if c in catalog.dishes]
    names = sorted(((normalize(n, keep).strip(), c) for n, c in pairs if n and normalize(n, keep).strip()),
                   key=lambda x: (-len(x[0]), x[1]))
    taken = [False] * len(norm)
    out = []
    for name, code in names:
        i = norm.find(f" {name} ")
        if i == -1:
            continue
        s, e = i + 1, i + 1 + len(name)
        if any(taken[s:e]) or any(c == code for c, _, _ in out):
            continue
        taken[s:e] = [True] * (e - s)
        out.append((code, s, e))
    return sorted(out, key=lambda x: x[1])


def find_unknown_compounds(text: str) -> list[str]:
    keep = has_diacritics(text)
    norm = normalize(text, keep)
    return [c for c in UNKNOWN_COMPOUNDS if f" {normalize(c, keep).strip()} " in norm]


def find_foods(text: str, catalog) -> list[FoodMatch]:
    """Tất cả nguyên liệu được nhắc tới, không chồng lấn, theo thứ tự xuất hiện."""
    keep = has_diacritics(text)
    norm = normalize(text, keep)
    taken = [False] * len(norm)
    out: list[FoodMatch] = []
    for alias, code in _alias_index(catalog, keep):
        needle = f" {alias} "
        start = 0
        while (i := norm.find(needle, start)) != -1:
            s, e = i + 1, i + 1 + len(alias)
            prev = norm[:s].split()[-1:] or [""]
            if alias in CONTAINER_WORDS and _UNIT_TOKEN.match(prev[0]):
                start = i + 1  # "1 lon coca": "lon" là vật chứa, không phải "lợn"
                continue
            if not any(taken[s:e]):
                for k in range(s, e):
                    taken[k] = True
                if code is not None and all(m.food_code != code for m in out):
                    qv, qu = _quantity_before(norm, s)
                    out.append(FoodMatch(food_code=code, alias=alias, start=s, end=e, qty_value=qv, qty_unit=qu))
            start = i + 1
    return sorted(out, key=lambda m: m.start)
