"""(c)+(d) Bộ sinh thực đơn có ràng buộc (ILP, PuLP/CBC) + rebalance +/- + nguyên liệu có sẵn.

Không phụ thuộc DB hay LLM: input/output là DTO thuần, test độc lập.
"""

from app.planner.rotation import forbidden_mains, max_consecutive_run
from app.planner.schemas import (
    DayPlan,
    LockedItem,
    MealPlan,
    MealStructure,
    PlanItem,
    PlannerTarget,
    PlanRequest,
    Requirement,
)
from app.planner.solver import solve_day

__all__ = [
    "DayPlan", "LockedItem", "MealPlan", "MealStructure", "PlanItem", "PlanRequest", "PlannerTarget", "Requirement",
    "forbidden_mains", "max_consecutive_run", "solve_day",
]
