"""Hồ sơ sức khỏe (mã hóa), xác nhận chuyên gia, sự kiện an toàn."""

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.crypto import get_cipher
from app.core.errors import AppError
from app.core.i18n import Lang
from app.db import models as M
from app.guardrails.eating_disorder import EDStatus, SafetyEventIn, assess
from app.guardrails.medical import pending_expert_confirmations
from app.nutrition import ExpertLimits, HealthProfileIn, LowEnergyNotAcknowledged, NutritionNeeds, compute_needs
from app.nutrition.schemas import SENSITIVE_CONDITIONS, Condition


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


def expert_limits(s: Session, user_id: uuid.UUID) -> tuple[ExpertLimits | None, set[str]]:
    rows = s.scalars(select(M.ExpertConfirmation).where(M.ExpertConfirmation.user_id == user_id)).all()
    if not rows:
        return None, set()
    merged: dict = {}
    for r in rows:  # nhiều bệnh nền ⇒ lấy giới hạn chặt nhất
        for k, v in get_cipher().decrypt(r.encrypted_limits).items():
            if v is not None:
                merged[k] = min(v, merged.get(k, v))
    return ExpertLimits(**merged), {r.condition_code for r in rows}


def save_profile(s: Session, user_id: uuid.UUID, p: HealthProfileIn) -> NutritionNeeds | None:
    """Lưu hồ sơ. Mục tiêu tự đặt dưới sàn: cần xác nhận; bị chặn nếu đã có tín hiệu rối loạn ăn uống."""
    limits, _ = expert_limits(s, user_id)
    needs = None
    try:
        needs = compute_needs(p, limits)
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
    """(hồ sơ, nhu cầu, bệnh nền nhạy cảm chưa được chuyên gia xác nhận)."""
    p = require_profile(s, user_id)
    limits, confirmed = expert_limits(s, user_id)
    needs = compute_needs(p, limits, lang=lang)
    return p, needs, pending_expert_confirmations(p.conditions, confirmed)


def confirm_expert(s: Session, user_id: uuid.UUID, condition: str, limits: ExpertLimits) -> None:
    if Condition(condition) not in SENSITIVE_CONDITIONS:
        raise AppError(422, "NOT_SENSITIVE_CONDITION")
    if not any(v is not None for v in limits.model_dump().values()):
        raise AppError(422, "LIMITS_REQUIRED")
    enc = get_cipher().encrypt(limits.model_dump())
    row = s.scalar(select(M.ExpertConfirmation).where(M.ExpertConfirmation.user_id == user_id,
                                                      M.ExpertConfirmation.condition_code == condition))
    if row:
        row.encrypted_limits, row.confirmed_at = enc, datetime.now(UTC)
    else:
        s.add(M.ExpertConfirmation(user_id=user_id, condition_code=condition, encrypted_limits=enc))
    s.commit()
