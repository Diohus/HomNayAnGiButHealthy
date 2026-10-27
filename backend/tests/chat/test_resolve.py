"""Vòng 5 K1: hiểu món bằng LLM (giả lập) — enum động, hậu kiểm, clarify, món ghép, cache, fallback, dislike."""

import pytest
from pydantic import ValidationError

from app.chat.engine import handle
from app.chat.parser import rule_parse
from app.chat.schemas import ParsedIntent
from app.foods import resolve as RS
from tests.chat.conftest import ask

ALL_FIELDS = {"food_code": None, "dish_code": None, "components": [], "confidence": 0.9, "alternatives": []}


class FakeLLM:
    name = "fake"

    def __init__(self, results):
        self.results, self.calls, self.users = results, 0, []

    def complete_json(self, system, user, schema, schema_name):
        self.calls += 1
        self.users.append(user)
        r = self.results(user) if callable(self.results) else self.results
        return {"results": [{**ALL_FIELDS, **x} for x in r]}


@pytest.fixture(autouse=True)
def _clear_cache():
    RS.cache.clear()
    yield
    RS.cache.clear()


def parsed(mentions, intent="want_food", slot=None):
    return ParsedIntent(intent=intent, mentions=mentions, quantity_value=None, quantity_unit=None, slot=slot,
                        day=None, cheat_day=False)


def with_llm(ctx, fake, lang="vi"):
    ctx.resolve_fn = lambda ms: RS.resolve_mentions(fake, ms, ctx.catalog_full, lang)
    return ctx


# ---------- ứng viên ----------
@pytest.mark.parametrize(("mention", "code"), [
    ("ga ran", "fried_chicken"), ("trứg luộc", "egg"), ("bún bò huế", "rice_noodles"), ("fried chiken", "fried_chicken"),
    ("ca hoi", "salmon"),
])
def test_candidates_contain_expected(catalog, mention, code):
    foods, dishes = RS.candidates(mention, catalog)
    assert code in foods and len(foods) == RS.TOP_K_FOODS and len(dishes) == RS.TOP_K_DISHES


def test_schema_enum_only_candidates(catalog):
    model = RS.build_model(["egg", "salmon"], ["trung_hap"], 1)
    with pytest.raises(ValidationError):
        model.model_validate({"results": [{**ALL_FIELDS, "mention": "x", "kind": "ingredient",
                                           "food_code": "chicken_breast"}]})


# ---------- hậu kiểm + fallback ----------
def test_code_outside_enum_rejected_then_fallback(make_ctx):
    fake = FakeLLM([{"mention": "trứg luộc", "kind": "ingredient", "food_code": "unicorn_meat"}])
    ctx, _ = make_ctx()
    r = handle("tôi muốn ăn trứg luộc", parsed(["trứg luộc"]), with_llm(ctx, fake))
    assert fake.calls == 3  # retry giới hạn rồi bỏ
    assert r.kind == "need_label" and r.unknown_mentions == ["trứg luộc"]


def test_typo_resolved_to_ingredient(make_ctx):
    fake = FakeLLM([{"mention": "trứg luộc", "kind": "ingredient", "food_code": "egg", "confidence": 0.95}])
    ctx, _ = make_ctx()
    r = handle("tôi muốn ăn trứg luộc", parsed(["trứg luộc"]), with_llm(ctx, fake))
    assert r.kind == "proposal" and r.detected[0].food_code == "egg"


def test_dish_resolution_uses_that_dish(make_ctx):
    fake = FakeLLM([{"mention": "ca kho to", "kind": "dish", "dish_code": "ca_kho_to", "confidence": 0.9}])
    ctx, _ = make_ctx()
    r = handle("trua nay an ca kho to", parsed(["ca kho to"], slot="lunch"), with_llm(ctx, fake))
    lunch = next(m for m in r.proposals[0].plan.meals if m.slot == "lunch")
    assert lunch.dish_code == "ca_kho_to"


