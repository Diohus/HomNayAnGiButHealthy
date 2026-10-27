"""Repository nguyên liệu: seed từ JSON vào DB, và dựng FoodCatalog từ DB (không hard-code số nguyên liệu)."""

import json
import uuid

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.db import models as M
from app.foods.catalog import NUTRIENT_CODES, SEED_DIR, Dish, Food, FoodCatalog, FoodSource, Portion

UNITS = {c: c.rsplit("_", 1)[1].replace("ug", "µg") for c in NUTRIENT_CODES}


def seed(session: Session) -> int:
    """Upsert toàn bộ seed (idempotent)."""
    for code, unit in UNITS.items():
        session.merge(M.Nutrient(code=code, unit=unit))
    foods = json.loads((SEED_DIR / "ingredients.json").read_text(encoding="utf-8"))
    for f in foods:
        ing = session.get(M.Ingredient, f["code"]) or M.Ingredient(code=f["code"])
        for k in ("name_vi", "name_en", "display_en", "category", "tags", "aliases", "min_g", "max_g", "step_g", "slots", "gi",
                  "gi_verified", "source", "portion", "unverified_nutrients"):
            setattr(ing, k, f.get(k))
        ref = f"{f['source']['dataset']} fdc_id {f['source']['fdc_id']}"
        ing.nutrients = [M.IngredientNutrient(nutrient_code=c, amount_per_100g=f["per_100g"].get(c), source_ref=ref)
                         for c in NUTRIENT_CODES]
        session.add(ing)
    session.flush()
    for d in json.loads((SEED_DIR / "dishes.json").read_text(encoding="utf-8")):
        dish = session.get(M.Dish, d["code"]) or M.Dish(code=d["code"])
        dish.name_vi, dish.name_en, dish.slots = d["name_vi"], d.get("name_en"), d["slots"]
        dish.components = [M.DishComponent(ingredient_code=c, role="main") for c in d["main"]]
        session.add(dish)
    session.commit()
    _cache.clear()
    return len(foods)


def _to_food(ing: M.Ingredient) -> Food:
    return Food(
        code=ing.code, name_vi=ing.name_vi, name_en=ing.name_en, display_en=ing.display_en, category=ing.category, tags=ing.tags or [],
        min_g=ing.min_g, max_g=ing.max_g, step_g=ing.step_g, slots=ing.slots, gi=ing.gi, gi_verified=ing.gi_verified,
        per_100g={n.nutrient_code: n.amount_per_100g for n in ing.nutrients},
        unverified_nutrients=ing.unverified_nutrients or [], source=FoodSource(**ing.source),
        aliases=ing.aliases or [], portion=Portion(**ing.portion) if ing.portion else None,
        user_provided=ing.owner_user_id is not None,
    )


_cache: dict[str, FoodCatalog] = {}


def global_catalog(session: Session) -> FoodCatalog:
    if "global" not in _cache:
        ings = session.scalars(select(M.Ingredient).where(M.Ingredient.owner_user_id.is_(None))).all()
        dishes = session.scalars(select(M.Dish)).all()
        _cache["global"] = FoodCatalog(
            [_to_food(i) for i in ings],
            [Dish(code=d.code, name_vi=d.name_vi, name_en=d.name_en, slots=d.slots,
                  main=[c.ingredient_code for c in d.components])
             for d in dishes],
        )
    return _cache["global"]


def user_foods(session: Session, user_id: uuid.UUID) -> list[Food]:
    rows = session.scalars(select(M.Ingredient).where(M.Ingredient.owner_user_id == user_id)).all()
    return [_to_food(i) for i in rows]


def visible_ingredient(session: Session, user_id: uuid.UUID, code: str) -> M.Ingredient | None:
    return session.scalar(select(M.Ingredient).where(
        M.Ingredient.code == code, or_(M.Ingredient.owner_user_id.is_(None), M.Ingredient.owner_user_id == user_id)))
