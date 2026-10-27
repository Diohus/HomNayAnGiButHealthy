"""Món / nguyên liệu không thích — ràng buộc MỀM của planner (khác dị ứng là ràng buộc cứng trong hồ sơ)."""

import uuid

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.core.i18n import Lang, name_of
from app.db import foods_repo
from app.db import models as M

KINDS = ("food", "dish", "text")
TEXT_MAX = 40  # kind="text": thứ chưa có trong catalog ("hành", "ngò") — planner bỏ qua, công thức tránh từ này


def dislikes(s: Session, user_id: uuid.UUID) -> tuple[set[str], set[str]]:
    rows = s.scalars(select(M.FoodPreference).where(M.FoodPreference.user_id == user_id)).all()
    return ({r.code for r in rows if r.kind == "food"}, {r.code for r in rows if r.kind == "dish"})


def text_dislikes(s: Session, user_id: uuid.UUID) -> list[str]:
    return list(s.scalars(select(M.FoodPreference.code).where(M.FoodPreference.user_id == user_id,
                                                              M.FoodPreference.kind == "text")))


def normalize_text(label: str) -> str:
    return " ".join(label.split()).lower()


def _lookup(s: Session, user_id: uuid.UUID, kind: str, code: str):
    if kind == "text":
        return code if 0 < len(code) <= TEXT_MAX else None
    if kind == "food":
        ing = foods_repo.visible_ingredient(s, user_id, code)
        return ing
    return foods_repo.global_catalog(s).dishes.get(code)


def list_dislikes(s: Session, user_id: uuid.UUID, lang: Lang = "vi") -> list[dict]:
    rows = s.scalars(select(M.FoodPreference).where(M.FoodPreference.user_id == user_id)
                     .order_by(M.FoodPreference.id)).all()
    out = []
    for r in rows:
        obj = _lookup(s, user_id, r.kind, r.code)
        name = r.code if r.kind == "text" else (name_of(obj, lang) if obj is not None else r.code)
        out.append({"id": r.id, "kind": r.kind, "code": r.code, "name": name})
    return out


def add_dislike(s: Session, user_id: uuid.UUID, kind: str, code: str) -> int:
    """Mã phải tồn tại trong catalog mà người dùng nhìn thấy (nguyên liệu chung hoặc của chính họ, món chung)."""
    if kind == "text":
        code = normalize_text(code)
        if not 0 < len(code) <= TEXT_MAX:
            raise AppError(422, "TEXT_TOO_LONG", params={"max": TEXT_MAX})
    if kind not in KINDS or _lookup(s, user_id, kind, code) is None:
        raise AppError(404, "FOOD_NOT_FOUND")
    row = s.scalar(select(M.FoodPreference).where(M.FoodPreference.user_id == user_id,
                                                  M.FoodPreference.kind == kind, M.FoodPreference.code == code))
    if row is None:
        row = M.FoodPreference(user_id=user_id, kind=kind, code=code)
        s.add(row)
        try:
            s.commit()
        except IntegrityError:  # thêm trùng đồng thời ⇒ coi như đã có
            s.rollback()
            row = s.scalar(select(M.FoodPreference).where(M.FoodPreference.user_id == user_id,
                                                          M.FoodPreference.kind == kind,
                                                          M.FoodPreference.code == code))
    return row.id


def delete_dislike(s: Session, user_id: uuid.UUID, pref_id: int) -> None:
    row = s.get(M.FoodPreference, pref_id)
    if row is None or row.user_id != user_id:
        raise AppError(404, "PREFERENCE_NOT_FOUND")
    s.delete(row)
    s.commit()
