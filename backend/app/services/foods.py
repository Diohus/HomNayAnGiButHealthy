"""Nguyên liệu do người dùng nhập từ nhãn sản phẩm (đánh dấu rõ "người dùng cung cấp")."""

import math
import uuid

from pydantic import BaseModel, Field, field_validator, model_validator
from sqlalchemy.orm import Session

from app.core.errors import AppError, KeyedValueError
from app.core.i18n import Lang, tr
from app.db import foods_repo
from app.db import models as M
from app.foods.catalog import NUTRIENT_CODES
from app.foods.restrictions import exclusion_reason, reason_msg
from app.nutrition.schemas import Allergen
from app.services import profile as P

# Mã nguồn dữ liệu (không phải chữ hiển thị): giao diện hiển thị nhãn "người dùng cung cấp" theo ngôn ngữ
USER_LABEL_SOURCE = "user_label"
CONTAINS = {"animal", "meat", "poultry", "pork", "beef", "fish", "shellfish", "egg", "dairy", "gluten"}


class LabelNutrients(BaseModel):
    energy_kcal: float = Field(ge=0, le=900)
    protein_g: float = Field(ge=0, le=100)
    carb_g: float = Field(ge=0, le=100)
    fat_g: float = Field(ge=0, le=100)
    fiber_g: float | None = Field(None, ge=0, le=100)
    sodium_mg: float | None = Field(None, ge=0, le=40000)

    @field_validator("*")
    @classmethod
    def _finite(cls, v):
        if v is not None and not math.isfinite(v):
            raise KeyedValueError("validation.invalid")
        return v

    @model_validator(mode="after")
    def _consistent(self):
        if self.protein_g + self.carb_g + self.fat_g > 100:
            raise KeyedValueError("validation.label_macro_sum")
        atwater = 4 * self.protein_g + 4 * self.carb_g + 9 * self.fat_g
        if abs(self.energy_kcal - atwater) > max(0.2 * max(self.energy_kcal, atwater), 15):
            raise KeyedValueError("validation.label_energy_mismatch")
        return self


class CustomFoodIn(BaseModel):
    name_vi: str = Field(min_length=2, max_length=80)
    per_100g: LabelNutrients
    portion_g: float = Field(gt=0, le=2000)
    portion_description: str | None = Field(None, max_length=60)  # trống ⇒ "1 phần"/"1 serving"
    contains_allergens: list[Allergen] = []
    contains: list[str] = []

    @field_validator("contains")
    @classmethod
    def _contains(cls, v):
        bad = set(v) - CONTAINS
        if bad:
            raise KeyedValueError("validation.invalid_values", values=", ".join(sorted(bad)))
        return v


def create_custom_food(s: Session, user_id: uuid.UUID, data: CustomFoodIn, lang: Lang = "vi") -> M.Ingredient:
    p = P.require_profile(s, user_id)
    tags = sorted({*data.contains, *(f"allergen:{a}" for a in data.contains_allergens)})
    probe = type("F", (), {"tags": tags})()
    if reason := exclusion_reason(probe, p.allergies, p.diets):
        raise AppError(422, "ALLERGEN_CONFLICT", key="error.ALLERGEN_CONFLICT.custom",
                       params={"reason": reason_msg(reason)}, reason=reason)
    code = f"user_{uuid.uuid4().hex[:12]}"
    provided = data.per_100g.model_dump()
    step = 5 if data.portion_g < 100 else 10
    ing = M.Ingredient(
        code=code, owner_user_id=user_id, name_vi=data.name_vi, name_en=data.name_vi, category="snack", tags=tags,
        aliases=[data.name_vi], min_g=step, max_g=round(data.portion_g * 10), step_g=step, slots="S", gi=None,
        gi_verified=False, source={"dataset": USER_LABEL_SOURCE},
        portion={"description": data.portion_description or tr("food.portion_default", lang), "grams": data.portion_g,
                 "source": USER_LABEL_SOURCE},
        unverified_nutrients=[c for c in NUTRIENT_CODES if provided.get(c) is None],
    )
    ing.nutrients = [M.IngredientNutrient(nutrient_code=c, amount_per_100g=provided.get(c),
                                          source_ref=USER_LABEL_SOURCE) for c in NUTRIENT_CODES]
    s.add(ing)
    s.commit()
    return ing


def list_foods(s: Session, user_id: uuid.UUID) -> list[dict]:
    p = P.load_profile(s, user_id)
    full = foods_repo.global_catalog(s).with_foods(foods_repo.user_foods(s, user_id))
    out = []
    for f in full.foods.values():
        reason = exclusion_reason(f, p.allergies, p.diets) if p else None
        out.append({**f.model_dump(), "role": full.role(f.code), "excluded_reason": reason})
    return out
