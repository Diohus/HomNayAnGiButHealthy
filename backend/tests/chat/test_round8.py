"""Vòng 8: N0a món gọi đích danh xếp được, N0b không đề xuất thực đơn hỏng, N0c "muốn ăn" vs "đã ăn",
N0d ghi nhật ký món kèm phần ăn kèm (ước tính)."""

from datetime import datetime

from app.chat import parser as P
from app.chat.engine import handle
from app.chat.parser import has_past_marker, parse, rule_parse, slot_over
from app.planner import DayPlan
from tests.chat.conftest import ask
from tests.chat.test_chat import FakeLLM


def _meal(r, dish):
    return next((m for m in r.proposals[0].plan.meals if m.dish_code == dish), None)


# ---------- N0a ----------
def test_bun_cha_unaccented_schedulable(make_ctx):
    for hour in (4, 9):
        ctx, _ = make_ctx()
        ctx.now = datetime(2026, 10, 21, hour, 0)
        r = ask(ctx, "toi muon an bun cha")
        assert r.kind == "proposal", (hour, r.text)
        assert r.proposals[0].plan.status != "conflict" and _meal(r, "bun_cha") is not None


# ---------- N0b ----------
def test_unusable_plan_gives_info_not_proposal(make_ctx):
    ctx, _ = make_ctx()
    real = ctx.plan_fn

    def broken(*a, **kw):
        p = real(*a, **kw)
        return DayPlan(**{**p.model_dump(), "status": "conflict", "conflicts": ["X"]})

    ctx.plan_fn = broken
    r = ask(ctx, "trưa nay ăn phở bò")
    assert r.kind == "info" and not r.proposals
    assert "phở bò" in r.text.lower() and "bữa khác hoặc ngày khác" in r.text


def test_unusable_plan_info_en(make_ctx):
    ctx, _ = make_ctx()
    ctx.lang = "en"
    real = ctx.plan_fn
    ctx.plan_fn = lambda *a, **kw: DayPlan(**{**real(*a, **kw).model_dump(), "meals": []})
    r = ask(ctx, "I want pho for lunch")
    assert r.kind == "info" and not r.proposals


# ---------- N0c ----------
def test_past_marker_and_slot_over():
    assert not has_past_marker("trưa nay ăn cơm tấm")
    assert has_past_marker("trưa nay ăn cơm tấm rồi") and has_past_marker("tôi vừa ăn phở")
    assert has_past_marker("I just had pho")
    assert not slot_over("lunch", datetime(2026, 10, 21, 8)) and slot_over("lunch", datetime(2026, 10, 21, 14))
    assert not slot_over("dinner", datetime(2026, 10, 21, 20, 59)) and not slot_over(None, datetime(2026, 10, 21, 22))


def test_rules_want_vs_log():
    assert rule_parse("trưa nay ăn cơm tấm").intent == "want_food"
    assert rule_parse("trưa nay ăn cơm tấm rồi").intent == "log_food"
    p = rule_parse("tối qua ăn phở")
    assert p.intent == "log_food" and p.past_day


def test_llm_log_food_without_marker_becomes_want():
    P._cache.clear()
    out = {"intent": "log_food", "mentions": ["cơm tấm"], "quantity_value": None, "quantity_unit": None,
           "slot": "lunch", "day": None, "cheat_day": False}
    p, src = parse("trưa nay ăn cơm tấm", FakeLLM(out), now=datetime(2026, 10, 21, 8))
    assert src == "llm" and p.intent == "want_food"
    # cùng câu (trúng cache) nhưng đã qua bữa trưa ⇒ giữ "đã ăn"
    p, _ = parse("trưa nay ăn cơm tấm", FakeLLM(out), now=datetime(2026, 10, 21, 15))
    assert p.intent == "log_food"
    P._cache.clear()


def test_chat_want_vs_log_flow(make_ctx):
    ctx, _ = make_ctx()
    ctx.now = datetime(2026, 10, 21, 8)
    r = ask(ctx, "trưa nay ăn cơm tấm")
    assert r.kind == "proposal" and r.proposals[0].key != "log"
    assert _meal(r, "com_tam_suon").slot == "lunch"
    r = ask(ctx, "trưa nay ăn cơm tấm rồi")
    assert r.kind == "proposal" and r.proposals[0].key == "log"


def test_log_yesterday_is_info(make_ctx):
    ctx, _ = make_ctx()
    r = ask(ctx, "tối qua ăn phở")
    assert r.kind == "info" and not r.proposals


# ---------- N0d ----------
def test_log_dish_includes_sides_as_estimate(make_ctx):
    ctx, _ = make_ctx()
    r = ask(ctx, "trưa nay ăn cơm tấm rồi")
    items = {e["food_code"]: e for e in r.proposals[0].intake}
    assert {"white_rice", "cucumber"} <= set(items) and "pork_ribs" in items
    assert items["cucumber"]["grams"] == 30 and all(e["source"] == "estimate" for e in items.values())
    assert "(ước tính)" in r.text


def test_seed_log_sides_valid(catalog):
    for d in catalog.dishes.values():
        for s in d.log_sides:
            f = catalog.food(s["food_code"])
            assert 0 < s["grams"] <= f.max_g, (d.code, s)
            assert s["food_code"] not in d.main, d.code


def test_handle_keeps_parser_name(make_ctx):
    ctx, _ = make_ctx()
    r = handle("toi muon an bun cha", rule_parse("toi muon an bun cha"), ctx, "rules")
    assert r.parser == "rules"
