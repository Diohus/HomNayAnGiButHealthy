from app.core.i18n import Lang, tr
from app.nutrition import references as R
from app.nutrition.schemas import (
    DIABETES,
    Condition,
    ExpertLimits,
    HealthProfileIn,
    LowEnergyNotAcknowledged,
    NutrientTarget,
    NutritionNeeds,
    Reference,
    Sex,
)

TOLERANCE = 0.05


def mifflin_st_jeor(sex: Sex, weight_kg: float, height_cm: float, age: int) -> float:
    base = 10 * weight_kg + 6.25 * height_cm - 5 * age
    return base + 5 if sex == Sex.male else base - 161


def _target(code, unit, value, ref, adjusted=None, tol=TOLERANCE) -> NutrientTarget:
    return NutrientTarget(
        code=code, unit=unit, kind="target", value=value,
        lower=value * (1 - tol), upper=value * (1 + tol), reference=ref, adjusted_for=adjusted or [],
    )


def compute_needs(p: HealthProfileIn, expert_limits: ExpertLimits | None = None,
                  tolerance: float = TOLERANCE, lang: Lang = "vi") -> NutritionNeeds:
    """Tính nhu cầu hằng ngày. Ném LowEnergyNotAcknowledged nếu mục tiêu tự đặt dưới sàn mà chưa xác nhận.
    `lang` chỉ ảnh hưởng chữ hiển thị (nguồn, ghi chú, giả định), không ảnh hưởng số liệu."""
    warnings: list[str] = []
    assumptions: list[str] = []
    applies = tr("ref.applies.male" if p.sex == Sex.male else "ref.applies.female", lang, age=p.age)
    adults = tr("ref.applies.adults", lang)
    expert_source = tr("ref.expert_limit", lang)

    # --- Năng lượng ---
    bmr = mifflin_st_jeor(p.sex, p.weight_kg, p.height_cm, p.age)
    factor = R.ACTIVITY_FACTORS[p.activity_level]
    tdee = bmr * factor
    floor = max(bmr, R.ENERGY_FLOOR[p.sex])
    energy_adjust: list[str] = []

    if p.custom_target_kcal is not None:
        energy = float(p.custom_target_kcal)
        energy_adjust.append("custom_target")
        if energy < floor:
            if not p.acknowledge_low_energy:
                raise LowEnergyNotAcknowledged(energy, floor)
            warnings.append("LOW_ENERGY_ACKNOWLEDGED")
    else:
        energy = tdee * (1 + R.GOAL_ENERGY_ADJ[p.goal.value])
        if p.goal.value != "maintain":
            energy_adjust.append(f"goal:{p.goal.value}")
            assumptions.append(tr("assumption.goal_energy", lang))
        if energy < floor:
            energy = floor
            energy_adjust.append("energy_floor")
            warnings.append("ENERGY_RAISED_TO_FLOOR")

    if expert_limits and expert_limits.energy_kcal_max and energy > expert_limits.energy_kcal_max:
        energy = expert_limits.energy_kcal_max
        energy_adjust.append("expert_limit")

    # --- Protein ---
    if p.goal.value == "gain_muscle":
        protein_g = R.PROTEIN_GAIN_G_PER_KG * p.weight_kg
        protein_ref = Reference(source=R.ISSN_PROTEIN, applies_to=tr("ref.applies.athletes", lang),
                                note=tr("ref.note.protein_gain", lang))
    else:
        protein_g = max(R.PROTEIN_RDA_G_PER_KG * p.weight_kg, 0.15 * energy / 4)
        protein_ref = Reference(source=R.DRI_MACRO, applies_to=adults, note=tr("ref.note.protein", lang))
    protein_g = min(protein_g, R.AMDR["protein"][1] * energy / 4)
    protein_adjust = []
    if expert_limits and expert_limits.protein_g_max and protein_g > expert_limits.protein_g_max:
        protein_g = expert_limits.protein_g_max
        protein_adjust.append("expert_limit")

    # --- Carb / Fat ---
    p_kcal = protein_g * 4
    carb_adjust: list[str] = []
    if set(p.conditions) & DIABETES:
        carb_kcal = max(R.AMDR["carb"][0] * energy, R.CARB_RDA_G * 4)
        fat_kcal = energy - p_kcal - carb_kcal
        carb_adjust.append("diabetes")
        assumptions.append(tr(R.DIABETES_NOTE, lang))
        fat_max = R.AMDR["fat"][1] * energy
        if fat_kcal > fat_max:  # đẩy phần dư sang protein, vẫn trong AMDR
            extra = fat_kcal - fat_max
            fat_kcal = fat_max
            p_kcal = min(p_kcal + extra, R.AMDR["protein"][1] * energy)
            protein_g = p_kcal / 4
    else:
        fat_kcal = 0.30 * energy
        carb_kcal = energy - p_kcal - fat_kcal
        lo, hi = R.AMDR["carb"]
        if carb_kcal > hi * energy:
            shift = min(carb_kcal - hi * energy, R.AMDR["fat"][1] * energy - fat_kcal)
            fat_kcal += shift
            carb_kcal -= shift
        elif carb_kcal < lo * energy:
            shift = min(lo * energy - carb_kcal, fat_kcal - R.AMDR["fat"][0] * energy)
            fat_kcal -= shift
            carb_kcal += shift
    fat_kcal = max(fat_kcal, R.AMDR["fat"][0] * energy)

    macro_ref = Reference(source=R.DRI_MACRO, applies_to=adults, note=tr("ref.note.amdr", lang))
    targets = [
        _target("energy_kcal", "kcal", energy, Reference(
            source=f"{R.MIFFLIN}; {tr(R.ACTIVITY_SOURCE, lang)}", applies_to=applies,
            note=tr("ref.note.energy", lang, bmr=f"{bmr:.0f}", factor=factor, tdee=f"{tdee:.0f}",
                    floor=f"{floor:.0f}", floor_source=tr(R.ENERGY_FLOOR_SOURCE, lang)),
        ), energy_adjust, tolerance),
        _target("protein_g", "g", protein_g, protein_ref, protein_adjust, tolerance),
        _target("carb_g", "g", carb_kcal / 4, macro_ref, carb_adjust, tolerance),
        _target("fat_g", "g", fat_kcal / 9, macro_ref, [], tolerance),
        NutrientTarget(code="fiber_g", unit="g", kind="min", value=R.FIBER_G_PER_1000_KCAL * energy / 1000,
                       reference=Reference(source=R.DRI_MACRO, applies_to=adults, note="AI 14 g / 1000 kcal")),
    ]

    # --- Vi chất ---
    for code, spec in R.MICRO_RDA.items():
        rda = R.band_value(spec["bands"], p.age, p.sex)
        ul = spec.get("ul") or R.band_ul(spec["ul_bands"], p.age)
        targets.append(NutrientTarget(
            code=code, unit=spec["unit"], kind="min", value=rda, upper=ul,
            reference=Reference(source=spec["source"], applies_to=applies, note=f"RDA {rda:g}; UL {ul:g}"),
        ))

    sodium_max, sodium_ref, sodium_adj = R.SODIUM_CDRR_MG, tr(R.SODIUM_SOURCE, lang), []
    if Condition.hypertension in p.conditions:
        sodium_max, sodium_ref, sodium_adj = R.SODIUM_HTN_MG, tr(R.SODIUM_HTN_SOURCE, lang), ["hypertension"]
    if expert_limits and expert_limits.sodium_mg_max:
        sodium_max, sodium_ref, sodium_adj = expert_limits.sodium_mg_max, expert_source, ["expert_limit"]
    targets.append(NutrientTarget(
        code="sodium_mg", unit="mg", kind="max", value=sodium_max,
        reference=Reference(source=sodium_ref, applies_to=applies, note=tr("ref.note.sodium", lang)),
        adjusted_for=sodium_adj,
    ))
    if expert_limits:
        for code, attr in (("potassium_mg", "potassium_mg_max"), ("phosphorus_mg", "phosphorus_mg_max")):
            v = getattr(expert_limits, attr)
            if v:
                targets.append(NutrientTarget(
                    code=code, unit="mg", kind="max", value=v,
                    reference=Reference(source=expert_source),
                    adjusted_for=["expert_limit"],
                ))

    if set(p.conditions) & DIABETES and p.uses_insulin_or_glucose_meds:
        warnings.append("CONSULT_DOCTOR_INSULIN")

    slots = R.MEAL_SLOTS[p.activity_level]
    return NutritionNeeds(
        bmr_kcal=bmr, activity_factor=factor, tdee_kcal=tdee, energy_floor_kcal=floor,
        meals_per_day=len(slots), meal_slots=slots, targets=targets,
        warnings=warnings, assumptions=assumptions,
    )
