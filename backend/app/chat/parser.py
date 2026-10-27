"""Hiểu câu chat. Ưu tiên LLM (schema + validate + retry), luôn có parser quy tắc dự phòng."""

import re

from app.ai.providers import LLMProvider
from app.ai.service import call_structured
from app.chat.schemas import ParsedIntent
from app.foods.matching import normalize
from app.guardrails.eating_disorder import detect_text_signals

SLOT_WORDS = [  # (cụm không dấu, slot)
    ("an vat", "snack"), ("an xe", "snack"), ("bua phu", "snack"), ("trang mieng", "snack"),
    ("buoi sang", "breakfast"), ("bua sang", "breakfast"), ("sang nay", "breakfast"), ("an sang", "breakfast"),
    ("buoi trua", "lunch"), ("bua trua", "lunch"), ("trua nay", "lunch"), ("an trua", "lunch"),
    ("buoi toi", "dinner"), ("bua toi", "dinner"), ("toi nay", "dinner"), ("an toi", "dinner"),
    # en
    ("snack", "snack"), ("snacks", "snack"), ("dessert", "snack"),
    ("breakfast", "breakfast"), ("this morning", "breakfast"),
    ("lunch", "lunch"), ("at noon", "lunch"),
    ("dinner", "dinner"), ("supper", "dinner"), ("tonight", "dinner"), ("this evening", "dinner"),
]
CHEAT_WORDS = ["cheat", "xa lang", "pha le", "tha ga", "an buffet", "hom nay an thoai mai", "treat myself"]
WANT_WORDS = ["muon an", "them", "an ", "cho toi", "thich an", "uong",
              " want ", " eat ", " have ", " drink ", " craving ", " add ", " like "]
TOMORROW_WORDS = [" ngay mai ", " mai ", " tomorrow "]
QTY = re.compile(r"(\d+(?:[.,]\d+)?)\s*(kg|g|gr|gram|ml|l|lít|lit)?(?![\w])(?!\s*(giờ|h|phút|ngày|tuổi|lần|tháng|năm|kcal|calo))",
                 re.IGNORECASE)


def rule_parse(text: str) -> ParsedIntent:
    norm = normalize(text)
    slot = next((s for w, s in SLOT_WORDS if f" {w} " in norm), None)
    day = "tomorrow" if any(w in norm for w in TOMORROW_WORDS) else None
    cheat = any(f" {w} " in norm or w in norm for w in CHEAT_WORDS)
    qv, qu = None, None
    if m := QTY.search(text.lower()):
        qv = float(m.group(1).replace(",", "."))
        unit = (m.group(2) or "").lower()
        if unit in ("g", "gr", "gram"):
            qu = "g"
        elif unit == "kg":
            qv, qu = qv * 1000, "g"
        elif unit == "ml":
            qu = "ml"
        elif unit in ("l", "lit", "lít"):
            qv, qu = qv * 1000, "ml"
        else:
            qu = "portion"
    if detect_text_signals(text):
        intent = "restrict"
    elif any(w in norm for w in WANT_WORDS):
        intent = "want_food"
    elif text.strip().endswith("?"):
        intent = "question"
    else:
        intent = "other"
    return ParsedIntent(intent=intent, mentions=[], quantity_value=qv, quantity_unit=qu, slot=slot, day=day,
                        cheat_day=cheat)


# Prompt hệ thống (không hiển thị cho người dùng). Câu chat có thể bằng tiếng Việt hoặc tiếng Anh.
SYSTEM = (
    "You analyse chat messages from users of a meal-planning app. Messages may be in Vietnamese or English. "
    "Return JSON matching the schema. intent=want_food when the user wants to eat/drink something; restrict when "
    "they want to fast, skip meals or eat extremely little; question when asking for information; other otherwise. "
    "mentions: list the food/drink names exactly as written in the message, in the user's language "
    "(e.g. 'gà', 'kem', 'trà sữa', 'chicken', 'ice cream'). Only fill quantity_value if the user states a number. "
    "slot: the meal the user refers to (snack for snacks/desserts). day: today/tomorrow only if stated. "
    "Never guess nutrition values."
)


def _validate(text: str):
    digits = set(re.findall(r"\d+(?:[.,]\d+)?", text))

    def check(p: ParsedIntent) -> list[str]:
        problems = []
        if p.quantity_value is not None:
            v = p.quantity_value
            shown = {f"{v:g}", f"{v:.0f}" if v.is_integer() else f"{v:g}", str(v).replace(".", ",")}
            if not (shown & digits) and not any(abs(float(d.replace(",", ".")) - v) < 1e-9 or
                                                abs(float(d.replace(",", ".")) * 1000 - v) < 1e-9 for d in digits):
                problems.append("QUANTITY_NOT_IN_TEXT")  # LLM không được bịa số lượng
        if p.quantity_value is not None and (p.quantity_value <= 0 or p.quantity_value > 5000):
            problems.append("QUANTITY_RANGE")
        return problems

    return check


def parse(text: str, provider: LLMProvider | None, max_retries: int = 2) -> tuple[ParsedIntent, str]:
    rules = rule_parse(text)
    out, status = call_structured(provider, SYSTEM, text[:1000], ParsedIntent, max_retries, validate=_validate(text))
    if out is None:
        return rules, "rules"
    # Tín hiệu an toàn từ quy tắc luôn được giữ, dù LLM nói gì
    if rules.intent == "restrict":
        out.intent = "restrict"
    out.cheat_day = out.cheat_day or rules.cheat_day
    return out, "llm"
