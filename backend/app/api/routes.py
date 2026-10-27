import uuid
from datetime import UTC, date, datetime, timedelta

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import delete, select, update
from sqlalchemy.orm import Session

from app.ai.providers import get_provider
from app.ai.recipes import generate_recipe
from app.api.deps import current_user
from app.core import ratelimit as RL
from app.core.config import get_settings
from app.core.errors import AppError
from app.core.i18n import Lang, get_lang, name_of
from app.core.ratelimit import client_ip, limiter
from app.core.security import (
    create_access_token,
    hash_password,
    hash_refresh_token,
    new_refresh_token,
    verify_password,
)
from app.db import models as M
from app.db.session import get_session
from app.guardrails.medical import menu_notices
from app.nutrition import ExpertLimits, HealthProfileIn
from app.nutrition.schemas import Condition
from app.services import chat as CS
from app.services import foods as FS
from app.services import menu as MS
from app.services import profile as P

router = APIRouter(prefix="/api")
LANG = Depends(get_lang)  # ngôn ngữ phản hồi theo Accept-Language (singleton để tránh B008)


# ---------------- auth ----------------
class Credentials(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class RefreshIn(BaseModel):
    refresh_token: str


REFRESH_REUSE_GRACE = timedelta(seconds=30)


def _aware(dt: datetime | None) -> datetime | None:
    """SQLite trả datetime không tz ⇒ coi là UTC."""
    return dt.replace(tzinfo=UTC) if dt is not None and dt.tzinfo is None else dt


def _issue(s: Session, uid: uuid.UUID) -> dict:
    raw, h = new_refresh_token()
    s.add(M.RefreshToken(user_id=uid, token_hash=h,
                         expires_at=datetime.now(UTC) + timedelta(days=get_settings().refresh_token_days)))
    s.commit()
    return {"access_token": create_access_token(uid), "refresh_token": raw, "token_type": "bearer"}


@router.post("/auth/register", status_code=201)
def register(body: Credentials, request: Request, s: Session = Depends(get_session)):
    limiter.hit(f"register:{client_ip(request)}", *RL.REGISTER)
    if s.scalar(select(M.User).where(M.User.email == body.email.lower())):
        raise AppError(409, "EMAIL_EXISTS")
    u = M.User(email=body.email.lower(), password_hash=hash_password(body.password))
    s.add(u)
    s.flush()
    return _issue(s, u.id)


@router.post("/auth/login")
def login(body: Credentials, request: Request, s: Session = Depends(get_session)):
    # Chống dò mật khẩu: chỉ đếm lần sai, theo (email, IP) và theo IP trên mọi email
    ip = client_ip(request)
    key, ip_key = f"login:{body.email.lower()}|{ip}", f"login-ip:{ip}"
    waits = [limiter.retry_after(key, *RL.LOGIN_FAILURES), limiter.retry_after(ip_key, *RL.LOGIN_FAILURES_IP)]
    if any(w is not None for w in waits):
        RL.raise_limited(max(w for w in waits if w is not None))
    u = s.scalar(select(M.User).where(M.User.email == body.email.lower()))
    if not u or not verify_password(body.password, u.password_hash):
        limiter.record(key)
        limiter.record(ip_key)
        raise AppError(401, "BAD_CREDENTIALS")
    limiter.clear(key)  # không xóa bộ đếm theo IP: một tài khoản đúng không được "rửa" lượt dò các email khác
    return _issue(s, u.id)


@router.post("/auth/refresh")
def refresh(body: RefreshIn, s: Session = Depends(get_session)):
    row = s.scalar(select(M.RefreshToken).where(M.RefreshToken.token_hash == hash_refresh_token(body.refresh_token)))
    exp = _aware(row.expires_at) if row else None
    now = datetime.now(UTC)
    if row and row.revoked:
        # Token đã xoay vòng/thu hồi bị dùng lại. Trong khoảng ân hạn sau khi xoay (các request song song của cùng
        # client) ⇒ chỉ từ chối. Ngoài khoảng đó hoặc token đã đăng xuất ⇒ coi như bị đánh cắp: thu hồi mọi phiên.
        rotated = _aware(row.rotated_at)
        if rotated is None or now - rotated > REFRESH_REUSE_GRACE:
            s.execute(update(M.RefreshToken).where(M.RefreshToken.user_id == row.user_id).values(revoked=True))
            s.commit()
    if not row or row.revoked or exp < now:
        raise AppError(401, "INVALID_REFRESH")
    row.revoked, row.rotated_at = True, now  # rotate
    return _issue(s, row.user_id)


@router.post("/auth/logout", status_code=204)
def logout(body: RefreshIn, s: Session = Depends(get_session)):
    row = s.scalar(select(M.RefreshToken).where(M.RefreshToken.token_hash == hash_refresh_token(body.refresh_token)))
    if row:
        row.revoked = True
        s.commit()


@router.delete("/me", status_code=204)
def delete_me(uid: uuid.UUID = Depends(current_user), s: Session = Depends(get_session)):
    """Xóa toàn bộ dữ liệu của người dùng (cascade mọi bảng)."""
    s.execute(delete(M.User).where(M.User.id == uid))
    s.commit()


# ---------------- hồ sơ & nhu cầu ----------------
@router.get("/profile")
def get_profile(uid: uuid.UUID = Depends(current_user), s: Session = Depends(get_session)):
    p = P.load_profile(s, uid)
    return {"profile": p.model_dump() if p else None}


@router.put("/profile")
def put_profile(body: HealthProfileIn, uid: uuid.UUID = Depends(current_user), s: Session = Depends(get_session),
                lang: Lang = LANG):
    P.save_profile(s, uid, body)
    return needs(uid, s, lang)


@router.get("/needs")
def needs(uid: uuid.UUID = Depends(current_user), s: Session = Depends(get_session), lang: Lang = LANG):
    p, n, blocked = P.current_needs(s, uid, lang)
    return {"needs": n.model_dump(), "notices": menu_notices(p.conditions, p.uses_insulin_or_glucose_meds, lang),
            "expert_confirmation_required": blocked}


class ExpertIn(BaseModel):
    condition: Condition
    confirmed_consulted_expert: bool
    limits: ExpertLimits


@router.post("/expert-confirmations", status_code=204)
def expert(body: ExpertIn, uid: uuid.UUID = Depends(current_user), s: Session = Depends(get_session)):
    if not body.confirmed_consulted_expert:
        raise AppError(422, "CONFIRMATION_REQUIRED")
    P.confirm_expert(s, uid, body.condition.value, body.limits)


# ---------------- nguyên liệu ----------------
@router.get("/foods")
def foods(uid: uuid.UUID = Depends(current_user), s: Session = Depends(get_session)):
    return FS.list_foods(s, uid)


@router.get("/dishes")
def dishes(uid: uuid.UUID = Depends(current_user), s: Session = Depends(get_session)):
    from app.db import foods_repo

    return [{"code": d.code, "name_vi": d.name_vi, "name_en": d.name_en or d.name_vi, "main": d.main, "slots": d.slots}
            for d in foods_repo.global_catalog(s).dishes.values()]


@router.post("/foods/custom", status_code=201)
def custom_food(body: FS.CustomFoodIn, uid: uuid.UUID = Depends(current_user), s: Session = Depends(get_session),
                lang: Lang = LANG):
    ing = FS.create_custom_food(s, uid, body, lang)
    return {"code": ing.code, "name_vi": ing.name_vi}


# ---------------- thực đơn ----------------
def _menu_out(s: Session, uid: uuid.UUID, day: date, lang: Lang = "vi") -> dict | None:
    md = MS.get_day(s, uid, day)
    if md is None:
        return None
    c = MS.Ctx(s, uid)
    plan = MS.to_plan(md, c.full, c.tol)
    recipes = {m.slot: {**m.recipe.content, "source": m.recipe.source} for m in md.meals if m.recipe and m.active}
    inactive = [m.slot for m in md.meals if not m.active]
    return {"day": day.isoformat(), "version": md.version, "plan": plan.model_dump(mode="json"),
            "targets": md.targets, "recipes": recipes, "inactive_meals": inactive,
            "energy_adjustment_kcal": MS.energy_delta(s, uid, day),
            "notices": menu_notices(c.profile.conditions, c.profile.uses_insulin_or_glucose_meds, lang)}


@router.get("/menu")
def get_menu(start: date, days: int = 1, uid: uuid.UUID = Depends(current_user), s: Session = Depends(get_session),
             lang: Lang = LANG):
    if not 1 <= days <= 14:
        raise AppError(422, "DAYS_RANGE", key="error.DAYS_RANGE.view")
    return [_menu_out(s, uid, start + timedelta(days=i), lang) for i in range(days)]


class GenerateIn(BaseModel):
    start: date
    days: int = Field(1, ge=1, le=7)


@router.post("/menu/generate")
def generate(body: GenerateIn, uid: uuid.UUID = Depends(current_user), s: Session = Depends(get_session),
             lang: Lang = LANG):
    MS.generate(s, uid, body.start, body.days)
    return [_menu_out(s, uid, body.start + timedelta(days=i), lang) for i in range(body.days)]


class AdjustIn(BaseModel):
    slot: str
    food_code: str
    delta_g: float


@router.post("/menu/{day}/adjust")
def adjust(day: date, body: AdjustIn, uid: uuid.UUID = Depends(current_user), s: Session = Depends(get_session),
           lang: Lang = LANG):
    MS.adjust(s, uid, day, body.slot, body.food_code, body.delta_g)
    return _menu_out(s, uid, day, lang)


class UnlockIn(BaseModel):
    slot: str
    food_code: str


@router.post("/menu/{day}/unlock")
def unlock(day: date, body: UnlockIn, uid: uuid.UUID = Depends(current_user), s: Session = Depends(get_session),
           lang: Lang = LANG):
    MS.unlock(s, uid, day, body.slot, body.food_code)
    return _menu_out(s, uid, day, lang)


@router.post("/menu/{day}/meals/{slot}/recipe")
def recipe(day: date, slot: str, uid: uuid.UUID = Depends(current_user), s: Session = Depends(get_session),
           lang: Lang = LANG):
    """AI đề xuất cách chế biến. Lỗi/timeout LLM ⇒ giữ công thức cũ nếu có, nếu không dùng template."""
    limiter.hit(f"recipe:{uid}", *RL.RECIPE)  # mỗi lần gọi LLM trả phí
    c = MS.Ctx(s, uid)
    md = MS.get_day(s, uid, day)
    meal = next((m for m in md.meals if m.slot == slot and m.active), None) if md else None
    if meal is None:
        raise AppError(404, "MEAL_NOT_FOUND")
    # Tên món/nguyên liệu theo ngôn ngữ: LLM viết công thức cùng ngôn ngữ (bộ lọc dị ứng kiểm tra cả vi + en)
    dish = name_of(c.full.dishes[meal.dish_code], lang) if meal.dish_code in c.full.dishes else None
    names = [name_of(c.full.food(i.ingredient_code), lang) for i in meal.items if i.ingredient_code in c.full.foods]
    settings = get_settings()
    r = generate_recipe(get_provider(settings), dish, names, c.profile.allergies, c.profile.diets,
                        low_sodium=Condition.hypertension in c.profile.conditions,
                        max_retries=settings.llm_max_retries, lang=lang)
    if r.source == "template" and meal.recipe is not None:
        return {**meal.recipe.content, "source": meal.recipe.source, "kept_previous": True}
    content = r.model_dump(exclude={"source"})
    if meal.recipe is None:
        meal.recipe = M.Recipe(content=content, source=r.source)
    else:
        # Cập nhật tại chỗ: thay object mới ⇒ SQLAlchemy INSERT trước DELETE (orphan) ⇒ vi phạm UNIQUE(meal_id)
        meal.recipe.content, meal.recipe.source, meal.recipe.created_at = content, r.source, datetime.now(UTC)
    s.commit()
    return r.model_dump()


# ---------------- nguyên liệu có sẵn ----------------
class PantryIn(BaseModel):
    day: date
    food_code: str
    grams: float


@router.get("/pantry")
def pantry(day: date, uid: uuid.UUID = Depends(current_user), s: Session = Depends(get_session)):
    rows = s.scalars(select(M.PantryItem).where(M.PantryItem.user_id == uid, M.PantryItem.day == day)).all()
    return [{"id": r.id, "food_code": r.ingredient_code, "grams": r.grams} for r in rows]


@router.post("/pantry", status_code=201)
def add_pantry(body: PantryIn, uid: uuid.UUID = Depends(current_user), s: Session = Depends(get_session)):
    return {"warnings": MS.add_pantry(s, uid, body.day, body.food_code, body.grams)}


@router.delete("/pantry/{item_id}", status_code=204)
def del_pantry(item_id: int, uid: uuid.UUID = Depends(current_user), s: Session = Depends(get_session)):
    s.execute(delete(M.PantryItem).where(M.PantryItem.id == item_id, M.PantryItem.user_id == uid))
    s.commit()


# ---------------- chatbot ----------------
class ChatIn(BaseModel):
    message: str


@router.post("/chat")
def chat(body: ChatIn, uid: uuid.UUID = Depends(current_user), s: Session = Depends(get_session), lang: Lang = LANG):
    limiter.hit(f"chat:{uid}", *RL.CHAT)  # mỗi tin nhắn có thể gọi LLM trả phí
    return CS.send(s, uid, body.message, lang=lang)


@router.get("/chat/history")
def chat_history(uid: uuid.UUID = Depends(current_user), s: Session = Depends(get_session)):
    return CS.history(s, uid)


@router.post("/chat/proposals/{proposal_id}/apply")
def apply(proposal_id: uuid.UUID, uid: uuid.UUID = Depends(current_user), s: Session = Depends(get_session),
          lang: Lang = LANG):
    res = CS.apply_proposal(s, uid, proposal_id)
    return {**res, "menu": _menu_out(s, uid, date.fromisoformat(res["day"]), lang)}
