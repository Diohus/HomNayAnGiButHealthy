"""Chatbot: lưu tin nhắn mã hóa (30 ngày), tạo đề xuất, áp dụng đề xuất khi người dùng xác nhận."""

import json
import uuid
from datetime import UTC, date, datetime, timedelta

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.ai.providers import get_provider
from app.chat.engine import ChatContext, handle
from app.chat.parser import parse
from app.chat.schemas import ChatReply, Proposal
from app.core.config import get_settings
from app.core.crypto import get_cipher
from app.core.errors import AppError
from app.core.i18n import Lang
from app.db import models as M
from app.planner import LockedItem
from app.services import menu as MS
from app.services import profile as P

RETENTION = timedelta(days=30)
PROPOSAL_TTL = timedelta(hours=1)


def _purge(s: Session, user_id: uuid.UUID) -> None:
    cutoff = datetime.now(UTC) - RETENTION
    s.execute(delete(M.ChatProposal).where(M.ChatProposal.user_id == user_id, M.ChatProposal.created_at < cutoff))
    s.execute(delete(M.ChatMessage).where(M.ChatMessage.user_id == user_id, M.ChatMessage.created_at < cutoff))


def _save_msg(s: Session, user_id: uuid.UUID, role: str, content: dict) -> M.ChatMessage:
    m = M.ChatMessage(user_id=user_id, role=role, encrypted_content=get_cipher().encrypt(content))
    s.add(m)
    s.flush()
    return m


def snacks_on(s: Session, user_id: uuid.UUID, day: date) -> list[LockedItem]:
    md = MS.get_day(s, user_id, day)
    if md is None:
        return []
    return [LockedItem(food_code=i.ingredient_code, grams=i.grams, slot="snack", origin="snack")
            for m in md.meals if m.slot == "snack" for i in m.items]


def send(s: Session, user_id: uuid.UUID, text: str, now: datetime | None = None, lang: Lang = "vi") -> dict:
    text = text.strip()
    if not 1 <= len(text) <= 1000:
        raise AppError(422, "MESSAGE_LENGTH")
    now = now or datetime.now()
    c = MS.Ctx(s, user_id)
    evs = P.events(s, user_id)
    settings = get_settings()
    parsed, parser_name = parse(text, get_provider(settings), settings.llm_max_retries)

    def plan_fn(day, required, snacks, energy_override, min_meal_energy):
        return c.solve(day, required=required, snacks=snacks, energy_override=energy_override,
                       min_meal_energy=min_meal_energy)[0]

    ctx = ChatContext(
        now=now, slots=c.needs.meal_slots, allergies=list(c.profile.allergies), diets=list(c.profile.diets),
        catalog_full=c.full, catalog=c.catalog,
        energy_target=lambda d: MS.energy_target(s, user_id, c.needs, d), energy_floor=c.needs.energy_floor_kcal,
        plan_fn=plan_fn, mains_by_date=MS.mains_by_date(s, user_id, now.date()),
        snacks_by_date={d: snacks_on(s, user_id, d) for d in (now.date(), now.date() + timedelta(days=1))},
        blocked_conditions=c.blocked, safety_events=evs, ed_flagged=P.ed_status(s, user_id).flagged, lang=lang,
    )
    reply: ChatReply = handle(text, parsed, ctx, parser_name)
    for kind in reply.safety_events:
        P.record_event(s, user_id, kind)

    _purge(s, user_id)
    _save_msg(s, user_id, "user", {"text": text})
    out_props = []
    msg = _save_msg(s, user_id, "assistant", {"text": reply.text, "kind": reply.kind})
    for pr in reply.proposals:
        md = MS.get_day(s, user_id, pr.day)
        row = M.ChatProposal(user_id=user_id, message_id=msg.id,
                             encrypted_payload=get_cipher().encrypt(json.loads(pr.model_dump_json())),
                             base_version=md.version if md else 0, expires_at=datetime.now(UTC) + PROPOSAL_TTL)
        s.add(row)
        s.flush()
        out_props.append({"id": str(row.id), "key": pr.key, "label": pr.label, "day": pr.day.isoformat(),
                          "plan": json.loads(pr.plan.model_dump_json()),
                          "compensation": json.loads(pr.compensation.model_dump_json()) if pr.compensation else None})
    s.commit()
    return {"kind": reply.kind, "text": reply.text, "parser": reply.parser,
            "detected": [d.model_dump() for d in reply.detected], "unknown_mentions": reply.unknown_mentions,
            "proposals": out_props}


def history(s: Session, user_id: uuid.UUID, limit: int = 50) -> list[dict]:
    _purge(s, user_id)
    s.commit()
    rows = s.scalars(select(M.ChatMessage).where(M.ChatMessage.user_id == user_id)
                     .order_by(M.ChatMessage.id.desc()).limit(limit)).all()
    cipher = get_cipher()
    return [{"id": r.id, "role": r.role, "at": r.created_at.isoformat(), **cipher.decrypt(r.encrypted_content)}
            for r in reversed(rows)]


def apply_proposal(s: Session, user_id: uuid.UUID, proposal_id: uuid.UUID) -> dict:
    row = s.get(M.ChatProposal, proposal_id)
    if row is None or row.user_id != user_id:
        raise AppError(404, "PROPOSAL_NOT_FOUND")
    if row.applied:
        raise AppError(409, "PROPOSAL_APPLIED")
    exp = row.expires_at if row.expires_at.tzinfo else row.expires_at.replace(tzinfo=UTC)
    if exp < datetime.now(UTC):
        raise AppError(409, "PROPOSAL_EXPIRED")
    pr = Proposal.model_validate(get_cipher().decrypt(row.encrypted_payload))
    md = MS.get_day(s, user_id, pr.day)
    if (md.version if md else 0) != row.base_version:
        raise AppError(409, "STALE_PROPOSAL")

    if pr.compensation and pr.compensation.reductions:
        if P.ed_status(s, user_id).flagged:
            raise AppError(409, "ED_SUPPORT")

    saved = MS.apply_plan(s, user_id, pr.plan)
    regenerated = []
    if pr.compensation:
        for r in pr.compensation.reductions:
            s.add(M.EnergyAdjustment(user_id=user_id, day=r.day, delta_kcal=-r.kcal, reason="cheat_day_compensation",
                                     source_day=pr.day))
        if pr.records_compensation_event:
            P.record_event(s, user_id, "COMPENSATION")
        s.flush()
        c = MS.Ctx(s, user_id)
        for r in pr.compensation.reductions:  # thực đơn đã có của các ngày bù được cân bằng lại theo mục tiêu mới
            if MS.get_day(s, user_id, r.day) is not None:
                plan, targets = c.solve(r.day, keep_structure=True)
                MS.save_plan(s, user_id, plan, targets)
                regenerated.append(r.day.isoformat())
    row.applied = True
    s.commit()
    return {"day": pr.day.isoformat(), "version": saved.version, "regenerated_days": regenerated}
