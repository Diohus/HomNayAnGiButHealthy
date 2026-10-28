"""Vòng 8 N1: một lượt LLM cho cả ý định + ánh xạ món (LLM giả lập)."""

from datetime import datetime

import pytest

from app.ai.providers import LLMError
from app.chat import parser as P
from app.chat import understand as U
from app.chat.engine import handle
from app.foods import resolve as RS

NOW = datetime(2026, 10, 21, 9, 0)
MENTION = {"food_code": None, "dish_code": None, "components": [], "confidence": 0.9, "alternatives": []}
INTENT = {"intent": "want_food", "quantity_value": None, "quantity_unit": None, "slot": None, "day": None,
          "cheat_day": False}


class FakeLLM:
    name = "fake"

    def __init__(self, out):
        self.out, self.calls, self.schemas = out, 0, []

    def complete_json(self, system, user, schema, schema_name):
        self.calls += 1
        self.schemas.append(schema_name)
        if isinstance(self.out, Exception):
            raise self.out
        o = self.out(user) if callable(self.out) else self.out
        return {**INTENT, **o, "mentions": [{**MENTION, **m} for m in o.get("mentions", [])]}


@pytest.fixture(autouse=True)
def _clear():
    for c in (U.cache, RS.cache, P._cache):
        c.clear()
    yield
    for c in (U.cache, RS.cache, P._cache):
        c.clear()


def test_ngram_candidates(catalog):
    foods, dishes = RS.text_candidates("toi muon an ga ran", catalog)
    assert "fried_chicken" in foods and len(dishes) == RS.TOP_K_DISHES
    foods, dishes = RS.text_candidates("trưa nay ăn bún bò huế", catalog)
    assert "bun_bo_hue" in dishes and {"fresh_rice_noodles", "beef_sirloin"} <= set(foods)  # + nguyên liệu chính
    assert "pineapple" in RS.text_candidates("cho tôi ít trái thơm", catalog)[0]


def test_single_call_intent_and_resolution(catalog):
    fake = FakeLLM({"mentions": [{"text": "ga ran", "kind": "ingredient", "food_code": "fried_chicken"}]})
    parsed, res = U.understand("toi muon an ga ran", fake, catalog, "vi", NOW)
    assert fake.calls == 1 and fake.schemas == ["ChatUnderstanding"]
    assert parsed.intent == "want_food" and parsed.mentions == ["ga ran"]
    assert res["ga ran"].kind == "ingredient" and res["ga ran"].food_code == "fried_chicken"


def test_invented_code_rejected_then_fallback_none(catalog):
    # mã ngoài enum ⇒ sai schema ở mọi lần thử ⇒ None (bên gọi chạy đường 2 bước cũ)
    fake = FakeLLM({"mentions": [{"text": "ga ran", "kind": "ingredient", "food_code": "unicorn"}]})
    assert U.understand("toi muon an ga ran", fake, catalog, "vi", NOW, max_retries=1) is None
    assert fake.calls == 2
    assert U.understand("toi muon an ga ran", FakeLLM(LLMError("timeout")), catalog, "vi", NOW, 0) is None


def test_quantity_must_be_in_text(catalog):
    fake = FakeLLM({"quantity_value": 3, "mentions": [{"text": "chuối", "kind": "ingredient", "food_code": "banana"}]})
    assert U.understand("tôi muốn ăn chuối", fake, catalog, "vi", NOW, max_retries=0) is None


def test_composite_clamped(catalog):
    fake = FakeLLM({"mentions": [{"text": "bánh canh bò", "kind": "composite", "components": [
        {"food_code": "fresh_rice_noodles", "grams": 200}, {"food_code": "beef_lean", "grams": 900}]}]})
    _, res = U.understand("trưa nay ăn bánh canh bò", fake, catalog, "vi", NOW)
    r = res["bánh canh bò"]
    assert r.kind == "composite" and dict(r.components)["beef_lean"] == 400 and "GRAMS_CLAMPED:beef_lean" in r.warnings