def test_low_confidence_asks_then_resolved(make_ctx):
    fake = FakeLLM([{"mention": "thịt", "kind": "ingredient", "food_code": "pork_tenderloin", "confidence": 0.4,
                     "alternatives": ["food:beef_lean", "food:chicken_breast"]}])
    ctx, _ = make_ctx()
    r = handle("tôi muốn ăn thịt", parsed(["thịt"]), with_llm(ctx, fake))
    assert r.kind == "clarify" and not r.proposals
    opts = r.clarify[0]["options"]
    assert r.clarify[0]["mention"] == "thịt" and [o["code"] for o in opts][:3] == [
        "food:pork_tenderloin", "food:beef_lean", "food:chicken_breast"]
    assert opts[0]["name"] == "Thăn heo"
    ctx.resolved = {"thịt": "food:beef_lean"}  # người dùng bấm nút
    r = handle("tôi muốn ăn thịt", parsed(["thịt"]), ctx)
    assert r.kind == "proposal" and r.detected[0].food_code == "beef_lean"
    ctx.resolved = {"thịt": "food:khong_ton_tai"}  # mã giả ⇒ bỏ qua
    assert handle("tôi muốn ăn thịt", parsed(["thịt"]), ctx).kind == "clarify"


def test_composite_ai_estimate_and_clamp(make_ctx):
    fake = FakeLLM([{"mention": "bún bò huế", "kind": "composite", "confidence": 0.85, "components": [
        {"food_code": "rice_noodles", "grams": 90}, {"food_code": "beef_lean", "grams": 900},
        {"food_code": "bean_sprouts", "grams": 1}]}])
    res = RS.resolve_mentions(fake, ["bún bò huế"], make_ctx()[0].catalog_full, "vi")
    r = res["bún bò huế"]
    assert r.kind == "composite" and dict(r.components) == {"rice_noodles": 90, "beef_lean": 400, "bean_sprouts": 30}
    assert set(r.warnings) == {"GRAMS_CLAMPED:beef_lean", "GRAMS_CLAMPED:bean_sprouts"}
    ctx, _ = make_ctx()
    out = handle("trưa nay ăn bún bò huế", parsed(["bún bò huế"], slot="lunch"), with_llm(ctx, fake))
    assert out.kind == "proposal", out.text
    lunch = next(m for m in out.proposals[0].plan.meals if m.slot == "lunch")
    assert {i.food_code: i.grams for i in lunch.items} == {"rice_noodles": 90, "beef_lean": 400, "bean_sprouts": 30}
    assert all(i.origin == "ai_estimate" and i.locked for i in lunch.items) and lunch.dish_code is None
    assert "AI ước tính" in out.text and "bún bò huế" in out.text


def test_composite_with_allergen_component_refused(make_ctx):
    fake = FakeLLM([{"mention": "canh chua cá lóc", "kind": "composite", "confidence": 0.9, "components": [
        {"food_code": "catfish", "grams": 150}, {"food_code": "tomato", "grams": 80}]}])
    ctx, _ = make_ctx(allergies=["fish"])
    r = handle("tôi muốn ăn canh chua cá lóc", parsed(["canh chua cá lóc"]), with_llm(ctx, fake))
    assert r.kind == "refusal" and not r.proposals
    assert "canh chua cá lóc" in r.text and "cá da trơn" in r.text and "dị ứng cá" in r.text


def test_cache_hit_skips_llm(make_ctx):
    fake = FakeLLM([{"mention": "trứg", "kind": "ingredient", "food_code": "egg"}])
    cat = make_ctx()[0].catalog_full
    RS.resolve_mentions(fake, ["trứg"], cat, "vi")
    RS.resolve_mentions(fake, ["  trứg "], cat, "vi")
    assert fake.calls == 1
    RS.resolve_mentions(fake, ["trứg"], cat, "en")  # khóa gồm ngôn ngữ
    assert fake.calls == 2


def test_cache_key_has_no_user_data():
    assert all("user" not in str(k) for k in RS.cache._d)


def test_llm_off_keeps_old_behaviour(make_ctx):
    ctx, _ = make_ctx()
    assert RS.resolve_mentions(None, ["trứg"], ctx.catalog_full, "vi") == {}
    r = handle("tôi muốn ăn trứg", parsed(["trứg"]), ctx)  # resolve_fn None
    assert r.kind == "need_label"


def test_not_food_stays_need_label(make_ctx):
    fake = FakeLLM([{"mention": "xà phòng", "kind": "not_food", "confidence": 0.95}])
    ctx, _ = make_ctx()
    r = handle("tôi muốn ăn xà phòng", parsed(["xà phòng"]), with_llm(ctx, fake))
    assert r.kind == "need_label" and r.unknown_mentions == ["xà phòng"]


