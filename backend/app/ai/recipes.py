"""Cách chế biến + gia vị cho một bữa. LLM chỉ viết văn bản; khối lượng/kcal luôn do planner tính.

Đầu ra LLM bị từ chối nếu: sai schema, nhắc tới nguyên liệu dị ứng/vi phạm chế độ ăn (kiểm tra từ khóa CẢ tiếng
Việt và tiếng Anh, bất kể ngôn ngữ), hoặc tự đưa con số khối lượng/năng lượng. Khi LLM lỗi/timeout ⇒ trả template
tĩnh theo ngôn ngữ, không ghi đè công thức đã có.
"""

import re

from pydantic import BaseModel, Field

from app.ai.providers import LLMProvider
from app.ai.service import call_structured
from app.core.i18n import Lang, tr


class Seasoning(BaseModel):
    name: str = Field(max_length=60)
    note: str = Field(max_length=200)


class RecipeOut(BaseModel):
    steps: list[str] = Field(min_length=1, max_length=8)
    seasonings: list[Seasoning] = Field(max_length=8)
    tip: str = Field(max_length=400)


class Recipe(RecipeOut):
    source: str  # llm | template


# Từ khóa (giữ dấu, so khớp theo từ) — GIẢ ĐỊNH, danh sách tối thiểu
FORBIDDEN_TERMS: dict[str, list[str]] = {
    "allergy:peanut": ["đậu phộng", "lạc", "bơ đậu phộng"],
    "allergy:tree_nut": ["hạt điều", "óc chó", "hạnh nhân", "hạt dẻ", "hạt mắc ca"],
    "allergy:milk": ["sữa", "bơ lạt", "bơ thực vật", "phô mai", "kem tươi", "whipping"],
    "allergy:egg": ["trứng", "mayonnaise", "sốt mayo"],
    "allergy:fish": ["nước mắm", "mắm", "cá"],
    "allergy:shellfish": ["tôm", "cua", "mực", "nghêu", "sò", "hàu", "dầu hào", "ruốc"],
    "allergy:soy": ["nước tương", "xì dầu", "đậu nành", "tương", "đậu hũ", "đậu phụ", "miso"],
    "allergy:wheat": ["bột mì", "nước tương", "xì dầu", "dầu hào", "bánh mì"],
    "allergy:gluten": ["bột mì", "nước tương", "xì dầu", "dầu hào", "bánh mì"],
    "allergy:sesame": ["mè", "vừng", "dầu mè"],
    "diet:vegetarian": ["nước mắm", "mắm", "dầu hào", "mỡ", "thịt", "nước dùng xương", "hạt nêm thịt"],
    "diet:vegan": ["nước mắm", "mắm", "dầu hào", "mỡ", "thịt", "sữa", "trứng", "mật ong", "bơ lạt", "phô mai"],
    "diet:halal": ["mỡ heo", "mỡ lợn", "thịt heo", "thịt lợn", "rượu"],
    "diet:no_pork": ["mỡ heo", "mỡ lợn", "thịt heo", "thịt lợn"],
    "diet:no_beef": ["thịt bò", "mỡ bò"],
    "diet:gluten_free": ["bột mì", "nước tương", "xì dầu", "dầu hào", "bánh mì"],
}

# Tiếng Anh — BẮT BUỘC khi LLM viết công thức tiếng Anh. `violations()` luôn kiểm tra CẢ HAI bộ, bất kể ngôn ngữ.
# GIẢ ĐỊNH, danh sách tối thiểu — cần chuyên gia mở rộng (docs/ASSUMPTIONS.md).
_WHEAT_EN = ["wheat", "wheat flour", "flour", "bread", "breadcrumbs", "pasta", "soy sauce", "oyster sauce"]
_ANIMAL_EN = ["fish sauce", "oyster sauce", "shrimp paste", "anchovy", "anchovies", "meat", "lard", "bone broth",
              "chicken stock", "beef stock", "gelatin", "gelatine"]