def test_safety_rules_override_llm(catalog):
    # LLM nói "muốn ăn" nhưng câu nói về dị ứng ⇒ quy tắc thắng; câu dị ứng/nhịn ăn KHÔNG được cache
    fake = FakeLLM({"mentions": [{"text": "tôm", "kind": "ingredient", "food_code": "shrimp"}]})
    parsed, _ = U.understand("tôi bị dị ứng tôm", fake, catalog, "vi", NOW)
    assert parsed.intent == "allergy"
    U.understand("tôi bị dị ứng tôm", fake, catalog, "vi", NOW)
    assert fake.calls == 2
    fake = FakeLLM({"intent": "want_food"})
    parsed, _ = U.understand("hôm nay tôi nhịn ăn cả ngày", fake, catalog, "vi", NOW)
    assert parsed.intent == "restrict"
    U.understand("hôm nay tôi nhịn ăn cả ngày", fake, catalog, "vi", NOW)
    assert fake.calls == 2


def test_cache_hit_and_past_check(catalog):
    fake = FakeLLM({"intent": "log_food", "slot": "lunch",
                    "mentions": [{"text": "cơm tấm", "kind": "dish", "dish_code": "com_tam_suon"}]})
    parsed, res = U.understand("Trưa nay ăn  cơm tấm", fake, catalog, "vi", datetime(2026, 10, 21, 8))
    assert parsed.intent == "want_food"  # chưa qua bữa trưa, không có dấu hiệu quá khứ
    parsed, res = U.understand("trưa nay ăn cơm tấm", fake, catalog, "vi", datetime(2026, 10, 21, 15))
    assert fake.calls == 1 and parsed.intent == "log_food" and res["cơm tấm"].dish_code == "com_tam_suon"
    U.understand("trưa nay ăn cơm tấm", fake, catalog, "en", NOW)
    assert fake.calls == 2  # khóa cache có ngôn ngữ


def test_engine_uses_preresolved(make_ctx, catalog):
    fake = FakeLLM({"mentions": [{"text": "trứg luộc", "kind": "ingredient", "food_code": "egg"}]})
    parsed, res = U.understand("trứg luộc", fake, catalog, "vi", NOW)
    ctx, _ = make_ctx()
    calls = []
    ctx.resolve_fn = lambda ms: calls.append(ms) or {m: res[m] for m in ms if m in res}
    r = handle("trứg luộc", parsed, ctx, "llm")
    assert r.kind == "proposal" and any(d.food_code == "egg" for d in r.detected)


def _single_pass_on(monkeypatch):
    from app.core.config import get_settings

    on = get_settings().model_copy(update={"chat_single_pass": True})
    monkeypatch.setattr("app.services.chat.get_settings", lambda: on)


def test_single_pass_off_by_default():
    from app.core.config import Settings

    assert Settings.model_fields["chat_single_pass"].default is False


def test_api_single_pass_and_fallback(client, auth, monkeypatch):
    _single_pass_on(monkeypatch)
    fake = FakeLLM({"mentions": [{"text": "ga ran", "kind": "ingredient", "food_code": "fried_chicken"}]})
    monkeypatch.setattr("app.services.chat.get_provider", lambda s: fake)
    r = client.post("/api/chat", json={"message": "toi muon an ga ran"}, headers=auth).json()
    assert fake.calls == 1 and r["parser"] == "llm"
    assert any(d["food_code"] == "fried_chicken" for d in r["detected"])
    # lượt gộp lỗi ⇒ đường 2 bước cũ ⇒ cuối cùng parser quy tắc (vẫn trả lời được)
    broken = FakeLLM(LLMError("timeout"))
    monkeypatch.setattr("app.services.chat.get_provider", lambda s: broken)
    r = client.post("/api/chat", json={"message": "tôi muốn ăn chuối"}, headers=auth).json()
    assert r["parser"] == "rules" and r["kind"] == "proposal"


def test_api_unknown_from_single_pass_retried_by_resolver(client, auth, monkeypatch):
    def out(user):
        if "Mentions:" in user:  # lượt resolver riêng (K1)
            return {"results": [{**MENTION, "mention": "trứg luộc", "kind": "ingredient", "food_code": "egg"}]}
        return {**INTENT, "mentions": [{**MENTION, "text": "trứg luộc", "kind": "unknown"}]}

    class Fake(FakeLLM):
        def complete_json(self, system, user, schema, schema_name):
            self.calls += 1
            return out(user)

    fake = Fake(None)
    _single_pass_on(monkeypatch)
    monkeypatch.setattr("app.services.chat.get_provider", lambda s: fake)
    r = client.post("/api/chat", json={"message": "trứg luộc"}, headers=auth).json()
    assert fake.calls == 2 and any(d["food_code"] == "egg" for d in r["detected"])
