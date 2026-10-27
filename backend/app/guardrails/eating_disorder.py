"""Phát hiện tín hiệu rối loạn ăn uống — chỉ dựa trên loại sự kiện + thời điểm (không lưu nội dung).

Ngưỡng là GIẢ ĐỊNH SẢN PHẨM, cần chuyên gia duyệt:
- LOW_TARGET_ATTEMPT: ≥3 lần đặt mục tiêu dưới sàn trong 14 ngày.
- DECREASE_WHEN_MET: ≥5 lần bấm giảm khi đã đạt ≥100% năng lượng trong cùng 1 ngày.
- COMPENSATION: >2 lần bù cheat day trong 14 ngày.
- RESTRICT_INTENT: ≥2 lần trong 14 ngày người dùng nói muốn nhịn/cắt giảm cực đoan (chat).
- DISTRESS: 1 lần là đủ (nôn sau ăn, dùng thuốc xổ để giảm cân, ...).
Khi bị gắn cờ: không tối ưu cắt giảm, không bù cheat day, hiển thị thông điệp hỗ trợ.
"""

from datetime import datetime, timedelta

from pydantic import BaseModel

from app.foods.matching import normalize

SUPPORT_KEY = "support.message"  # thông điệp hỗ trợ (app/i18n) — cùng nội dung với error.ED_SUPPORT

RULES = {  # loại sự kiện → (số lần, cửa sổ)
    "LOW_TARGET_ATTEMPT": (3, timedelta(days=14)),
    "DECREASE_WHEN_MET": (5, timedelta(days=1)),
    "COMPENSATION": (3, timedelta(days=14)),
    "RESTRICT_INTENT": (2, timedelta(days=14)),
    "DISTRESS": (1, timedelta(days=30)),
}

# Cụm từ (đã chuẩn hóa: chữ thường, không dấu, bỏ dấu câu). Tiếng Việt + tiếng Anh.
# Danh sách tối thiểu — GIẢ ĐỊNH, cần chuyên gia mở rộng. Tránh cụm mơ hồ ("i'm starving" = rất đói, KHÔNG phải nhịn).
RESTRICT_PHRASES = [
    "nhin an", "bo bua", "khong an gi", "an it nhat co the", "an duoi 800", "an 500 kcal", "nhin doi",
    "cat het tinh bot", "nhin ca ngay",
    # en
    "skip meals", "skip all meals", "skipping meals", "stop eating", "not eat anything", "eat nothing",
    "starve myself", "starving myself", "starve all day", "fast all day", "eat as little as possible",
    "under 800 calories", "under 800 kcal", "only 500 calories", "cut all carbs",
]
DISTRESS_PHRASES = [
    "moc hong", "tu gay non", "non sau khi an", "non ra", "thuoc xo de giam can", "thuoc nhuan trang de giam can",
    "ghet co the", "an xong thay toi loi", "phat ban than",
    # en
    "make myself throw up", "make myself vomit", "made myself throw up", "throw up after eating",
    "vomit after eating", "purging", "laxatives to lose weight", "laxative to lose weight", "hate my body",
    "feel guilty after eating", "punish myself",
]


class SafetyEventIn(BaseModel):
    kind: str
    at: datetime


class EDStatus(BaseModel):
    flagged: bool
    reasons: list[str] = []


def assess(events: list[SafetyEventIn], now: datetime) -> EDStatus:
    reasons = []
    for kind, (count, window) in RULES.items():
        n = sum(1 for e in events if e.kind == kind and now - window <= e.at <= now)
        if n >= count:
            reasons.append(kind)
    return EDStatus(flagged=bool(reasons), reasons=reasons)


def would_flag(events: list[SafetyEventIn], new_kind: str, now: datetime) -> bool:
    return assess([*events, SafetyEventIn(kind=new_kind, at=now)], now).flagged


def detect_text_signals(text: str) -> list[str]:
    norm = normalize(text)
    kinds = []
    if any(f" {p} " in norm for p in DISTRESS_PHRASES):
        kinds.append("DISTRESS")
    if any(f" {p} " in norm for p in RESTRICT_PHRASES):
        kinds.append("RESTRICT_INTENT")
    return kinds