FORBIDDEN_TERMS_EN: dict[str, list[str]] = {
    "allergy:peanut": ["peanut", "peanuts", "peanut butter", "peanut oil", "groundnut"],
    "allergy:tree_nut": ["cashew", "cashews", "walnut", "walnuts", "almond", "almonds", "hazelnut", "pecan",
                         "pistachio", "macadamia", "chestnut"],
    "allergy:milk": ["milk", "butter", "cheese", "cream", "ghee", "whey", "yogurt", "yoghurt", "condensed milk"],
    "allergy:egg": ["egg", "eggs", "mayonnaise", "mayo"],
    "allergy:fish": ["fish", "fish sauce", "anchovy", "anchovies"],
    "allergy:shellfish": ["shrimp", "shrimps", "prawn", "prawns", "crab", "squid", "oyster", "oyster sauce", "clam",
                          "mussel", "lobster", "scallop", "shrimp paste"],
    "allergy:soy": ["soy", "soya", "soy sauce", "tofu", "miso", "edamame", "tempeh"],
    "allergy:wheat": _WHEAT_EN,
    "allergy:gluten": [*_WHEAT_EN, "gluten", "barley", "rye"],
    "allergy:sesame": ["sesame", "sesame oil", "tahini"],
    "diet:vegetarian": _ANIMAL_EN,
    "diet:vegan": [*_ANIMAL_EN, "milk", "butter", "cheese", "cream", "ghee", "yogurt", "egg", "eggs", "honey"],
    "diet:halal": ["pork", "lard", "bacon", "ham", "wine", "rice wine", "beer", "alcohol", "gelatin", "gelatine"],
    "diet:no_pork": ["pork", "lard", "bacon", "ham"],
    "diet:no_beef": ["beef", "beef stock", "beef fat"],
    "diet:gluten_free": [*_WHEAT_EN, "gluten", "barley", "rye"],
}
NUMERIC_CLAIM = re.compile(
    r"\d+([.,]\d+)?\s*(kcal|calo|calories|calorie|cal\b|g\b|gr\b|gram|kg\b|ml\b|mg\b"
    r"|tbsp|tsp|tablespoons?|teaspoons?|cups?\b|oz\b|ounces?|lbs?\b|pounds?)",
    re.IGNORECASE,
)


def _terms(allergies, diets) -> list[str]:
    """Từ khóa cấm của CẢ tiếng Việt và tiếng Anh (công thức ngôn ngữ nào cũng phải qua cả hai bộ)."""
    keys = [f"allergy:{a}" for a in allergies] + [f"diet:{d}" for d in diets]
    return sorted({t for k in keys for src in (FORBIDDEN_TERMS, FORBIDDEN_TERMS_EN) for t in src.get(k, [])},
                  key=len, reverse=True)


def violations(text: str, allergies, diets, allowed_phrases: list[str] = ()) -> list[str]:
    """`allowed_phrases`: tên nguyên liệu đã qua bộ lọc (vd. "sữa đậu nành" hợp lệ với người dị ứng sữa bò)."""
    low = text.lower()
    for ph in sorted(allowed_phrases, key=len, reverse=True):
        low = low.replace(ph.lower(), " ")
    found = [t for t in _terms(allergies, diets) if re.search(rf"(?<!\w){re.escape(t)}(?!\w)", low)]
    if NUMERIC_CLAIM.search(text):
        found.append("NUMERIC_CLAIM")
    return found


def _all_text(r: RecipeOut) -> str:
    return " ".join([*r.steps, *(f"{s.name} {s.note}" for s in r.seasonings), r.tip])


SEASONINGS = ("garlic", "scallion", "pepper", "ginger", "fish_sauce", "salt")


def template_recipe(dish_name: str | None, ingredient_names: list[str], allergies, diets,
                    low_sodium: bool, lang: Lang = "vi") -> Recipe:
    """Fallback tĩnh theo ngôn ngữ, an toàn với mọi hạn chế (lọc lại bằng chính bộ kiểm tra, cả hai bộ từ khóa)."""
    candidates = [
        Seasoning(name=tr(f"recipe.season.{k}", lang),
                  note=tr(f"recipe.season.{k}.note" + (".low_sodium" if k == "salt" and low_sodium else ""), lang))
        for k in SEASONINGS
    ]
    seasonings = [s for s in candidates if not violations(f"{s.name} {s.note}", allergies, diets)]
    main = dish_name or tr("recipe.default_dish", lang)
    steps = [tr("recipe.step.prep", lang), tr("recipe.step.main", lang, dish=main.lower()),
             tr("recipe.step.veg", lang), tr("recipe.step.starch", lang)]
    tip = tr("recipe.tip", lang) + (" " + tr("recipe.tip.low_sodium", lang) if low_sodium else "")
    return Recipe(steps=steps, seasonings=seasonings, tip=tip.strip(), source="template")


def generate_recipe(provider: LLMProvider | None, dish_name: str | None, ingredient_names: list[str],
                    allergies, diets, low_sodium: bool, max_retries: int = 2, lang: Lang = "vi") -> Recipe:
    """`dish_name`, `ingredient_names` đã theo ngôn ngữ `lang`. Prompt và template cũng theo `lang`."""
    banned = _terms(allergies, diets)
    user = tr("recipe.user", lang, dish=dish_name or tr("recipe.default_dish", lang),
              ingredients=", ".join(ingredient_names),
              banned=", ".join(banned) if banned else tr("recipe.none", lang),
              low_sodium=tr("recipe.low_sodium_hint", lang) if low_sodium else "")
    out, _ = call_structured(provider, tr("recipe.system", lang), user, RecipeOut, max_retries,
                             validate=lambda r: violations(_all_text(r), allergies, diets, ingredient_names))
    if out is None:
        return template_recipe(dish_name, ingredient_names, allergies, diets, low_sodium, lang)
    return Recipe(**out.model_dump(), source="llm")
