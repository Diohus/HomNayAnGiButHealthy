"""Bù năng lượng sau "cheat day" — chính sách đã được người dùng duyệt (bù có giới hạn).

Mọi ngưỡng dưới đây là GIẢ ĐỊNH SẢN PHẨM, cần chuyên gia dinh dưỡng duyệt:
- Mỗi ngày sau giảm tối đa 10% mục tiêu năng lượng, tối đa 3 ngày.
- Không bao giờ dưới sàn năng lượng của ngày đó.
- Phần vượt còn lại được BỎ QUA (không dồn tiếp) — tránh vòng lặp cắt giảm bù trừ.
- Ngày cheat day: các bữa chính vẫn giữ ≥ 50% năng lượng mục tiêu (không bỏ bữa để "nhường" cho đồ ăn vặt).
"""

from datetime import date

from pydantic import BaseModel

MAX_DAILY_REDUCTION_PCT = 0.10
MAX_DAYS = 3
MEAL_FLOOR_SHARE = 0.50
# Guardrail: bù quá 2 lần trong 14 ngày ⇒ tín hiệu rối loạn ăn uống (xem guardrails.eating_disorder)


class DayEnergy(BaseModel):
    day: date
    target_kcal: float
    floor_kcal: float


class Reduction(BaseModel):
    day: date
    kcal: float


class CompensationPlan(BaseModel):
    overflow_kcal: float
    reductions: list[Reduction]
    forgiven_kcal: float


def plan_compensation(overflow_kcal: float, next_days: list[DayEnergy]) -> CompensationPlan:
    remaining = max(overflow_kcal, 0.0)
    reductions: list[Reduction] = []
    for d in sorted(next_days, key=lambda x: x.day)[:MAX_DAYS]:
        if remaining <= 0:
            break
        cap = min(MAX_DAILY_REDUCTION_PCT * d.target_kcal, max(d.target_kcal - d.floor_kcal, 0.0))
        r = min(cap, remaining)
        if r > 0:
            reductions.append(Reduction(day=d.day, kcal=r))
            remaining -= r
    return CompensationPlan(overflow_kcal=max(overflow_kcal, 0.0), reductions=reductions,
                            forgiven_kcal=max(remaining, 0.0))


def cheat_day_energy(target_kcal: float, snack_kcal: float) -> float:
    """Năng lượng ngày cheat day: bữa chính vẫn giữ ≥ MEAL_FLOOR_SHARE × mục tiêu."""
    return max(target_kcal, snack_kcal + MEAL_FLOOR_SHARE * target_kcal)
