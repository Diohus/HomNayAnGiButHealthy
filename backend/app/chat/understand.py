"""N1: hiểu câu chat bằng MỘT lượt LLM (ý định + ánh xạ món vào catalog cùng lúc).

1. Ứng viên lấy từ n-gram 1–4 từ của cả câu (`text_candidates`, cùng bộ chấm điểm K1).
2. Schema gộp = các trường của ParsedIntent + `mentions: [{text, kind, food_code, dish_code, components,
   confidence, alternatives}]`; mã là enum đúng các ứng viên ⇒ không bịa mã. Hậu kiểm như K1 (`review`).
3. Quy tắc an toàn (dị ứng, nhịn ăn/rối loạn ăn uống, không thích, "đã ăn") áp SAU LLM như parser cũ.
4. Cache: khóa (câu chuẩn hóa, lang, phiên bản catalog); KHÔNG cache câu có tín hiệu ED/nhịn ăn/dị ứng.
Lượt gộp lỗi ⇒ trả None, bên gọi chạy đường 2 bước cũ (parse ⇒ resolve), cuối cùng là parser quy tắc.
"""

from types import SimpleNamespace

from pydantic import BaseModel, Field, create_model

from app.ai.providers import LLMProvider
from app.ai.service import call_structured
from app.chat import parser as P
from app.chat.schemas import ParsedIntent
from app.core.cache import LRU
from app.foods import resolve as RS
from app.foods.catalog import FoodCatalog
from app.foods.matching import normalize

cache = LRU(1000)

SYSTEM = (
    P.SYSTEM + " "
    "In the same answer, map every food/drink you list to the fixed catalog given below: for each one return text "
    "(verbatim from the message), kind=ingredient with food_code if it is one catalog ingredient; kind=dish with "
    "dish_code if it is one catalog dish (ALWAYS prefer an existing catalog dish over composite); kind=composite with "
    "components (catalog ingredients + estimated raw grams for ONE serving) if it is a mixed dish not in the catalog; "
    "kind=not_food if it is not food; kind=unknown if nothing in the catalog fits. Users may misspell, omit "
    "Vietnamese diacritics or use regional words (e.g. 'trái thơm' = pineapple). Use ONLY codes from the enums; "
    "never invent codes. confidence is 0-1; give up to 3 alternatives when unsure."
)


def build_model(food_codes: list[str], dish_codes: list[str]) -> type[BaseModel]:
    """Schema gộp: trường ý định của ParsedIntent + mentions có ánh xạ catalog (enum ứng viên)."""
    mention = RS.mention_model(food_codes, dish_codes, key="text")
    fields = {k: (f.annotation, f) for k, f in ParsedIntent.model_fields.items()
              if k not in ("mentions", "dislike_object", "past_day")}
    return create_model("ChatUnderstanding", **fields,
                        mentions=(list[mention], Field(max_length=5, description="Food/drink mentions + catalog match")))


def understand(text: str, provider: LLMProvider | None, catalog: FoodCatalog, lang: str = "vi", now=None,
               max_retries: int = 2) -> tuple[ParsedIntent, dict[str, RS.Resolution]] | None:
    """(ý định, mention → Resolution) hoặc None khi lượt gộp không dùng được (bên gọi chạy đường cũ)."""
    if provider is None:
        return None
    rules = P.rule_parse(text)
    cacheable = P.cacheable_text(text, rules)
    key = (" ".join(normalize(text).split()), lang, RS.catalog_version(catalog))
    if cacheable and (hit := cache.get(key)) is not None:
        parsed, res = hit
        return P.past_check(parsed.model_copy(deep=True), text, now), dict(res)
    foods, dishes = RS.text_candidates(text, catalog)
    model = build_model(foods, dishes)
    user = ("Catalog candidates:\n" + RS._catalog_lines(catalog, foods, dishes) + "\n\nMessage:\n" + text[:1000])
    out, _ = call_structured(provider, SYSTEM, user, model, max_retries, validate=P.validate_quantity(text))
    if out is None:
        return None
    parsed = ParsedIntent(intent=out.intent, mentions=[m.text.strip() for m in out.mentions if m.text.strip()],
                          quantity_value=out.quantity_value, quantity_unit=out.quantity_unit, slot=out.slot,
                          day=out.day, cheat_day=out.cheat_day)
    P.merge_rules(parsed, rules)
    fset, dset = set(foods), set(dishes)
    res: dict[str, RS.Resolution] = {}
    for m in out.mentions:
        t = m.text.strip()
        if t and t not in res:
            res[t] = RS.review(SimpleNamespace(**m.__dict__, mention=t), t, catalog, fset, dset)
    if cacheable:
        cache.put(key, (parsed.model_copy(deep=True), dict(res)))
    return P.past_check(parsed, text, now), res
