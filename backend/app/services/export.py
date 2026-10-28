"""P2: "Tải dữ liệu của tôi" — toàn bộ dữ liệu của MỘT người dùng, đã giải mã, dạng JSON.

KHÔNG xuất: password hash, refresh token (kể cả hash), ID nội bộ của người khác. Sự kiện an toàn (rối loạn ăn
uống) chỉ xuất SỐ LƯỢNG theo loại. Mọi truy vấn lọc theo user_id.
"""

import uuid
from collections import Counter
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.crypto import get_cipher
from app.db import foods_repo
from app.db import models as M
from app.services import chat as CS
from app.services import preferences as PREF
from app.services import profile as P

SCHEMA_VERSION = 1


def _iso(v) -> str | None:
    return v.isoformat() if v is not None else None


def export(s: Session, user_id: uuid.UUID) -> dict:
    u = s.get(M.User, user_id)
    profile = P.load_profile(s, user_id)
    menus = []
    for md in s.scalars(select(M.MenuDay).where(M.MenuDay.user_id == user_id).order_by(M.MenuDay.day)):
        menus.append({"day": md.day.isoformat(), "version": md.version, "status": md.status, "meals": [
            {"slot": m.slot, "active": m.active, "dish_code": m.dish_code,
             "items": [{"food_code": i.ingredient_code, "grams": i.grams, "locked": i.locked, "origin": i.origin}
                       for i in m.items],
             "recipe": {"content": m.recipe.content, "source": m.recipe.source} if m.recipe else None}
            for m in md.meals]})
    intake = s.scalars(select(M.IntakeEntry).where(M.IntakeEntry.user_id == user_id)
                       .order_by(M.IntakeEntry.day, M.IntakeEntry.id)).all()
    pantry = s.scalars(select(M.PantryItem).where(M.PantryItem.user_id == user_id).order_by(M.PantryItem.day)).all()
    adjust = s.scalars(select(M.EnergyAdjustment).where(M.EnergyAdjustment.user_id == user_id)
                       .order_by(M.EnergyAdjustment.day)).all()
    safety = Counter(s.scalars(select(M.SafetyEvent.kind).where(M.SafetyEvent.user_id == user_id)))
    chat = CS.history(s, user_id, limit=100_000)  # đã giải mã; chỉ giữ 30 ngày (purge + commit)
    cipher = get_cipher()
    return {
        "schema_version": SCHEMA_VERSION,
        "exported_at": datetime.now(UTC).isoformat(),
        "account": {"email": u.email, "created_at": _iso(u.created_at)},
        "profile": profile.model_dump(mode="json") if profile else None,
        "health_limits": [{"condition": r.condition_code, "source": r.source, "confirmed_at": _iso(r.confirmed_at),
                           "limits": cipher.decrypt(r.encrypted_payload)} for r in P.limit_rows(s, user_id)],
        "dislikes": PREF.list_dislikes(s, user_id),
        "menus": menus,
        "intake": [{"day": r.day.isoformat(), "slot": r.slot, "food_code": r.food_code, "grams": r.grams,
                    "source": r.source, "created_at": _iso(r.created_at)} for r in intake],
        "pantry": [{"day": r.day.isoformat(), "food_code": r.ingredient_code, "grams": r.grams} for r in pantry],
        "energy_adjustments": [{"day": r.day.isoformat(), "delta_kcal": r.delta_kcal, "reason": r.reason,
                                "source_day": _iso(r.source_day)} for r in adjust],
        "chat_history": chat,
        "custom_foods": [f.model_dump(mode="json") for f in foods_repo.user_foods(s, user_id)],
        "safety_event_counts": dict(safety),
    }
