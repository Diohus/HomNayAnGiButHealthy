"""Chuyển nhu cầu dinh dưỡng → mục tiêu cho planner, có điều chỉnh năng lượng theo ngày.

Khi năng lượng ngày thay đổi (bù cheat day, hoặc ngày cheat day), giữ nguyên đạm và co giãn carb/chất béo
theo tỉ lệ năng lượng — GIẢ ĐỊNH sản phẩm.
"""

from app.nutrition.schemas import NutritionNeeds
from app.planner.schemas import PlannerTarget


def day_energy(needs: NutritionNeeds, delta_kcal: float = 0.0) -> float:
    base = needs.get("energy_kcal").value
    return max(base + delta_kcal, needs.energy_floor_kcal) if delta_kcal < 0 else base + delta_kcal


def planner_targets(needs: NutritionNeeds, energy_kcal: float | None = None) -> list[PlannerTarget]:
    base_e = needs.get("energy_kcal").value
    e = energy_kcal if energy_kcal is not None else base_e
    protein = needs.get("protein_g").value
    # năng lượng không đến từ đạm được phân bổ lại cho carb/béo theo tỉ lệ gốc
    rest_base = base_e - protein * 4
    rest_new = max(e - protein * 4, 0.0)
    k = rest_new / rest_base if rest_base > 0 else 1.0
    out = []
    for t in needs.targets:
        v = t.value
        if t.code == "energy_kcal":
            v = e
        elif t.code in ("carb_g", "fat_g"):
            v = t.value * k
        elif t.code == "fiber_g":
            v = t.value * e / base_e
        out.append(PlannerTarget(code=t.code, kind=t.kind, value=v))
    return out
