"""Vòng 2 (E3/E4): chatbot song ngữ — hiểu câu tiếng Anh, trả lời theo ngôn ngữ, lý do dị ứng đã dịch."""

import re

from app.foods.matching import find_foods
from tests.chat.conftest import ask
from tests.conftest import BASE_PROFILE, register

VI_CHARS = re.compile(r"[à-ỹÀ-Ỹđ]")


def en(ctx):
    ctx.lang = "en"
    return ctx


def test_english_aliases_match(catalog):
    def codes(t):
        return [m.food_code for m in find_foods(t, catalog)]

    assert codes("I want to eat chicken for dinner") == ["chicken_breast"]
    assert codes("fried chicken please") == ["fried_chicken"]  # cụm dài nhất thắng
    assert codes("some salmon and rice") == ["salmon", "white_rice"]
    assert codes("2 ice creams") == ["ice_cream_vanilla"]
    assert codes("an eggplant") == ["eggplant"]  # "egg" không khớp trong "eggplant"
    assert codes("brown rice") == ["brown_rice"]  # alias sinh từ name_en
    assert find_foods("2 ice creams", catalog)[0].qty_value == 2


def test_english_main_food_proposal(make_ctx):
    ctx, _ = make_ctx()
    r = ask(en(ctx), "I want to eat chicken for dinner")
    assert r.kind == "proposal" and r.proposals and r.detected[0].food_code == "chicken_breast"
    dinner = next(m for m in r.proposals[0].plan.meals if m.slot == "dinner")
    assert dinner.dish_code in ("ga_ap_chao", "ga_luoc_xe")
    assert "Here's a menu for today built around" in r.text and "Dinner" in r.text
    assert not VI_CHARS.search(r.text) and not VI_CHARS.search(r.proposals[0].label)


def test_english_restrict_and_distress_support(make_ctx):
    ctx, _ = make_ctx()
    r = ask(en(ctx), "I want to starve myself")
    assert r.kind == "support" and r.safety_events == ["RESTRICT_INTENT"] and not r.proposals
    assert "I don't suggest fasting" in r.text
    r = ask(ctx, "after dinner I make myself throw up")
    assert r.kind == "support" and r.safety_events == ["DISTRESS"]
    assert "pressure around eating" in r.text
    # "I'm starving" = rất đói, không phải tín hiệu nhịn ăn
    assert ask(ctx, "I'm starving, I want chicken").kind == "proposal"


def test_english_allergy_refusal_uses_translated_reason(make_ctx):
    ctx, _ = make_ctx(allergies=["fish"])
    r = ask(en(ctx), "I want salmon")
    assert r.kind == "refusal" and not r.proposals
    assert "fish allergy" in r.text and "allergy:" not in r.text and "(fish)" not in r.text


def test_vietnamese_refusal_no_raw_code(make_ctx):
    ctx, _ = make_ctx(allergies=["fish"])
    r = ask(ctx, "tôi muốn ăn cá hồi")
    assert "dị ứng cá" in r.text and "(fish)" not in r.text and "allergy:" not in r.text


def test_english_snack(make_ctx):
    ctx, _ = make_ctx()
    r = ask(en(ctx), "I want 2 ice creams")
    assert r.detected[0].role == "snack" and r.proposals
    assert "Vanilla ice cream" in r.text


def test_english_unknown_food_and_help(make_ctx):
    ctx, _ = make_ctx()
    r = ask(en(ctx), "I want to eat unicornburger")
    assert r.kind == "need_label" and "verified nutrition data" in r.text
    assert "You can tell me things like" in ask(ctx, "hello").text


def test_chat_api_follows_accept_language(client, auth):
    r = client.post("/api/chat", json={"message": "I want to eat chicken for dinner"},
                    headers={**auth, "Accept-Language": "en"})
    assert r.status_code == 200 and r.json()["kind"] == "proposal"
    assert r.json()["detected"][0]["name"] == "Chicken breast"
    assert r.json()["proposals"][0]["label"] == "Apply this menu"
    r = client.post("/api/chat", json={"message": "tôi muốn ăn gà"}, headers=auth)
    assert r.json()["proposals"][0]["label"] == "Áp dụng thực đơn này"
    # lịch sử giữ nguyên ngôn ngữ lúc gửi
    texts = [m["text"] for m in client.get("/api/chat/history", headers=auth).json() if m["role"] == "assistant"]
    assert texts[0].startswith("Here's a menu") and texts[1].startswith("Mình đề xuất")


def test_chat_api_allergy_refusal_english(client):
    h = register(client, email="fish@example.com", profile={**BASE_PROFILE, "allergies": ["fish"]})
    r = client.post("/api/chat", json={"message": "I want salmon"}, headers={**h, "Accept-Language": "en-GB"})
    assert r.json()["kind"] == "refusal" and "fish allergy" in r.json()["text"]


# ---------- Vòng 3 G2: tên hiển thị tiếng Anh ngắn, không viết thường sai ----------
def test_english_salmon_refusal_uses_display_name(client):
    h = register(client, email="fish2@example.com", profile={**BASE_PROFILE, "allergies": ["fish"]})
    r = client.post("/api/chat", json={"message": "I want salmon tonight"}, headers={**h, "Accept-Language": "en"})
    text = r.json()["text"]
    assert r.json()["kind"] == "refusal" and "salmon" in text.lower()
    assert "atlantic" not in text.lower() and ", farmed" not in text
    assert text == "I can't suggest Salmon because it conflicts with the fish allergy you declared."


def test_english_plan_text_has_no_usda_descriptions(make_ctx):
    ctx, _ = make_ctx()
    r = ask(en(ctx), "I want to eat chicken for dinner")
    assert "built around Chicken breast:" in r.text
    assert ", skinless" not in r.text and "whole egg" not in r.text.lower() and "unenriched" not in r.text


def test_vietnamese_names_still_lowercase_in_sentences(make_ctx):
    ctx, _ = make_ctx()
    assert "xoay quanh ức gà:" in ask(ctx, "tôi muốn ăn ức gà").text


def test_every_ingredient_has_display_en(catalog):
    assert len(catalog.foods) == 80
    for f in catalog.foods.values():
        assert f.display_en and "," not in f.display_en and not VI_CHARS.search(f.display_en), f.code


def test_foods_api_returns_display_en(client, auth):
    foods = {f["code"]: f for f in client.get("/api/foods", headers=auth).json()}
    assert foods["salmon"]["display_en"] == "Salmon" and foods["salmon"]["name_en"] == "Atlantic salmon, farmed"
