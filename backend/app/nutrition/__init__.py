"""(b) Bộ tính nhu cầu dinh dưỡng — thuần Python, không I/O, test độc lập."""

from app.nutrition.calculator import compute_needs
from app.nutrition.schemas import (
    ActivityLevel,
    Allergen,
    Condition,
    Diet,
    ExpertLimits,
    Goal,
    HealthProfileIn,
    LowEnergyNotAcknowledged,
    NutritionNeeds,
    Sex,
)

__all__ = [
    "ActivityLevel", "Allergen", "Condition", "Diet", "ExpertLimits", "Goal", "HealthProfileIn",
    "LowEnergyNotAcknowledged", "NutritionNeeds", "Sex", "compute_needs",
]
