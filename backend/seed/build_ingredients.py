"""Sinh `ingredients.json` từ bộ CSV USDA FoodData Central SR Legacy.

Cách dùng:
    1. Tải https://fdc.nal.usda.gov/fdc-datasets/FoodData_Central_sr_legacy_food_csv_2018-04.zip
    2. Giải nén, rồi chạy:
       python seed/build_ingredients.py <thư_mục_csv> seed/ingredients.json

Không có giá trị dinh dưỡng nào được gõ tay. Chất nào USDA không có số liệu cho thực phẩm
đó sẽ là `null` và nằm trong `unverified_nutrients` (hiển thị "chưa xác minh").
"""

import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from catalog import ALIASES, ALIASES_EN, CATALOG, DISPLAY_EN, SNACKS  # noqa: E402

# nutrient_nbr của USDA → mã nội bộ
NUTRIENTS = {
    "208": "energy_kcal",
    "203": "protein_g",
    "204": "fat_g",
    "205": "carb_g",
    "291": "fiber_g",
    "301": "calcium_mg",
    "303": "iron_mg",
    "305": "phosphorus_mg",
    "306": "potassium_mg",
    "307": "sodium_mg",
    "309": "zinc_mg",
    "328": "vitamin_d_ug",
}
CORE = {"energy_kcal", "protein_g", "fat_g", "carb_g"}
DATASET = "USDA FoodData Central, SR Legacy (2018-04)"


def build(csv_dir: Path) -> list[dict]:
    with open(csv_dir / "nutrient.csv", encoding="utf-8") as f:
        id_to_code = {r["id"]: NUTRIENTS[r["nutrient_nbr"]] for r in csv.DictReader(f) if r["nutrient_nbr"] in NUTRIENTS}

    wanted = {row[3] for row in CATALOG} | {row[3] for row in SNACKS}
    portions: set[tuple[int, str, float]] = set()
    with open(csv_dir / "food_portion.csv", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            desc = " ".join(x for x in (r["amount"], r["modifier"], r["portion_description"]) if x).strip()
            portions.add((int(r["fdc_id"]), desc, float(r["gram_weight"])))
    foods: dict[int, dict] = {}
    with open(csv_dir / "food.csv", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            fid = int(r["fdc_id"])
            if fid in wanted:
                foods[fid] = {"description": r["description"], "publication_date": r["publication_date"]}

    values: dict[int, dict[str, float]] = {fid: {} for fid in wanted}
    with open(csv_dir / "food_nutrient.csv", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            fid = int(r["fdc_id"])
            if fid in values and r["nutrient_id"] in id_to_code:
                values[fid][id_to_code[r["nutrient_id"]]] = float(r["amount"])

    rows = [(*r, None, None) for r in CATALOG]
    for code, name_vi, name_en, fdc_id, tags, pdesc, pg in SNACKS:
        if not any(fid == fdc_id and abs(g - pg) < 0.01 and pdesc in d for fid, d, g in portions):
            raise SystemExit(f"{code}: khẩu phần '{pdesc}' = {pg} g không có trong USDA food_portion")
        step = 5 if pg < 100 else 10
        rows.append((code, name_vi, name_en, fdc_id, "snack", tags, step, round(pg * 3), step, None, "S", pdesc, pg))
    if missing_display := {r[0] for r in rows} - set(DISPLAY_EN):
        raise SystemExit(f"Thiếu DISPLAY_EN cho: {missing_display}")
    unknown = (set(ALIASES) | set(ALIASES_EN) | set(DISPLAY_EN)) - {r[0] for r in rows}
    if unknown:
        raise SystemExit(f"ALIASES tham chiếu mã không tồn tại: {unknown}")

    out = []
    for code, name_vi, name_en, fdc_id, category, tags, min_g, max_g, step_g, gi, slots, pdesc, pg in rows:
        if fdc_id not in foods:
            raise SystemExit(f"fdc_id {fdc_id} ({code}) không có trong dataset")
        nutr = {k: values[fdc_id].get(k) for k in NUTRIENTS.values()}
        missing = sorted(k for k, v in nutr.items() if v is None)
        if CORE & set(missing):
            raise SystemExit(f"{code}: thiếu chỉ số cốt lõi {CORE & set(missing)}")
        out.append({
            "code": code,
            "name_vi": name_vi,
            "name_en": name_en,
            "display_en": DISPLAY_EN[code],  # tên hiển thị; name_en là mô tả USDA
            "category": category,
            "tags": tags,
            "min_g": min_g,
            "max_g": max_g,
            "step_g": step_g,
            "slots": slots,
            "gi": gi,
            "gi_source": "Atkinson et al., Diabetes Care 2008;31:2281-3" if gi is not None else None,
            "gi_verified": False,
            "aliases": [*ALIASES.get(code, []), *ALIASES_EN.get(code, [])],
            "portion": {"description": pdesc, "grams": pg,
                        "source": f"USDA food_portion (fdc_id {fdc_id})"} if pg else None,
            "source": {
                "dataset": DATASET,
                "fdc_id": fdc_id,
                "description": foods[fdc_id]["description"],
                "publication_date": foods[fdc_id]["publication_date"],
                "url": f"https://fdc.nal.usda.gov/food-details/{fdc_id}/nutrients",
            },
            "per_100g": nutr,
            "unverified_nutrients": missing,
        })
    return out


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit(__doc__)
    data = build(Path(sys.argv[1]))
    Path(sys.argv[2]).write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"Đã ghi {len(data)} nguyên liệu → {sys.argv[2]}")
