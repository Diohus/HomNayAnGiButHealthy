from datetime import date
from typing import Literal

from pydantic import BaseModel, Field
from pydantic.json_schema import SkipJsonSchema

from app.nutrition.compensation import CompensationPlan
from app.planner.schemas import DayPlan

Slot = Literal["breakfast", "lunch", "dinner", "snack"]


class ParsedIntent(BaseModel):
    """Schema đầu ra LLM (và parser quy tắc). Chỉ mô tả ý định, không chứa số liệu dinh dưỡng."""

    intent: Literal["want_food", "log_food", "question", "restrict", "dislike", "allergy", "other"]
    mentions: list[str] = Field(max_length=5, description="Food/drink names the user mentioned, verbatim")
    quantity_value: float | None = Field(description="Quantity explicitly stated by the user, if any")
    quantity_unit: Literal["portion", "g", "ml"] | None
    slot: Slot | None
    day: Literal["today", "tomorrow"] | None
    cheat_day: bool = Field(description="User explicitly says today is a cheat day")
    # Chỉ do parser quy tắc điền (không có trong schema LLM): cụm sau "không thích/không ăn được/don't like"
    dislike_object: SkipJsonSchema[str | None] = None


class DetectedFood(BaseModel):
    food_code: str
    name: str
    role: str  # main | side | snack
    allowed: bool
    reason: str | None = None
    dish_code: str | None = None  # LLM nhận ra đúng một món trong catalog (K1)


class Proposal(BaseModel):
    key: str  # absorb | plan_update | smaller_portion | cheat_day | preference
    label: str
    day: date
    plan: DayPlan | None = None  # None với key=preference
    preference: dict | None = None  # {"kind": "food" | "dish" | "text", "code": ...} — danh sách không thích
    intake: list[dict] | None = None  # key=log: [{"slot", "food_code", "grams", "source"}] — ghi nhật ký đã ăn
    compensation: CompensationPlan | None = None
    snacks: list[dict] = []  # [{"food_code", "grams"}] — đồ ăn vặt mới, ghi nhận khi áp dụng
    records_compensation_event: bool = False


class ChatReply(BaseModel):
    kind: str  # info | proposal | warning | refusal | support | need_label | clarify | allergy_redirect
    text: str
    clarify: list[dict] = []  # [{mention, options: [{code: "food:x"|"dish:y", name}]}] — nút chọn nhanh
    detected: list[DetectedFood] = []
    unknown_mentions: list[str] = []
    proposals: list[Proposal] = []
    safety_events: list[str] = []  # loại sự kiện cần ghi nhận (service lưu)
    parser: str = "rules"  # llm | rules
