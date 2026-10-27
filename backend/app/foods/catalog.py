import json
from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel

SEED_DIR = Path(__file__).resolve().parents[2] / "seed"

NUTRIENT_CODES = [
    "energy_kcal", "protein_g", "fat_g", "carb_g", "fiber_g", "calcium_mg", "iron_mg",
    "phosphorus_mg", "potassium_mg", "sodium_mg", "zinc_mg", "vitamin_d_ug",
]


class FoodSource(BaseModel):
    dataset: str
    fdc_id: int | None = None
    description: str | None = None
    publication_date: str | None = None
    url: str | None = None


SLOT_LETTER = {"breakfast": "B", "lunch": "L", "dinner": "D", "snack": "S"}


class Portion(BaseModel):
    description: str
    grams: float
    source: str


class Food(BaseModel):
    code: str
    name_vi: str
    name_en: str  # mô tả USDA (dữ liệu nguồn, không dùng để hiển thị)
    display_en: str | None = None  # tên hiển thị tiếng Anh ngắn
    category: str  # protein | carb | vegetable | fruit | dairy | nut | fat | snack
    tags: list[str]
    min_g: float
    max_g: float
    step_g: float
    slots: str  # tập con của "BLDS" (S = ăn vặt ngoài bữa)
    gi: float | None = None
    gi_verified: bool = False
    per_100g: dict[str, float | None]
    unverified_nutrients: list[str] = []
    source: FoodSource
    aliases: list[str] = []
    portion: Portion | None = None
    user_provided: bool = False  # số liệu do người dùng nhập từ nhãn sản phẩm

    def nutrient(self, code: str, grams: float) -> float:
        """Lượng chất trong `grams` gram. Chất chưa xác minh → 0 (và được đánh dấu ở tầng hiển thị)."""
        v = self.per_100g.get(code)
        return 0.0 if v is None else v * grams / 100.0

    def allowed_in(self, slot: str) -> bool:
        return SLOT_LETTER[slot] in self.slots


class Dish(BaseModel):
    code: str
    name_vi: str
    name_en: str | None = None
    main: list[str]
    slots: str

    def allowed_in(self, slot: str) -> bool:
        return SLOT_LETTER[slot] in self.slots


class FoodCatalog:
    def __init__(self, foods: list[Food], dishes: list[Dish]):
        self.foods = {f.code: f for f in foods}
        self.dishes = {d.code: d for d in dishes}
        for d in dishes:
            missing = [m for m in d.main if m not in self.foods]
            if missing:
                raise ValueError(f"Món {d.code} tham chiếu nguyên liệu không tồn tại: {missing}")

    def food(self, code: str) -> Food:
        return self.foods[code]

    def with_foods(self, extra: list[Food]) -> "FoodCatalog":
        """Thêm nguyên liệu riêng của người dùng (nhập từ nhãn)."""
        return FoodCatalog([*self.foods.values(), *extra], list(self.dishes.values()))

    def role(self, code: str) -> str:
        """Vai trò xác định (không dùng LLM): main nếu là nguyên liệu chính của món nào đó; snack; còn lại side."""
        f = self.foods[code]
        if f.category == "snack":
            return "snack"
        if any(code in d.main for d in self.dishes.values()):
            return "main"
        return "side"

    def filtered(self, allergies, diets) -> "FoodCatalog":
        """Catalog chỉ gồm nguyên liệu hợp lệ; món bị loại nếu bất kỳ nguyên liệu chính nào bị loại."""
        from app.foods.restrictions import exclusion_reason

        foods = [f for f in self.foods.values() if exclusion_reason(f, allergies, diets) is None]
        ok = {f.code for f in foods}
        dishes = [d for d in self.dishes.values() if all(m in ok for m in d.main)]
        return FoodCatalog(foods, dishes)


@lru_cache
def load_seed_catalog() -> FoodCatalog:
    foods = [Food(**x) for x in json.loads((SEED_DIR / "ingredients.json").read_text(encoding="utf-8"))]
    dishes = [Dish(**x) for x in json.loads((SEED_DIR / "dishes.json").read_text(encoding="utf-8"))]
    return FoodCatalog(foods, dishes)
