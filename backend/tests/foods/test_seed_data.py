"""Vòng 7 M1: dữ liệu seed — không bịa số liệu, 80 nguyên liệu cũ giữ nguyên, món tham chiếu nguyên liệu thật."""

import hashlib
import json
from pathlib import Path

from app.foods.catalog import SEED_DIR

ROOT = Path(__file__).resolve().parents[3]
FOODS = json.loads((SEED_DIR / "ingredients.json").read_text(encoding="utf-8"))
DISHES = json.loads((SEED_DIR / "dishes.json").read_text(encoding="utf-8"))
BY = {f["code"]: f for f in FOODS}

# Snapshot số liệu (fdc_id, per_100g, portion) của 80 nguyên liệu v2 — đổi ⇒ test đỏ (không được sửa số liệu cũ)
OLD_CODES = sorted(
    "apple baguette banana banana_chips bean_sprouts beef_lean bitter_melon black_beans bok_choy broccoli brown_rice "
    "butter_cookies cabbage carrot cashews catfish chayote cheese_pizza cheeseburger chicken_breast chicken_thigh "
    "choc_chip_cookies chocolate_cake cola corn croissant cucumber dark_chocolate egg eggplant french_fries "
    "fried_chicken glass_noodles green_beans guava ice_cream_chocolate ice_cream_vanilla lentils lettuce mackerel "
    "mango milk_chocolate milk_lowfat mung_beans mushroom mustard_greens napa_cabbage oats okra olive_oil orange "
    "orange_drink papaya peanuts popcorn pork_tenderloin potato potato_chips pumpkin rice_noodles salmon shrimp "
    "soybean_oil soymilk spinach sponge_cake squid sweet_potato sweet_potato_leaves taro tilapia tofu tomato tuna "
    "vanilla_pudding watermelon white_rice wholewheat_bread winter_melon yogurt_lowfat".split())
OLD_SNAPSHOT_SHA256 = "c22e2d38c725a0e79c98c02931b5aa9ad626b3679c4ba5cc038aeaa5cb91d833"


def test_old_80_ingredients_unchanged():
    assert len(OLD_CODES) == 80 and set(OLD_CODES) <= set(BY)
    snap = {c: {"fdc": BY[c]["source"]["fdc_id"], "per_100g": BY[c]["per_100g"], "portion": BY[c].get("portion")}
            for c in OLD_CODES}
    assert hashlib.sha256(json.dumps(snap, sort_keys=True).encode()).hexdigest() == OLD_SNAPSHOT_SHA256


def test_counts_and_unique_fdc_ids():
    assert len(FOODS) >= 115 and len(DISHES) >= 65
    ids = [f["source"]["fdc_id"] for f in FOODS]
    assert len(ids) == len(set(ids)) and all(isinstance(i, int) for i in ids)
    assert all(f["source"]["dataset"].startswith("USDA FoodData Central, SR Legacy") for f in FOODS)
    assert len({f["code"] for f in FOODS}) == len(FOODS) and len({d["code"] for d in DISHES}) == len(DISHES)


def test_every_number_comes_from_usda():
    for f in FOODS:  # chất USDA không có ⇒ null + "chưa xác minh", không bao giờ tự điền
        for k, v in f["per_100g"].items():
            assert v is None or v >= 0, (f["code"], k)
            assert (v is None) == (k in f["unverified_nutrients"]), (f["code"], k)
        assert f["source"]["description"] and f["source"]["url"].endswith(f"/{f['source']['fdc_id']}/nutrients")


def test_dishes_reference_real_ingredients():
    for d in DISHES:
        assert d["main"] and set(d["main"]) <= set(BY), d["code"]
        assert d["name_vi"] and d["name_en"] and d["slots"] and set(d["slots"]) <= set("BLD"), d["code"]
        assert all(set(d["slots"]) & set(BY[m]["slots"]) for m in d["main"]), d["code"]  # main dùng được ở bữa đó


def test_new_ingredients_have_aliases_and_display():
    for code, f in BY.items():
        if code in OLD_CODES:
            continue
        assert f["display_en"] and "," not in f["display_en"], code
        assert any(any(ch in a for ch in "àáảãạăắằẳẵặâấầẩẫậđèéẻẽẹêếềểễệìíỉĩịòóỏõọôốồổỗộơớờởỡợùúủũụưứừửữựỳýỷỹỵ")
                   or a.isascii() and a == a.lower() for a in f["aliases"]), code
        assert f["aliases"], code


def test_allergen_tags():
    for f in FOODS:
        tags = set(f["tags"])
        if "fish" in tags:
            assert "allergen:fish" in tags, f["code"]
        if "shellfish" in tags:
            assert "allergen:shellfish" in tags, f["code"]
    for code in ("crab", "clam", "shrimp", "squid"):
        assert "allergen:shellfish" in BY[code]["tags"]
    for code in ("snakehead", "anchovy", "salmon"):
        assert "allergen:fish" in BY[code]["tags"]
    for code in ("tofu", "fried_tofu", "soymilk"):
        assert "allergen:soy" in BY[code]["tags"]
    assert "allergen:egg" in BY["duck_egg"]["tags"] and "allergen:milk" in BY["condensed_milk"]["tags"]


def test_aromatics_not_free_picked_by_planner():
    """Gia vị/rau thơm (hành, tỏi, gừng, sả, ngò, ớt, chanh): planner không tự chọn làm rau của bữa."""
    for code in ("scallion", "garlic", "ginger", "lemongrass", "coriander", "chili", "lime"):
        assert BY[code]["slots"] == "", code


def test_data_sources_doc_counts():
    doc = (ROOT / "docs" / "DATA_SOURCES.md").read_text(encoding="utf-8")
    cooking = sum(1 for f in FOODS if f["category"] != "snack")
    snacks = len(FOODS) - cooking
    assert f"{cooking} nguyên liệu nấu ăn + {snacks} đồ ăn vặt" in doc and f"{len(DISHES)} món" in doc
