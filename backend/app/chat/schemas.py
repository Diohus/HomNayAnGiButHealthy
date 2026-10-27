from datetime import date
from typing import Literal

from pydantic import BaseModel, Field

from app.nutrition.compensation import CompensationPlan
from app.planner.schemas import DayPlan

Slot = Literal["breakfast", "lunch", "dinner", "snack"]


class ParsedIntent(BaseModel):
    """Schema đầu ra LLM (và parser quy tắc). Chỉ mô tả ý định, không chứa số liệu dinh dưỡng."""

    intent: Literal["want_food", "question", "restrict", "other"]
    mentions: list[str] = Field(max_length=5, description="Food/drink names the user mentioned, verbatim")
    quantity_value: float | None = Field(description="Quantity explicitly stated by the user, if any")
    quantity_unit: Literal["portion", "g", "ml"] | None
    slot: Slot | None
    day: Literal["today", "tomorrow"] | None
    cheat_day: bool = Field(description="User explicitly says today is a cheat day")


class DetectedFood(BaseModel):
    food_code: str
    name: str
    role: str  # main | side | snack
    allowed: bool
    reason: str | None = None


class Proposal(BaseModel):
    key: str  # absorb | plan_update | smaller_portion | cheat_day
    label: str
    day: date
    plan: DayPlan
    compensation: CompensationPlan | None = None
    snacks: list[dict] = []  # [{"food_code", "grams"}] — đồ ăn vặt mới, ghi nhận khi áp dụng
    records_compensation_event: bool = False


class ChatReply(BaseModel):
    kind: str  # info | proposal | warning | refusal | support | need_label
    text: str
    detected: list[DetectedFood] = []
    unknown_mentions: list[str] = []
    proposals: list[Proposal] = []
    safety_events: list[str] = []  # loại sự kiện cần ghi nhận (service lưu)
    parser: str = "rules"  # llm | rules
