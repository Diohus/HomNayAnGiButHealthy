"""Hằng số tham chiếu — mỗi giá trị đi kèm nguồn. Xem docs/DATA_SOURCES.md."""

from app.nutrition.schemas import ActivityLevel, Sex

MIFFLIN = "Mifflin MD et al. A new predictive equation for resting energy expenditure. Am J Clin Nutr 1990;51:241-7"

# Hệ số hoạt động (PAL) — bộ hệ số phổ biến dùng kèm Mifflin-St Jeor
# (McArdle WD, Katch FI, Katch VL. Exercise Physiology). GIẢ ĐỊNH: sai số cá nhân ±10% trở lên.
ACTIVITY_FACTORS: dict[ActivityLevel, float] = {
    ActivityLevel.sedentary: 1.2,  # ít/không tập
    ActivityLevel.light: 1.375,  # tập nhẹ 1–3 ngày/tuần
    ActivityLevel.moderate: 1.55,  # tập vừa 3–5 ngày/tuần
    ActivityLevel.active: 1.725,  # tập nặng 6–7 ngày/tuần
    ActivityLevel.very_active: 1.9,  # lao động nặng / tập 2 lần/ngày
}
ACTIVITY_SOURCE = "ref.activity_source"  # khóa i18n: McArdle, Katch & Katch, Exercise Physiology — giả định

# Quyết định sản phẩm (không phải khuyến nghị y khoa)
MEAL_SLOTS: dict[ActivityLevel, list[str]] = {
    ActivityLevel.sedentary: ["lunch", "dinner"],
    ActivityLevel.light: ["lunch", "dinner"],
    ActivityLevel.moderate: ["breakfast", "lunch", "dinner"],
    ActivityLevel.active: ["breakfast", "lunch", "dinner"],
    ActivityLevel.very_active: ["breakfast", "lunch", "dinner"],
}

# Điều chỉnh năng lượng theo mục tiêu — GIẢ ĐỊNH, cần chuyên gia duyệt
GOAL_ENERGY_ADJ = {"lose": -0.15, "maintain": 0.0, "gain_muscle": 0.10}

# Sàn năng lượng — NHLBI. Clinical Guidelines on the Identification, Evaluation, and Treatment of
# Overweight and Obesity in Adults (1998): chế độ giảm cân 1000–1200 kcal/ngày cho nữ, 1200–1600 cho nam.
# Ứng dụng lấy cận trên an toàn hơn: 1200 nữ / 1500 nam — CẦN XÁC MINH LẠI với chuyên gia.
ENERGY_FLOOR = {Sex.female: 1200.0, Sex.male: 1500.0}
ENERGY_FLOOR_SOURCE = "ref.energy_floor_source"  # khóa i18n: NHLBI Obesity Education Initiative 1998

DRI_MACRO = "Institute of Medicine. Dietary Reference Intakes for Energy, Carbohydrate, Fiber, Fat, Fatty Acids, Cholesterol, Protein, and Amino Acids. 2005"
ISSN_PROTEIN = "Jäger R et al. ISSN Position Stand: protein and exercise. J Int Soc Sports Nutr 2017;14:20"
AMDR = {"carb": (0.45, 0.65), "fat": (0.20, 0.35), "protein": (0.10, 0.35)}
PROTEIN_RDA_G_PER_KG = 0.8
PROTEIN_GAIN_G_PER_KG = 1.6  # ISSN 2017: 1.4–2.0 g/kg/ngày
CARB_RDA_G = 130.0  # IOM 2005, người trưởng thành
FIBER_G_PER_1000_KCAL = 14.0  # IOM 2005 AI

# Vi chất — NIH Office of Dietary Supplements, Health Professional Fact Sheets (dựa trên IOM/NASEM DRI).
# (age_min, age_max, male, female)
NIH_ODS = "NIH Office of Dietary Supplements – Health Professional Fact Sheet"
MICRO_RDA: dict[str, dict] = {
    "iron_mg": {
        "unit": "mg", "source": f"{NIH_ODS}: Iron (RDA)", "ul": 45.0,
        "bands": [(18, 18, 11.0, 15.0), (19, 50, 8.0, 18.0), (51, 200, 8.0, 8.0)],
    },
    "zinc_mg": {
        "unit": "mg", "source": f"{NIH_ODS}: Zinc (RDA)", "ul": 40.0,
        "bands": [(18, 18, 11.0, 9.0), (19, 200, 11.0, 8.0)],
    },
    "calcium_mg": {
        "unit": "mg", "source": f"{NIH_ODS}: Calcium (RDA)", "ul_bands": [(18, 18, 3000.0), (19, 50, 2500.0), (51, 200, 2000.0)],
        "bands": [(18, 18, 1300.0, 1300.0), (19, 50, 1000.0, 1000.0), (51, 70, 1000.0, 1200.0), (71, 200, 1200.0, 1200.0)],
    },
    "vitamin_d_ug": {
        "unit": "µg", "source": f"{NIH_ODS}: Vitamin D (RDA)", "ul": 100.0,
        "bands": [(18, 70, 15.0, 15.0), (71, 200, 20.0, 20.0)],
    },
}

SODIUM_CDRR_MG = 2300.0
SODIUM_SOURCE = "ref.sodium_source"  # khóa i18n: NASEM DRI Sodium and Potassium 2019 (CDRR)
SODIUM_HTN_MG = 1500.0
SODIUM_HTN_SOURCE = "ref.sodium_htn_source"  # khóa i18n: American Heart Association ≤1500 mg/ngày

DIABETES_NOTE = "assumption.diabetes_carb"  # khóa i18n: ADA Standards of Care — carb 45% AMDR, ≥130 g/ngày


def band_value(bands, age: int, sex: Sex) -> float:
    for lo, hi, m, f in bands:
        if lo <= age <= hi:
            return m if sex == Sex.male else f
    raise ValueError("age out of band")


def band_ul(bands, age: int) -> float:
    for lo, hi, v in bands:
        if lo <= age <= hi:
            return v
    raise ValueError("age out of band")
