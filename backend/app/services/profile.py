"""Hồ sơ sức khỏe (mã hóa), giới hạn sức khỏe do người dùng cung cấp, sự kiện an toàn."""

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.crypto import get_cipher
from app.core.errors import AppError
from app.core.i18n import Lang, Msg
from app.db import models as M
from app.guardrails.eating_disorder import EDStatus, SafetyEventIn, assess
from app.guardrails.medical import conditions_without_limits, sensitive_conditions
from app.nutrition import HealthLimits, HealthProfileIn, LowEnergyNotAcknowledged, NutritionNeeds, compute_needs

LIMIT_SOURCES = ("manual", "document")


def load_profile(s: Session, user_id: uuid.UUID) -> HealthProfileIn | None:
    row = s.get(M.HealthProfile, user_id)
    return HealthProfileIn.model_validate(get_cipher().decrypt(row.encrypted_payload)) if row else None


def require_profile(s: Session, user_id: uuid.UUID) -> HealthProfileIn:
    p = load_profile(s, user_id)
    if p is None:
        raise AppError(409, "PROFILE_REQUIRED")
    return p


def record_event(s: Session, user_id: uuid.UUID, kind: str) -> None:
    s.add(M.SafetyEvent(user_id=user_id, kind=kind, at=datetime.now(UTC)))


def events(s: Session, user_id: uuid.UUID) -> list[SafetyEventIn]:
    since = datetime.now(UTC) - timedelta(days=30)
    rows = s.scalars(select(M.SafetyEvent).where(M.SafetyEvent.user_id == user_id, M.SafetyEvent.at >= since)).all()
    return [SafetyEventIn(kind=r.kind, at=r.at if r.at.tzinfo else r.at.replace(tzinfo=UTC)) for r in rows]


def ed_status(s: Session, user_id: uuid.UUID) -> EDStatus:
    return assess(events(s, user_id), datetime.now(UTC))


# ---------------- giới hạn sức khỏe ----------------
def limit_rows(s: Session, user_id: uuid.UUID) -> list[M.HealthLimit]:
    return list(s.scalars(select(M.HealthLimit).where(M.HealthLimit.user_id == user_id).order_by(M.HealthLimit.id)))


def merged_limits(s: Session, user_id: uuid.UUID) -> tuple[HealthLimits | None, dict[str, str], set]:
    """(giới hạn gộp — lấy chặt nhất mỗi chỉ số, nguồn của từng chỉ số, tập condition đã có giới hạn)."""
    rows = limit_rows(s, user_id)
    if not rows:
        return None, {}, set()
    merged: dict[str, float] = {}
    sources: dict[str, str] = {}
    for r in rows:
        for k, v in get_cipher().decrypt(r.encrypted_payload).items():
            if v is not None and (k not in merged or v < merged[k]):
                merged[k], sources[k] = v, r.source
    return HealthLimits(**merged), sources, {r.condition_code for r in rows}


def list_limits(s: Session, user_id: uuid.UUID) -> list[dict]:
    cipher = get_cipher()
    return [{"id": r.id, "condition": r.condition_code, "source": r.source, "confirmed_at": r.confirmed_at.isoformat(),
             "limits": HealthLimits(**cipher.decrypt(r.encrypted_payload)).model_dump()} for r in limit_rows(s, user_id)]


def upsert_limits(s: Session, user_id: uuid.UUID, condition: str | None, limits: HealthLimits, source: str) -> int:
    if not any(v is not None for v in limits.model_dump().values()):
        raise AppError(422, "LIMITS_REQUIRED")
    enc = get_cipher().encrypt(limits.model_dump())
    cond = M.HealthLimit.condition_code.is_(None) if condition is None else M.HealthLimit.condition_code == condition
    row = s.scalar(select(M.HealthLimit).where(M.HealthLimit.user_id == user_id, cond))
    if row:
        row.encrypted_payload, row.source, row.confirmed_at = enc, source, datetime.now(UTC)
    else:
        row = M.HealthLimit(user_id=user_id, condition_code=condition, encrypted_payload=enc, source=source)
        s.add(row)
    s.commit()
    return row.id


def delete_limit(s: Session, user_id: uuid.UUID, limit_id: int) -> None:
    row = s.get(M.HealthLimit, limit_id)
    if row is None or row.user_id != user_id:
        raise AppError(404, "LIMIT_NOT_FOUND")
    s.delete(row)
    s.commit()


# ---------------- hồ sơ & nhu cầu ----------------
def save_profile(s: Session, user_id: uuid.UUID, p: HealthProfileIn) -> NutritionNeeds | None:
    """Lưu hồ sơ. Bệnh nền nhạy cảm: cần xác nhận tự quản lý. Mục tiêu tự đặt dưới sàn: cần xác nhận;
    bị chặn nếu đã có tín hiệu rối loạn ăn uống."""
    if (sens := sensitive_conditions(p.conditions)) and not p.acknowledge_self_managed:
        raise AppError(409, "SELF_MANAGED_ACK_REQUIRED", params={"conditions": [Msg(f"condition.{c}") for c in sens]},
                       conditions=sens)
    limits, sources, _ = merged_limits(s, user_id)
    needs = None
    try:
        needs = compute_needs(p, limits, limit_sources=sources)
    except LowEnergyNotAcknowledged as e:
        record_event(s, user_id, "LOW_TARGET_ATTEMPT")
        s.commit()
        raise AppError(409, "LOW_ENERGY_ACK_REQUIRED",
                       params={"requested_kcal": round(e.requested), "floor_kcal": round(e.floor / 10) * 10},
                       floor_kcal=round(e.floor)) from e
    if "LOW_ENERGY_ACKNOWLEDGED" in needs.warnings:
        record_event(s, user_id, "LOW_TARGET_ATTEMPT")
        if ed_status(s, user_id).flagged:
            s.commit()
            raise AppError(409, "ED_SUPPORT")
    payload = get_cipher().encrypt(p.model_dump(mode="json"))
    row = s.get(M.HealthProfile, user_id)
    if row:
        row.encrypted_payload, row.version = payload, row.version + 1
    else:
        s.add(M.HealthProfile(user_id=user_id, encrypted_payload=payload))
    s.commit()
    return needs


def current_needs(s: Session, user_id: uuid.UUID,
                  lang: Lang = "vi") -> tuple[HealthProfileIn, NutritionNeeds, list[str]]:
    """(hồ sơ, nhu cầu, bệnh nền nhạy cảm CHƯA có giới hạn do người dùng cung cấp — chỉ để hiện notice)."""
    p = require_profile(s, user_id)
    limits, sources, covered = merged_limits(s, user_id)
    needs = compute_needs(p, limits, lang=lang, limit_sources=sources)
    return p, needs, conditions_without_limits(p.conditions, covered)