# ---------- dislike / dị ứng (K3) ----------
@pytest.mark.parametrize(("text", "intent"), [
    ("tôi không ăn được hành", "dislike"), ("ghét rau mùi", "dislike"), ("I don't like fish", "dislike"),
    ("tôi bị dị ứng tôm", "allergy"), ("I'm allergic to peanuts", "allergy"),
])
def test_rule_intents(text, intent):
    assert rule_parse(text).intent == intent


def test_skipping_breakfast_is_not_a_dislike():
    assert rule_parse("tôi không ăn sáng").intent != "dislike"


def test_dislike_proposes_preference(make_ctx):
    ctx, _ = make_ctx()
    r = ask(ctx, "tôi không thích cá hồi")
    assert r.kind == "proposal" and len(r.proposals) == 1
    p = r.proposals[0]
    assert p.key == "preference" and p.plan is None and p.preference == {"kind": "food", "code": "salmon"}
    ctx.lang = "en"
    assert ask(ctx, "I don't like fish").proposals[0].preference["code"] == "catfish"


def test_dislike_unknown_food_saved_as_text(make_ctx):
    """L0b: "hành" chưa có trong catalog ⇒ đề xuất lưu dạng chữ (công thức sẽ tránh), không bịa mã."""
    ctx, _ = make_ctx()
    r = ask(ctx, "tôi không ăn được hành")  # parser quy tắc: tách cụm sau "không ăn được"
    assert r.kind == "proposal" and r.proposals[0].preference == {"kind": "text", "code": "hành"}
    assert "tránh hành" in r.proposals[0].label


def test_allergy_statement_never_proposes_food(make_ctx):
    ctx, _ = make_ctx()
    r = ask(ctx, "tôi bị dị ứng tôm")
    assert r.kind == "allergy_redirect" and not r.proposals and "Hồ sơ" in r.text


def test_quantity_words_not_sent_to_llm(make_ctx):
    fake = FakeLLM([])
    ctx, _ = make_ctx()
    r = handle("tôi muốn ăn 2 cây kem", parsed(["2 cây kem"]), with_llm(ctx, fake))
    assert fake.calls == 0 and r.detected[0].food_code == "ice_cream_vanilla"
    assert r.proposals[0].snacks[0]["grams"] == 2 * ctx.catalog.food("ice_cream_vanilla").portion.grams


def test_partial_resolved_to_same_ingredient_keeps_alias_match(make_ctx):
    fake = FakeLLM([{"mention": "cá hồi nướng", "kind": "ingredient", "food_code": "salmon"}])
    ctx, _ = make_ctx()
    r = handle("tối nay ăn cá hồi nướng", parsed(["cá hồi nướng"], slot="dinner"), with_llm(ctx, fake))
    assert fake.calls == 1 and [d.food_code for d in r.detected] == ["salmon"] and r.kind == "proposal"


# ---------- mô phỏng các câu PO sẽ chạy E2E (LLM giả lập) ----------
def test_po_sentences_do_not_break(make_ctx):
    def llm(user):
        if "trái thơm" in user:
            return [{"mention": "trái thơm", "kind": "unknown", "confidence": 0.9}]
        if "trứg luộc" in user:
            return [{"mention": "trứg luộc", "kind": "ingredient", "food_code": "egg"}]
        if "bún bò huế" in user:
            return [{"mention": "bún bò huế", "kind": "composite", "components": [
                {"food_code": "rice_noodles", "grams": 100}, {"food_code": "beef_lean", "grams": 100}]}]
        return []

    fake = FakeLLM(llm)
    cases = [
        ("toi muon an ga ran", [], "proposal"),  # khớp alias không dấu, không cần LLM
        ("trứg luộc", ["trứg luộc"], "proposal"),
        ("trưa nay ăn bún bò huế", ["bún bò huế"], "proposal"),
        ("cho tôi ít trái thơm", ["trái thơm"], "need_label"),
        ("tôi không ăn được hành", ["hành"], "proposal"),
        ("I don't like fish", ["fish"], "proposal"),
        ("tôi bị dị ứng tôm", ["tôm"], "allergy_redirect"),
    ]
    for text, mentions, kind in cases:
        ctx, _ = make_ctx()
        rp = rule_parse(text)
        p = parsed(mentions, intent=rp.intent if rp.intent in ("dislike", "allergy") else "want_food", slot=rp.slot)
        r = handle(text, p, with_llm(ctx, fake))
        assert r.kind == kind, (text, r.kind, r.text)
