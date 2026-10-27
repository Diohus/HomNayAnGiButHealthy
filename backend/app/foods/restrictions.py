"""Dị ứng và chế độ ăn là ràng buộc CỨNG. Hàm này là nguồn sự thật duy nhất cho việc loại nguyên liệu."""

from collections.abc import Iterable

ALLERGEN_TAGS: dict[str, set[str]] = {
    "peanut": {"allergen:peanut"},
    "tree_nut": {"allergen:tree_nut"},
    "milk": {"allergen:milk"},
    "egg": {"allergen:egg"},
    "fish": {"allergen:fish"},
    "shellfish": {"allergen:shellfish"},
    "soy": {"allergen:soy"},
    "wheat": {"allergen:wheat"},
    "gluten": {"allergen:gluten"},
    "sesame": {"allergen:sesame"},
}

DIET_EXCLUDED_TAGS: dict[str, set[str]] = {
    "vegetarian": {"meat", "fish", "shellfish"},
    "vegan": {"animal"},
    "halal": {"pork"},
    "no_pork": {"pork"},
    "no_beef": {"beef"},
    "gluten_free": {"gluten"},
}


def exclusion_reason(food, allergies: Iterable[str], diets: Iterable[str]) -> str | None:
    tags = set(food.tags)
    for a in allergies:
        if tags & ALLERGEN_TAGS[str(a)]:
            return f"allergy:{a}"
    for d in diets:
        if tags & DIET_EXCLUDED_TAGS[str(d)]:
            return f"diet:{d}"
    return None


def reason_msg(reason: str | None):
    """Lý do loại ("allergy:fish") ⇒ câu đã dịch ("dị ứng cá" / "fish allergy"), không bao giờ là mã thô."""
    from app.core.i18n import Msg

    kind, _, code = (reason or "").partition(":")
    if kind == "allergy":
        return Msg("reason.allergy", {"name": Msg(f"allergen.{code}")})
    if kind == "diet":
        return Msg("reason.diet", {"name": Msg(f"diet.{code}")})
    return Msg("reason.unknown")
