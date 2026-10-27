"""Chatbot: hiểu ý, phân loại món chính/phụ/ăn vặt, xây thực đơn quanh món chính, cheat day có giới hạn."""

from datetime import date, timedelta

from app.ai.providers import LLMError
from app.chat.parser import parse, rule_parse
from app.guardrails.eating_disorder import SafetyEventIn
from tests.chat.conftest import NOW, ask

TODAY = NOW.date()


def test_main_food_builds_menu_around_it(make_ctx):
    ctx, _ = make_ctx()
    r = ask(ctx, "tôi muốn ăn món gà")
    assert r.kind == "proposal" and r.detected[0].role == "main"
    plan = r.proposals[0].plan
    assert any(m.dish_code in ("ga_ap_chao", "ga_luoc_xe") for m in plan.meals)
    assert plan.status == "ok"


def test_main_with_slot(make_ctx):
    ctx, _ = make_ctx()
    r = ask(ctx, "tối nay ăn cá hồi")
    dinner = next(m for m in r.proposals[0].plan.meals if m.slot == "dinner")
    assert dinner.dish_code == "ca_hoi_ap_chao"


def test_side_and_main(make_ctx):
    ctx, _ = make_ctx()
    r = ask(ctx, "trưa nay ăn bò với bún")
    roles = {d.food_code: d.role for d in r.detected}
    assert roles == {"beef_lean": "main", "rice_noodles": "side"}
    lunch = next(m for m in r.proposals[0].plan.meals if m.slot == "lunch")
    assert lunch.dish_code in ("bo_xao", "bo_bam_sot_ca")
    assert any(i.food_code == "rice_noodles" for i in lunch.items)


def test_small_snack_absorbed_whole_day(make_ctx):
    ctx, n = make_ctx()
    r = ask(ctx, "tôi muốn ăn kem")
    assert r.detected[0].role == "snack" and r.proposals[0].key == "absorb"
    plan = r.proposals[0].plan
    assert plan.meals[-1].slot == "snack"
    assert abs(plan.totals["energy_kcal"] / n.get("energy_kcal").value - 1) <= 0.05


def test_big_snack_warns_with_options(make_ctx):
    ctx, n = make_ctx()
    r = ask(ctx, "tôi muốn ăn 8 miếng bánh kem")
    assert r.kind == "warning"
    keys = [p.key for p in r.proposals]
    assert "cheat_day" in keys
    cheat = next(p for p in r.proposals if p.key == "cheat_day")
    target = n.get("energy_kcal").value
    meals = sum(m.totals["energy_kcal"] for m in cheat.plan.meals if m.slot != "snack")
    assert meals >= 0.5 * target - 1  # không bỏ bữa chính
    comp = cheat.compensation
    assert len(comp.reductions) <= 3
    for red in comp.reductions:
        assert red.kcal <= 0.10 * target + 1e-6
        assert target - red.kcal >= n.energy_floor_kcal
    if "smaller_portion" in keys:
        sp = next(p for p in r.proposals if p.key == "smaller_portion")
        assert sp.plan.status == "ok" and sp.snacks[0]["grams"] < 512


def test_cheat_day_not_needed_when_fits(make_ctx):
    ctx, _ = make_ctx()
    r = ask(ctx, "hôm nay cheat day ăn 1 miếng pizza")
    assert r.proposals[0].key == "absorb" and "không cần cheat day" in r.text


def test_cheat_day_no_compensation_when_ed_risk(make_ctx):
    ctx, _ = make_ctx()
    ctx.safety_events = [SafetyEventIn(kind="COMPENSATION", at=NOW - timedelta(days=i)) for i in (1, 5)]
    r = ask(ctx, "tôi muốn ăn 8 miếng bánh kem")
    cheat = next(p for p in r.proposals if p.key == "cheat_day")
    assert cheat.compensation is None and "không bù" in cheat.label


def test_multiple_snacks_with_own_quantities(make_ctx):
    ctx, _ = make_ctx()
    r = ask(ctx, "2 cái bánh kem sô-cô-la và 1 lon coca")
    snacks = {s["food_code"]: s["grams"] for s in r.proposals[-1].snacks}
    assert snacks == {"chocolate_cake": 128, "cola": 370}


def test_allergy_refused(make_ctx):
    ctx, _ = make_ctx(allergies=["fish"])
    r = ask(ctx, "tôi muốn ăn cá hồi")
    assert r.kind == "refusal" and not r.proposals and "dị ứng" in r.text


def test_unknown_food_asks_for_label(make_ctx):
    ctx, _ = make_ctx()
    r = ask(ctx, "tôi muốn uống trà sữa")
    assert r.kind == "need_label" and r.unknown_mentions == ["trà sữa"] and not r.proposals


