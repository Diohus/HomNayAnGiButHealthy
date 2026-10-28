"""Hiểu câu chat. Ưu tiên LLM (schema + validate + retry), luôn có parser quy tắc dự phòng."""

import re

from app.ai.providers import LLMProvider
from app.ai.service import DATA_NOT_INSTRUCTIONS, call_structured
from app.chat.schemas import ParsedIntent
from app.core.cache import LRU
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
# Đã ăn (thì quá khứ) ⇒ ghi nhật ký, không phải đề xuất thực đơn
LOG_WORDS = [" vua an ", " da an ", " an roi ", " moi an ", " vua uong ", " da uong ", " uong roi ", " an xong ",
             " just ate ", " just had ", " i ate ", " i had ", " have eaten ", " already ate ", " ate ", " had "]
# Dấu hiệu quá khứ rõ ràng (N0c): thiếu dấu hiệu này thì "trưa nay ăn cơm tấm" là MUỐN ăn, không phải đã ăn
PAST_WORDS = [" vua ", " da ", " moi ", " roi ", " xong ", " just ", " had ", " ate ", " eaten ", " already ",
              " hom qua ", " toi qua ", " trua qua ", " sang qua ", " yesterday ", " last night "]
PAST_DAY_WORDS = [" hom qua ", " toi qua ", " trua qua ", " sang qua ", " yesterday ", " last night "]
# Mốc "bữa chưa qua" theo giờ hiện tại (sáng < 10h, trưa < 14h, tối < 21h)
SLOT_OVER_HOUR = {"breakfast": 10, "lunch": 14, "dinner": 21}
# Câu nói về dị ứng (ưu tiên cao nhất: không bao giờ đề xuất món người dùng vừa nói bị dị ứng)
ALLERGY_WORDS = [" di ung ", " bi ung ", " allergic ", " allergy ", " allergies "]
# Không thích (ràng buộc mềm). Không dùng "không ăn" trơn: "tôi không ăn sáng" là bỏ bữa, không phải khẩu vị
DISLIKE_WORDS = [" khong an duoc ", " ko an duoc ", " k an duoc ", " ghet ", " khong thich ", " ko thich ",
                 " k thich ", " khong ua ", " don t like ", " dont like ", " do not like ", " hate ", " dislike ",
                 " can t eat ", " cannot eat ", " can t stand "]
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
    if any(w in norm for w in ALLERGY_WORDS):
        intent = "allergy"
    elif detect_text_signals(text):
        intent = "restrict"
    elif any(w in norm for w in DISLIKE_WORDS):
        intent = "dislike"
    elif any(w in norm for w in LOG_WORDS) or any(w in norm for w in PAST_DAY_WORDS) or (
            (" an " in norm or " uong " in norm) and norm.rstrip().endswith(" roi")):
        intent = "log_food"
    elif any(w in norm for w in WANT_WORDS):
        intent = "want_food"
    elif text.strip().endswith("?"):
        intent = "question"
    else:
        intent = "other"
    return ParsedIntent(intent=intent, mentions=[], quantity_value=qv, quantity_unit=qu, slot=slot, day=day,
                        cheat_day=cheat, dislike_object=_dislike_object(text) if intent == "dislike" else None,
                        past_day=any(w in norm for w in PAST_DAY_WORDS))


def has_past_marker(text: str) -> bool:
    norm = normalize(text)
    return any(w in norm for w in PAST_WORDS) or norm.rstrip().endswith(" roi")


def slot_over(slot: str | None, now) -> bool:
    return bool(slot) and now is not None and slot in SLOT_OVER_HOUR and now.hour >= SLOT_OVER_HOUR[slot]


_DISLIKE_RE = re.compile(
    r"(?:không|ko|k)\s+(?:ăn được|an duoc|thích|thich|ưa|ua)|ghét|ghet|don'?t like|do not like|hate|dislike|"
    r"can'?t eat|cannot eat|can'?t stand", re.IGNORECASE)


