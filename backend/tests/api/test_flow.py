"""Luồng chính end-to-end: đăng ký → hồ sơ → nhu cầu kèm nguồn → thực đơn 2/3 bữa ±5% → +/- → pantry → xóa dữ liệu."""

from datetime import date

from tests.conftest import BASE_PROFILE, register

DAY = date(2026, 10, 21)
MACROS = ("energy_kcal", "protein_g", "carb_g", "fat_g")


def _macros_within(plan, tol=0.05):
    devs = {d["code"]: d for d in plan["deviations"]}
    return all(abs(devs[c]["pct"]) <= tol + 1e-9 for c in MACROS)


def test_needs_have_references(client, auth):
    r = client.get("/api/needs", headers=auth)
    assert r.status_code == 200
    n = r.json()["needs"]
    codes = {t["code"] for t in n["targets"]}
    assert {"energy_kcal", "protein_g", "carb_g", "fat_g", "fiber_g", "iron_mg", "zinc_mg", "calcium_mg",
            "vitamin_d_ug"} <= codes
    for t in n["targets"]:
        assert t["reference"]["source"], t["code"]
    for t in n["targets"]:
        if t["code"] in ("iron_mg", "zinc_mg", "calcium_mg", "vitamin_d_ug"):
            assert "nữ, 30 tuổi" == t["reference"]["applies_to"]
    assert any(x["code"] == "DISCLAIMER" for x in r.json()["notices"])


def test_three_meals_within_tolerance(client, auth):
    r = client.post("/api/menu/generate", json={"start": DAY.isoformat(), "days": 1}, headers=auth)
    assert r.status_code == 200, r.text
    m = r.json()[0]
    slots = [x["slot"] for x in m["plan"]["meals"]]
    assert slots == ["breakfast", "lunch", "dinner"]
    assert _macros_within(m["plan"])
    assert any(n["code"] == "DISCLAIMER" for n in m["notices"])


def test_two_meals_for_low_activity(client):
    h = register(client, profile={**BASE_PROFILE, "activity_level": "sedentary"})
    m = client.post("/api/menu/generate", json={"start": DAY.isoformat()}, headers=h).json()[0]
    assert [x["slot"] for x in m["plan"]["meals"]] == ["lunch", "dinner"]
    assert _macros_within(m["plan"])


def test_meal_totals_computed_from_ingredients(client, auth, catalog):
    m = client.post("/api/menu/generate", json={"start": DAY.isoformat()}, headers=auth).json()[0]
    for meal in m["plan"]["meals"]:
        kcal = sum(catalog.food(i["food_code"]).nutrient("energy_kcal", i["grams"]) for i in meal["items"])
        assert abs(kcal - meal["totals"]["energy_kcal"]) < 1e-6


def test_delete_all_data(client, auth, engine):
    client.post("/api/menu/generate", json={"start": DAY.isoformat()}, headers=auth)
    client.post("/api/chat", json={"message": "tôi muốn ăn kem"}, headers=auth)
    assert client.post("/api/pantry", json={"day": DAY.isoformat(), "food_code": "egg", "grams": 100},
                       headers=auth).status_code == 201
    assert client.delete("/api/me", headers=auth).status_code == 204
    from sqlalchemy import func, select, text

    from app.db.session import Base

    with engine.connect() as c:
        assert c.execute(text("PRAGMA foreign_keys")).scalar() == 1  # do init_engine bật, không phải conftest
        for t in ("users", "health_profiles", "menu_days", "meals", "meal_items", "chat_messages", "chat_proposals",
                  "safety_events", "pantry_items", "refresh_tokens"):
            assert c.execute(text(f"select count(*) from {t}")).scalar() == 0, t
        # mọi cột tham chiếu users.id (user_id, owner_user_id, kể cả bảng thêm sau này) không còn dòng nào
        user_cols = [col for t in Base.metadata.sorted_tables for col in t.c
                     if any(fk.column.table.name == "users" for fk in col.foreign_keys)]
        assert len(user_cols) >= 5
        for col in user_cols:
            n = c.execute(select(func.count()).select_from(col.table).where(col.is_not(None))).scalar()
            assert n == 0, f"{col.table.name}.{col.name}"
    assert client.get("/api/profile", headers=auth).status_code == 401