def test_rotation_respected(make_ctx):
    ctx, _ = make_ctx()
    ctx.mains_by_date = {TODAY - timedelta(days=i): {"ga_ap_chao", "ga_luoc_xe"} for i in (1, 2, 3)}
    r = ask(ctx, "tôi muốn ăn ức gà")
    assert all(m.dish_code not in ("ga_ap_chao", "ga_luoc_xe") for p in r.proposals for m in p.plan.meals)
    assert "3 ngày liên tiếp" in r.text


def test_distress_and_restrict(make_ctx):
    ctx, _ = make_ctx()
    assert ask(ctx, "ăn xong tôi tự gây nôn").safety_events == ["DISTRESS"]
    r = ask(ctx, "mai tôi muốn bỏ bữa")
    assert r.kind == "support" and r.safety_events == ["RESTRICT_INTENT"]


def test_rule_parser():
    p = rule_parse("ngày mai ăn vặt 200g kem lúc 3 giờ")
    assert (p.day, p.slot, p.quantity_value, p.quantity_unit) == ("tomorrow", "snack", 200, "g")
    assert rule_parse("ăn kem lúc 3 giờ chiều").quantity_value is None
    assert rule_parse("hôm nay cheat day").cheat_day


class FakeLLM:
    name = "fake"

    def __init__(self, out):
        self.out, self.calls = out, 0

    def complete_json(self, *a):
        self.calls += 1
        if isinstance(self.out, Exception):
            raise self.out
        return self.out


def test_llm_parser_cannot_invent_quantity():
    fake = FakeLLM({"intent": "want_food", "mentions": ["kem"], "quantity_value": 5, "quantity_unit": "portion",
                    "slot": None, "day": None, "cheat_day": False})
    p, src = parse("tôi muốn ăn kem", fake)
    assert src == "rules" and p.quantity_value is None and fake.calls == 3


def test_llm_parser_used_when_valid_and_restrict_kept():
    fake = FakeLLM({"intent": "want_food", "mentions": ["kem"], "quantity_value": None, "quantity_unit": None,
                    "slot": "snack", "day": None, "cheat_day": False})
    p, src = parse("tôi muốn ăn kem", fake)
    assert src == "llm" and p.slot == "snack"
    p, _ = parse("tôi muốn nhịn ăn, chỉ ăn kem", fake)
    assert p.intent == "restrict"


def test_llm_parser_timeout_falls_back():
    p, src = parse("tôi muốn ăn gà", FakeLLM(LLMError("timeout")))
    assert src == "rules" and p.intent == "want_food"


# ---- qua API: đề xuất → xác nhận → áp dụng ----
def test_apply_proposal_and_compensation(client, auth):
    from tests.conftest import register  # noqa: F401

    r = client.post("/api/chat", json={"message": "tôi muốn ăn 8 miếng bánh kem"}, headers=auth).json()
    cheat = next(p for p in r["proposals"] if p["key"] == "cheat_day")
    out = client.post(f"/api/chat/proposals/{cheat['id']}/apply", headers=auth)
    assert out.status_code == 200, out.text
    menu = out.json()["menu"]
    assert any(m["slot"] == "snack" for m in menu["plan"]["meals"])
    day = date.fromisoformat(out.json()["day"])
    nxt = client.get(f"/api/menu?start={day + timedelta(days=1)}", headers=auth)
    assert nxt.status_code == 200
    # đề xuất không dùng lại được
    assert client.post(f"/api/chat/proposals/{cheat['id']}/apply", headers=auth).status_code == 409
    hist = client.get("/api/chat/history", headers=auth).json()
    assert [h["role"] for h in hist] == ["user", "assistant"]


def test_stale_proposal_rejected(client, auth):
    r = client.post("/api/chat", json={"message": "tôi muốn ăn kem"}, headers=auth).json()
    pid = r["proposals"][0]["id"]
    client.post("/api/menu/generate", json={"start": r["proposals"][0]["day"]}, headers=auth)
    out = client.post(f"/api/chat/proposals/{pid}/apply", headers=auth)
    assert out.status_code == 409 and out.json()["code"] == "STALE_PROPOSAL"


def test_chat_messages_encrypted(client, auth, engine):
    client.post("/api/chat", json={"message": "tôi muốn ăn kem"}, headers=auth)
    from sqlalchemy import text

    with engine.connect() as c:
        blobs = c.execute(text("select encrypted_content from chat_messages")).scalars().all()
    assert blobs and all("kem".encode() not in b for b in blobs)
