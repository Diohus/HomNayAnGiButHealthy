"""Vòng 6 (cần fixture make_ctx của tests/chat): chat log_food, L0a alias liền kề ⇒ món ghép.
Vòng 7: "phở bò" đã là món trong catalog ⇒ dùng "cơm gà" (2 alias liền kề, chưa có món)."""

from app.chat.engine import handle
from app.foods import resolve as RS
from tests.chat.conftest import ask
from tests.chat.test_resolve import FakeLLM, parsed, with_llm


def test_chat_log_food_rules(make_ctx):
    ctx, _ = make_ctx()
    r = ask(ctx, "tôi vừa ăn 2 quả chuối")
    assert r.kind == "proposal" and [p.key for p in r.proposals] == ["log", "rebalance"]
    entry = r.proposals[0].intake[0]
    assert entry["food_code"] == "banana" and entry["source"] == "chat" and entry["slot"] == "breakfast"  # 9h sáng
    assert entry["grams"] > 0 and r.proposals[1].plan is None


def test_chat_log_composite_and_allergy(make_ctx):
    fake = FakeLLM([{"mention": "cơm gà", "kind": "composite", "components": [
        {"food_code": "white_rice", "grams": 100}, {"food_code": "chicken_breast", "grams": 80}]}])
    ctx, _ = make_ctx()
    p = parsed(["cơm gà"], intent="log_food")
    r = handle("tôi vừa ăn 1 đĩa cơm gà", p, with_llm(ctx, fake))
    assert {e["source"] for e in r.proposals[0].intake} == {"ai_estimate"}
    ctx, _ = make_ctx(allergies=["shellfish"])
    r = ask(ctx, "tôi vừa ăn tôm")
    assert r.kind == "refusal" and not r.proposals


def test_adjacent_aliases_sent_to_llm(make_ctx):
    fake = FakeLLM([{"mention": "cơm gà", "kind": "composite", "components": [
        {"food_code": "white_rice", "grams": 100}, {"food_code": "chicken_breast", "grams": 100}]}])
    ctx, _ = make_ctx()
    r = handle("tối nay ăn cơm gà nha", parsed(["cơm gà"], slot="dinner"), with_llm(ctx, fake))
    assert fake.calls == 1 and r.kind == "proposal"
    dinner = next(m for m in r.proposals[0].plan.meals if m.slot == "dinner")
    assert all(i.origin == "ai_estimate" for i in dinner.items)


def test_adjacent_aliases_llm_returns_ingredient_keeps_old(make_ctx):
    RS.cache.clear()
    fake = FakeLLM([{"mention": "cơm gà", "kind": "ingredient", "food_code": "chicken_breast"}])
    ctx, _ = make_ctx()
    r = handle("tối nay ăn cơm gà", parsed(["cơm gà"], slot="dinner"), with_llm(ctx, fake))
    assert {d.food_code for d in r.detected} == {"white_rice", "chicken_breast"}
