"""Chatbot: lưu tin nhắn mã hóa (30 ngày), tạo đề xuất, áp dụng đề xuất khi người dùng xác nhận."""

import json
import logging
import time
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
from app.foods.resolve import resolve_mentions
from app.planner import LockedItem
from app.services import intake as IN
from app.services import menu as MS
from app.services import preferences as PREF
from app.services import profile as P

log = logging.getLogger(__name__)
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


def send(s: Session, user_id: uuid.UUID, text: str, now: datetime | None = None, lang: Lang = "vi",
         resolved: dict[str, str] | None = None) -> dict:
    """`resolved`: lựa chọn của người dùng sau câu hỏi lại (clarify) — mention → "food:x" | "dish:y"."""
    text = text.strip()
    if not 1 <= len(text) <= 1000:
        raise AppError(422, "MESSAGE_LENGTH")
    now = now or datetime.now()
    c = MS.Ctx(s, user_id)
    evs = P.events(s, user_id)
    settings = get_settings()
    provider = get_provider(settings)
    t0 = time.perf_counter()
    timing = {"parse": 0.0, "resolve": 0.0}
    parsed, parser_name = parse(text, provider, settings.llm_max_retries, lang)
    timing["parse"] = (time.perf_counter() - t0) * 1000

    def plan_fn(day, required, snacks, energy_override, min_meal_energy, extra=()):
        return c.solve(day, required=required, snacks=snacks, energy_override=energy_override,
                       min_meal_energy=min_meal_energy, extra_locked=list(extra))[0]

    def resolve_fn(mentions):  # K1: LLM chọn mã trong ứng viên; cache không chứa user_id/dị ứng
        t = time.perf_counter()
        try:
            return resolve_mentions(provider, mentions, c.full, lang, settings.llm_max_retries)
        finally:
            timing["resolve"] += (time.perf_counter() - t) * 1000

    ctx = ChatContext(
        now=now, slots=c.needs.meal_slots, allergies=list(c.profile.allergies), diets=list(c.profile.diets),
        catalog_full=c.full, catalog=c.catalog,
        energy_target=lambda d: MS.energy_target(s, user_id, c.needs, d), energy_floor=c.needs.energy_floor_kcal,
        plan_fn=plan_fn, mains_by_date=MS.mains_by_date(s, user_id, now.date()),
        snacks_by_date={d: snacks_on(s, user_id, d) for d in (now.date(), now.date() + timedelta(days=1))},
        safety_events=evs, ed_flagged=P.ed_status(s, user_id).flagged, lang=lang,
        resolve_fn=resolve_fn if provider is not None else None, resolved=dict(resolved or {}),
    )
    reply: ChatReply = handle(text, parsed, ctx, parser_name)
    log.debug("chat timing_ms total=%d parse=%d resolve=%d parser=%s kind=%s", (time.perf_counter() - t0) * 1000,
              timing["parse"], timing["resolve"], parser_name, reply.kind)  # không log nội dung
    for kind in reply.safety_events:
        P.record_event(s, user_id, kind)

    _purge(s, user_id)
    _save_msg(s, user_id, "user", {"text": text})
    out_props = []
    msg = _save_msg(s, user_id, "assistant", {"text": reply.text, "kind": reply.kind})
    # đề xuất "không thích" không gắn thực đơn ngày nào ⇒ base_version = 0, không kiểm tra lỗi thời
    for pr in reply.proposals:
        md = MS.get_day(s, user_id, pr.day)
        row = M.ChatProposal(user_id=user_id, message_id=msg.id,
                             encrypted_payload=get_cipher().encrypt(json.loads(pr.model_dump_json())),
                             base_version=md.version if md else 0, expires_at=datetime.now(UTC) + PROPOSAL_TTL)
        s.add(row)
        s.flush()
        out_props.append({"id": str(row.id), "key": pr.key, "label": pr.label, "day": pr.day.isoformat(),
                          "plan": json.loads(pr.plan.model_dump_json()) if pr.plan else None,
                          "preference": pr.preference,
                          "compensation": json.loads(pr.compensation.model_dump_json()) if pr.compensation else None})
    s.commit()
    return {"kind": reply.kind, "text": reply.text, "parser": reply.parser, "clarify": reply.clarify,
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
    if pr.key == "log" and pr.intake:  # ghi nhật ký đã ăn (kiểm tra lại dị ứng từng món)
        for e in pr.intake:
            IN.add_entry(s, user_id, pr.day, e["slot"], e["food_code"], e["grams"], e.get("source", "chat"),
                         commit=False)
        row.applied = True
        s.commit()
        return {"day": pr.day.isoformat(), "version": None, "regenerated_days": []}
    if pr.key == "rebalance":  # cân lại các bữa chưa ăn theo nhật ký
        row.applied = True
        plan = IN.rebalance(s, user_id, pr.day)
        return {"day": pr.day.isoformat(), "version": None, "regenerated_days": [], "warnings": plan.warnings}
    if pr.key == "preference" and pr.preference:  # thêm vào danh sách không thích (ràng buộc mềm)
        PREF.add_dislike(s, user_id, pr.preference["kind"], pr.preference["code"])
        row.applied = True
        s.commit()
        return {"day": None, "version": None, "regenerated_days": [], "preference": pr.preference}
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