def _dislike_object(text: str) -> str | None:
    """Cụm ngay sau cụm "không thích…" (fallback khi không có LLM), tối đa 40 ký tự."""
    m = _DISLIKE_RE.search(text)
    if not m:
        return None
    rest = re.split(r"[.,;!?\n]", text[m.end():], maxsplit=1)[0].strip()
    rest = re.sub(r"^(?:ăn|an|eat|eating|món|mon)\s+", "", rest, flags=re.IGNORECASE).strip()
    return rest[:40] or None


# Prompt hệ thống (không hiển thị cho người dùng). Câu chat có thể bằng tiếng Việt hoặc tiếng Anh.
SYSTEM = (
    "You analyse chat messages from users of a meal-planning app. Messages may be in Vietnamese or English. "
    "Return JSON matching the schema. intent=want_food when the user wants to eat/drink something; restrict when "
    "they want to fast, skip meals or eat extremely little; log_food ONLY when they clearly report something they "
    "ALREADY ate or drank (past markers like vừa/đã/mới/rồi/xong, just/had/ate — e.g. 'tôi vừa ăn 1 bát phở', 'I just "
    "had a banana'); a plan for a meal ('trưa nay ăn cơm tấm') is want_food, not log_food; dislike when they say they don't like / can't eat a food "
    "(taste preference); allergy when they mention being allergic to something; question when asking for "
    "information; other otherwise. "
    "mentions: list the food/drink names exactly as written in the message, in the user's language "
    "(e.g. 'gà', 'kem', 'trà sữa', 'chicken', 'ice cream'). Only fill quantity_value if the user states a number. "
    "slot: the meal the user refers to (snack for snacks/desserts). day: today/tomorrow only if stated. "
    "Never guess nutrition values."
) + DATA_NOT_INSTRUCTIONS


def validate_quantity(text: str):
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


# Cache kết quả LLM: khóa = văn bản chuẩn hóa + ngôn ngữ. KHÔNG cache câu có tín hiệu rối loạn ăn uống/dị ứng
# (luôn xử lý lại để ghi sự kiện an toàn và áp quy tắc mới nhất).
_cache = LRU(1000)


def parse(text: str, provider: LLMProvider | None, max_retries: int = 2,
          lang: str = "vi", now=None) -> tuple[ParsedIntent, str]:
    rules = rule_parse(text)
    cacheable = provider is not None and cacheable_text(text, rules)
    key = (" ".join(text.lower().split()), lang)
    if cacheable and (hit := _cache.get(key)) is not None:
        return past_check(hit.model_copy(deep=True), text, now), "llm"
    out, _ = call_structured(provider, SYSTEM, text[:1000], ParsedIntent, max_retries, validate=validate_quantity(text))
    if out is None:
        return rules, "rules"
    merge_rules(out, rules)
    if cacheable:
        _cache.put(key, out.model_copy(deep=True))
    return past_check(out, text, now), "llm"


def cacheable_text(text: str, rules: ParsedIntent) -> bool:
    """Câu có tín hiệu rối loạn ăn uống / nhịn ăn / dị ứng KHÔNG bao giờ được cache."""
    return rules.intent not in ("restrict", "allergy") and not detect_text_signals(text)


def merge_rules(out: ParsedIntent, rules: ParsedIntent) -> ParsedIntent:
    """Tín hiệu an toàn từ quy tắc luôn được giữ, dù LLM nói gì
    (dị ứng/nhịn ăn luôn thắng; không thích/đã ăn thắng khi LLM chỉ nói "muốn ăn"/"khác")."""
    if rules.intent in ("restrict", "allergy") or (
            rules.intent in ("dislike", "log_food") and out.intent in ("want_food", "other")):
        out.intent = rules.intent
    out.cheat_day = out.cheat_day or rules.cheat_day
    if out.intent == "dislike" and not out.mentions:
        out.dislike_object = rules.dislike_object
    out.past_day = rules.past_day
    return out


def past_check(out: ParsedIntent, text: str, now) -> ParsedIntent:
    """LLM nói "đã ăn" nhưng câu không có dấu hiệu quá khứ và bữa đó chưa qua ⇒ hiểu là "muốn ăn"."""
    if out.intent == "log_food" and not has_past_marker(text) and not slot_over(out.slot, now):
        out.intent = "want_food"
    return out
