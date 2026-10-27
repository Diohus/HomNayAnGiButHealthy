"""(a) Bộ tính nhu cầu dinh dưỡng — test độc lập, không DB."""

import pytest
from pydantic import ValidationError

from app.nutrition import HealthProfileIn, LowEnergyNotAcknowledged, compute_needs
from app.nutrition.calculator import mifflin_st_jeor
from app.nutrition.references import ACTIVITY_FACTORS

P = dict(sex="male", age=30, height_cm=175, weight_kg=70, activity_level="moderate", goal="maintain")


def test_mifflin_known_values():
    # 10*70 + 6.25*175 - 5*30 + 5 = 1648.75 ; nữ: -161
    assert mifflin_st_jeor("male", 70, 175, 30) == pytest.approx(1648.75)
    assert mifflin_st_jeor("female", 70, 175, 30) == pytest.approx(1482.75)


def test_tdee_uses_documented_factor():
    n = compute_needs(HealthProfileIn(**P))
    assert n.activity_factor == ACTIVITY_FACTORS["moderate"] == 1.55
    assert n.tdee_kcal == pytest.approx(1648.75 * 1.55)
    assert n.get("energy_kcal").value == pytest.approx(n.tdee_kcal)


def test_meals_per_day_by_activity():
    assert compute_needs(HealthProfileIn(**{**P, "activity_level": "sedentary"})).meal_slots == ["lunch", "dinner"]
    assert compute_needs(HealthProfileIn(**{**P, "activity_level": "light"})).meals_per_day == 2
    assert compute_needs(HealthProfileIn(**{**P, "activity_level": "active"})).meals_per_day == 3


def test_macros_within_amdr():
    for goal in ("lose", "maintain", "gain_muscle"):
        n = compute_needs(HealthProfileIn(**{**P, "goal": goal}))
        e = n.get("energy_kcal").value
        assert 0.45 <= n.get("carb_g").value * 4 / e <= 0.65 + 1e-9
        assert 0.20 - 1e-9 <= n.get("fat_g").value * 9 / e <= 0.35 + 1e-9
        assert 0.10 <= n.get("protein_g").value * 4 / e <= 0.35 + 1e-9
        total = (n.get("carb_g").value + n.get("protein_g").value) * 4 + n.get("fat_g").value * 9
        assert total == pytest.approx(e, rel=1e-6)


def test_every_target_has_source_and_micros_have_age_sex():
    n = compute_needs(HealthProfileIn(**{**P, "sex": "female", "age": 25}))
    for t in n.targets:
        assert t.reference.source
    iron = n.get("iron_mg")
    assert iron.value == 18 and iron.upper == 45 and iron.reference.applies_to == "nữ, 25 tuổi"
    assert compute_needs(HealthProfileIn(**{**P, "age": 75})).get("vitamin_d_ug").value == 20


def test_energy_floor_never_below_bmr_or_sex_floor():
    small = HealthProfileIn(sex="female", age=60, height_cm=150, weight_kg=45, activity_level="sedentary", goal="lose")
    n = compute_needs(small)
    assert n.get("energy_kcal").value >= max(n.bmr_kcal, 1200)
    assert "ENERGY_RAISED_TO_FLOOR" in n.warnings


def test_custom_low_target_requires_ack():
    p = HealthProfileIn(**{**P, "custom_target_kcal": 1000})
    with pytest.raises(LowEnergyNotAcknowledged):
        compute_needs(p)
    n = compute_needs(HealthProfileIn(**{**P, "custom_target_kcal": 1000, "acknowledge_low_energy": True}))
    assert "LOW_ENERGY_ACKNOWLEDGED" in n.warnings


def test_custom_target_below_800_rejected():
    with pytest.raises(ValidationError):
        HealthProfileIn(**{**P, "custom_target_kcal": 600, "acknowledge_low_energy": True})


def test_diabetes_carb_control_and_floor():
    n = compute_needs(HealthProfileIn(**{**P, "conditions": ["diabetes_t2"]}))
    e = n.get("energy_kcal").value
    assert n.get("carb_g").value * 4 / e == pytest.approx(0.45, abs=0.01)
    assert n.get("carb_g").value >= 130
    assert any("ADA" in a for a in n.assumptions)


def test_insulin_reminder_flag():
    n = compute_needs(HealthProfileIn(**{**P, "conditions": ["diabetes_t1"], "uses_insulin_or_glucose_meds": True}))
    assert "CONSULT_DOCTOR_INSULIN" in n.warnings


def test_hypertension_sodium_limit():
    n = compute_needs(HealthProfileIn(**{**P, "conditions": ["hypertension"]}))
    assert n.get("sodium_mg").value == 1500 and n.get("sodium_mg").kind == "max"
