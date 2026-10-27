import math
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.core.errors import KeyedValueError
from app.core.i18n import Msg


class Sex(StrEnum):
    male = "male"
    female = "female"


class ActivityLevel(StrEnum):
    sedentary = "sedentary"
    light = "light"
    moderate = "moderate"
    active = "active"
    very_active = "very_active"


class Goal(StrEnum):
    lose = "lose"
    maintain = "maintain"
    gain_muscle = "gain_muscle"


class Condition(StrEnum):
    diabetes_t1 = "diabetes_t1"
    diabetes_t2 = "diabetes_t2"
    hypertension = "hypertension"
    kidney = "kidney"
    cardio = "cardio"
    liver = "liver"
    pregnant = "pregnant"
    lactating = "lactating"


SENSITIVE_CONDITIONS = {Condition.kidney, Condition.cardio, Condition.liver, Condition.pregnant, Condition.lactating}
DIABETES = {Condition.diabetes_t1, Condition.diabetes_t2}


class Allergen(StrEnum):
    peanut = "peanut"
    tree_nut = "tree_nut"
    milk = "milk"
    egg = "egg"
    fish = "fish"
    shellfish = "shellfish"
    soy = "soy"
    wheat = "wheat"
    gluten = "gluten"
    sesame = "sesame"


class Diet(StrEnum):
    vegetarian = "vegetarian"  # lacto-ovo: không thịt, cá, hải sản
    vegan = "vegan"
    halal = "halal"  # MVP: chỉ loại thịt heo; không xác minh chứng nhận halal
    gluten_free = "gluten_free"
    no_pork = "no_pork"
    no_beef = "no_beef"


def _check_decimal(v: float, field: str, max_decimals: int) -> float:
    """`field`: khóa i18n tên trường (vd "field.height"). Thông điệp lỗi là khóa, handler dịch theo ngôn ngữ."""
    if isinstance(v, bool):
        raise KeyedValueError("validation.not_number", field=Msg(field))
    if not math.isfinite(v):
        raise KeyedValueError("validation.invalid_field", field=Msg(field))
    if round(v, max_decimals) != v:
        raise KeyedValueError("validation.max_decimals", field=Msg(field), n=max_decimals)
    return v


class HealthLimits(BaseModel):
    """Giới hạn sức khỏe do NGƯỜI DÙNG cung cấp (tự nhập hoặc trích từ tài liệu của bác sĩ).
    Ứng dụng không tự đặt giới hạn y khoa; khoảng dưới đây chỉ chặn giá trị vô lý/gõ nhầm."""

    model_config = ConfigDict(extra="forbid")
    energy_kcal_max: float | None = Field(None, gt=0, le=6000)
    protein_g_max: float | None = Field(None, gt=0, le=400)
    carb_g_max: float | None = Field(None, ge=20, le=600)
    fat_g_max: float | None = Field(None, ge=10, le=300)
    sodium_mg_max: float | None = Field(None, gt=0, le=6000)
    potassium_mg_max: float | None = Field(None, gt=0, le=8000)
    phosphorus_mg_max: float | None = Field(None, gt=0, le=4000)


ExpertLimits = HealthLimits  # tên cũ (vòng 1–3)
LIMIT_FIELDS = tuple(HealthLimits.model_fields)


class HealthProfileIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sex: Sex
    age: int = Field(..., description="Age (years)")
    height_cm: float
    weight_kg: float
    activity_level: ActivityLevel
    goal: Goal = Goal.maintain
    conditions: list[Condition] = []
    uses_insulin_or_glucose_meds: bool = False
    allergies: list[Allergen] = []
    diets: list[Diet] = []
    custom_target_kcal: int | None = None
    acknowledge_low_energy: bool = False
    # Có bệnh nền nhạy cảm ⇒ bắt buộc xác nhận: app không có bác sĩ theo dõi, thực đơn chỉ là gợi ý có sai số
    acknowledge_self_managed: bool = False

    @field_validator("age", mode="before")
    @classmethod
    def _age(cls, v):
        if isinstance(v, bool) or not isinstance(v, int | float) or (isinstance(v, float) and not v.is_integer()):
            raise KeyedValueError("validation.age_integer")
        v = int(v)
        if v < 18 or v > 100:
            raise KeyedValueError("validation.age_range")
        return v

    @field_validator("height_cm", mode="before")
    @classmethod
    def _height(cls, v):
        if isinstance(v, bool) or not isinstance(v, int | float):
            raise KeyedValueError("validation.not_number", field=Msg("field.height"))
        v = _check_decimal(float(v), "field.height", 1)
        if v < 120 or v > 230:
            raise KeyedValueError("validation.height_range")
        return v

    @field_validator("weight_kg", mode="before")
    @classmethod
    def _weight(cls, v):
        if isinstance(v, bool) or not isinstance(v, int | float):
            raise KeyedValueError("validation.not_number", field=Msg("field.weight"))
        v = _check_decimal(float(v), "field.weight", 1)
        if v < 30 or v > 300:
            raise KeyedValueError("validation.weight_range")
        return v

    @field_validator("custom_target_kcal")
    @classmethod
    def _custom(cls, v):
        if v is not None and (v < 800 or v > 5000):
            raise KeyedValueError("validation.custom_kcal_range")
        return v

    @model_validator(mode="after")
    def _consistency(self):
        if Condition.diabetes_t1 in self.conditions and Condition.diabetes_t2 in self.conditions:
            raise KeyedValueError("validation.diabetes_both")
        if self.sex == Sex.male and ({Condition.pregnant, Condition.lactating} & set(self.conditions)):
            raise KeyedValueError("validation.pregnancy_sex")
        self.conditions = sorted(set(self.conditions))
        self.allergies = sorted(set(self.allergies))
        self.diets = sorted(set(self.diets))
        return self


class Reference(BaseModel):
    source: str
    applies_to: str | None = None
    note: str | None = None


class NutrientTarget(BaseModel):
    code: str
    unit: str
    kind: str  # target | min | max
    value: float
    lower: float | None = None  # khoảng chấp nhận (±tolerance) cho target
    upper: float | None = None
    reference: Reference
    adjusted_for: list[str] = []


class NutritionNeeds(BaseModel):
    bmr_kcal: float
    activity_factor: float
    tdee_kcal: float
    energy_floor_kcal: float
    meals_per_day: int
    meal_slots: list[str]
    targets: list[NutrientTarget]
    warnings: list[str] = []
    assumptions: list[str] = []

    def get(self, code: str) -> NutrientTarget | None:
        return next((t for t in self.targets if t.code == code), None)


class LowEnergyNotAcknowledged(Exception):
    def __init__(self, requested: float, floor: float):
        self.requested = requested
        self.floor = floor
        super().__init__("low energy target requires acknowledgement")
