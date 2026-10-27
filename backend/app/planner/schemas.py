from datetime import date

from pydantic import BaseModel

MACROS = ("energy_kcal", "protein_g", "carb_g", "fat_g")


class PlannerTarget(BaseModel):
    code: str
    kind: str  # target | min | max
    value: float


class LockedItem(BaseModel):
    """Nguyên liệu cố định khối lượng.

    - origin="user_adjust": người dùng bấm +/- → cố định trong bữa `slot`.
    - origin="pantry": nguyên liệu có sẵn → `slot=None`, solver tự phân bổ vào các bữa, tổng = grams.
    """

    food_code: str
    grams: float
    slot: str | None = None
    origin: str = "user_adjust"


class MealStructure(BaseModel):
    """Giữ nguyên cấu trúc bữa khi rebalance: món chính + tập nguyên liệu tự do hiện có."""

    dish_code: str | None
    food_codes: list[str]


class Requirement(BaseModel):
    """Yêu cầu từ người dùng: món chính (dish) hoặc nguyên liệu phụ (food) phải có, ở bữa `slot` hoặc bất kỳ."""

    kind: str  # dish | food
    code: str
    slot: str | None = None


class PlanRequest(BaseModel):
    day: date
    slots: list[str]
    targets: list[PlannerTarget]
    tolerance: float = 0.05
    forbidden_dishes: set[str] = set()
    recent_dishes: dict[str, int] = {}  # dish_code → số ngày gần đây đã dùng (phạt nhẹ để đa dạng)
    locked: list[LockedItem] = []
    structure: dict[str, MealStructure] | None = None  # None = sinh mới
    required: list[Requirement] = []
    min_meal_energy_kcal: float | None = None  # ràng buộc CỨNG: tổng năng lượng các bữa chính (ngày cheat day)
    prefer_low_gi: bool = False
    time_limit_s: int = 10
    # Bữa giữ nguyên (đổi một bữa): không sinh biến cho các bữa này, item của chúng truyền qua `locked` ở đúng slot.
    # Bữa có item origin="ai_estimate" (món ghép AI ước tính) cũng tự giữ nguyên.
    frozen_slots: set[str] = set()
    # Không thích: ràng buộc MỀM (phạt nặng); khác dị ứng là ràng buộc cứng (đã lọc khỏi catalog)
    disliked_foods: set[str] = set()
    disliked_dishes: set[str] = set()
    # Sàn năng lượng theo từng bữa (cân lại sau khi ăn): phạt rất nặng nếu thấp hơn — không bỏ bữa
    min_slot_energy_kcal: dict[str, float] = {}


class PlanItem(BaseModel):
    food_code: str
    grams: float
    locked: bool = False
    origin: str = "optimizer"


class MealPlan(BaseModel):
    slot: str
    dish_code: str | None
    items: list[PlanItem]
    totals: dict[str, float]


class Deviation(BaseModel):
    code: str
    kind: str
    target: float
    actual: float
    pct: float  # (actual-target)/target
    within: bool


class Suggestion(BaseModel):
    nutrient: str
    food_codes: list[str]


class DayPlan(BaseModel):
    day: date
    status: str  # ok | partial | conflict
    meals: list[MealPlan]
    totals: dict[str, float]
    deviations: list[Deviation]
    shortfalls: list[str] = []  # chỉ số không đạt (thiếu hoặc vượt)
    suggestions: list[Suggestion] = []
    conflicts: list[str] = []
    warnings: list[str] = []

    def main_dishes(self) -> set[str]:
        return {m.dish_code for m in self.meals if m.dish_code}
