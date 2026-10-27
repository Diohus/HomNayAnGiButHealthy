"""(b) Cơ sở dữ liệu nguyên liệu: nguồn kiểm chứng, lọc dị ứng, nhận diện tên món."""

import json

from app.foods.catalog import SEED_DIR
from app.foods.matching import find_foods, find_unknown_compounds
from app.foods.restrictions import exclusion_reason


def test_every_food_has_verifiable_source(catalog):
    for f in catalog.foods.values():
        assert f.source.dataset.startswith("USDA FoodData Central")
        assert f.source.fdc_id and f.source.url.endswith(f"{f.source.fdc_id}/nutrients")
        for core in ("energy_kcal", "protein_g", "fat_g", "carb_g"):
            assert f.per_100g[core] is not None


def test_missing_values_marked_unverified_not_invented(catalog):
    for f in catalog.foods.values():
        for code, v in f.per_100g.items():
            assert (v is None) == (code in f.unverified_nutrients)
    assert "fiber_g" in catalog.food("shrimp").unverified_nutrients


def test_seed_matches_known_usda_values():
    """Đối chiếu ngẫu nhiên vài giá trị với USDA SR Legacy (fdc 171077 ức gà, 169756 gạo trắng)."""
    data = {x["code"]: x for x in json.loads((SEED_DIR / "ingredients.json").read_text(encoding="utf-8"))}
    assert data["chicken_breast"]["per_100g"]["energy_kcal"] == 120
    assert data["chicken_breast"]["per_100g"]["protein_g"] == 22.5
    assert data["white_rice"]["per_100g"]["energy_kcal"] == 365


def test_snack_portions_from_usda(catalog):
    snacks = [f for f in catalog.foods.values() if f.category == "snack"]
    assert len(snacks) >= 15
    for f in snacks:
        assert f.portion and "USDA food_portion" in f.portion.source


def test_allergen_and_diet_filtering(catalog):
    assert exclusion_reason(catalog.food("shrimp"), ["shellfish"], []) == "allergy:shellfish"
    assert exclusion_reason(catalog.food("pork_tenderloin"), [], ["halal"]) == "diet:halal"
    assert exclusion_reason(catalog.food("egg"), [], ["vegan"]) == "diet:vegan"
    assert exclusion_reason(catalog.food("egg"), [], ["vegetarian"]) is None
    assert exclusion_reason(catalog.food("baguette"), ["gluten"], []) == "allergy:gluten"
    vegan = catalog.filtered([], ["vegan"])
    assert all("animal" not in f.tags for f in vegan.foods.values())
    assert all(all(m in vegan.foods for m in d.main) for d in vegan.dishes.values())


def test_matching_longest_alias_and_roles(catalog):
    assert [m.food_code for m in find_foods("tôi muốn ăn gà", catalog)] == ["chicken_breast"]
    assert [m.food_code for m in find_foods("cho tôi gà rán", catalog)] == ["fried_chicken"]
    assert [m.food_code for m in find_foods("bánh kem sinh nhật", catalog)] == ["chocolate_cake"]
    assert catalog.role("chicken_breast") == "main"
    assert catalog.role("ice_cream_vanilla") == "snack"
    assert catalog.role("rice_noodles") == "side"


def test_matching_respects_diacritics(catalog):
    assert [m.food_code for m in find_foods("1 lon coca", catalog)] == ["cola"]  # "lon" (lon nước) ≠ "lợn"
    assert [m.food_code for m in find_foods("uống 1 lon coca nhé", catalog)] == ["cola"]
    assert [m.food_code for m in find_foods("toi muon an thit lon", catalog)] == ["pork_tenderloin"]


def test_unknown_compounds_not_misread(catalog):
    assert find_foods("tôi muốn uống trà sữa", catalog) == []
    assert find_unknown_compounds("tôi muốn uống trà sữa") == ["trà sữa"]


def test_quantity_attached_to_mention(catalog):
    ms = {m.food_code: (m.qty_value, m.qty_unit) for m in find_foods("2 cái bánh kem và 330ml coca", catalog)}
    assert ms["chocolate_cake"] == (2, "portion")
    assert ms["cola"] == (330, "ml")
