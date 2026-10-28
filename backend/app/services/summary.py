"""P1: tổng quan 7 ngày — mục tiêu, kế hoạch, đã ăn; trung bình; chất hay thiếu kèm gợi ý thực phẩm.

Chỉ tính các ngày CÓ ghi nhật ký (`basis="eaten"`); không ngày nào ghi ⇒ tính theo thực đơn (`basis="planned"`).
Số liệu trả về chưa làm tròn: giao diện làm tròn (format.ts) để không hiển thị độ chính xác giả.
"""

import uuid
from datetime import date, timedelta

from sqlalchemy.orm import Session

from app.core.i18n import Lang, name_of
from app.services import intake as IN
from app.services import menu as MS

DAYS = 7
MACROS = ["energy_kcal", "protein_g", "carb_g", "fat_g", "fiber_g"]
WATCH = ["fiber_g", "calcium_mg", "iron_mg", "zinc_mg", "vitamin_d_ug"]  # chất hay thiếu
CODES = MACROS + WATCH[1:]
LOW_SHARE = 0.8  # dưới 80 % mục tiêu
LOW_MIN_DAYS = 4  # ở ≥ 4/7 ngày
ENERGY_BAND = 0.10  # năng lượng "đạt" trong ±10 %
N_SUGGEST = 3


def _pick(totals: dict | None) -> dict | None:
    return None if totals is None else {c: float(totals.get(c) or 0.0) for c in CODES}


def suggest(c: MS.Ctx, code: str, lang: Lang) -> list[dict]:
    """Thực phẩm giàu chất `code` (theo khẩu phần tối đa): bỏ đồ ăn vặt, đồ tự nhập, gia vị không xếp vào bữa,
    món không thích; catalog đã lọc dị ứng/chế độ ăn."""
    ranked = sorted((f for f in c.catalog.foods.values()
                     if f.category != "snack" and not f.user_provided and f.slots and f.code not in c.disliked_foods
                     and (f.per_100g.get(code) or 0) > 0),
                    key=lambda f: (-f.nutrient(code, f.max_g), f.code))
    return [{"food_code": f.code, "name": name_of(f, lang)} for f in ranked[:N_SUGGEST]]


def week(s: Session, user_id: uuid.UUID, end: date, lang: Lang = "vi") -> dict:
    c = MS.Ctx(s, user_id, lang)
    days = []
    for i in range(DAYS - 1, -1, -1):
        d = end - timedelta(days=i)
        targets = {t.code: t.value for t in MS.targets_for(s, user_id, c.needs, d)}
        md = MS.get_day(s, user_id, d)
        logged = bool(IN.entries(s, user_id, d))
        days.append({
            "day": d.isoformat(),
            "target": {k: targets[k] for k in CODES if k in targets},
            "planned": _pick(MS.to_plan(md, c.full, c.tol).totals) if md is not None else None,
            "eaten": _pick(IN.summary(s, user_id, d, c.full)["totals"]) if logged else None,
            "logged": logged,
        })
    basis = "eaten" if any(x["logged"] for x in days) else "planned"
    used = [(x, x[basis]) for x in days if x[basis] is not None]
    avg = {k: sum(v[k] for _, v in used) / len(used) for k in CODES} if used else {}
    energy_ok = sum(1 for x, v in used if x["target"].get("energy_kcal")
                    and abs(v["energy_kcal"] - x["target"]["energy_kcal"]) <= ENERGY_BAND * x["target"]["energy_kcal"])
    low = []
    for k in WATCH:
        n = sum(1 for x, v in used if x["target"].get(k) and v[k] < LOW_SHARE * x["target"][k])
        if n >= LOW_MIN_DAYS:
            low.append({"nutrient": k, "days_low": n, "suggestions": suggest(c, k, lang)})
    return {"end": end.isoformat(), "basis": basis, "days": days, "days_counted": len(used), "average": avg,
            "energy_within_days": energy_ok, "low_nutrients": low}
