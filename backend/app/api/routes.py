import uuid
from datetime import UTC, date, datetime, timedelta
from typing import Literal

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import delete, select, update
from sqlalchemy.orm import Session

from app.ai.providers import get_provider
from app.api.deps import current_user
from app.core import ratelimit as RL
from app.core.config import get_settings
from app.core.errors import AppError
from app.core.i18n import Lang, get_lang
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
from app.nutrition import HealthLimits, HealthProfileIn
from app.nutrition.schemas import Condition
from app.services import chat as CS
from app.services import export as EX
from app.services import foods as FS
from app.services import intake as IN
from app.services import limits_extract as LX
from app.services import meal_photo as PH
from app.services import menu as MS
from app.services import preferences as PREF
from app.services import profile as P
from app.services import shopping as SH
from app.services import summary as SUM

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


class PasswordIn(BaseModel):
    password: str = Field(min_length=1, max_length=200)


@router.post("/me/export")
def export_me(body: PasswordIn, uid: uuid.UUID = Depends(current_user), s: Session = Depends(get_session)):
    """Tải toàn bộ dữ liệu của tôi (JSON). Phải nhập lại mật khẩu; không chứa hash mật khẩu/refresh token."""
    limiter.hit(f"export:{uid}", *RL.EXPORT)
    u = s.get(M.User, uid)
    if u is None or not verify_password(body.password, u.password_hash):
        raise AppError(401, "BAD_PASSWORD")
    data = EX.export(s, uid)
    name = f"homnayangi-data-{datetime.now(UTC).date().isoformat()}.json"
    return JSONResponse(data, headers={"Content-Disposition": f'attachment; filename="{name}"',
                                       "Cache-Control": "no-store"})


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
    p, n, no_limits = P.current_needs(s, uid, lang)
    return {"needs": n.model_dump(),
            "notices": menu_notices(p.conditions, p.uses_insulin_or_glucose_meds, lang, no_limits),
            "conditions_without_limits": no_limits}


# ---------------- giới hạn sức khỏe do người dùng cung cấp ----------------
class HealthLimitIn(BaseModel):
    condition: Condition | None = None  # None = áp dụng chung
    limits: HealthLimits
    source: Literal["manual", "document"] = "manual"


@router.get("/health-limits")
def get_health_limits(uid: uuid.UUID = Depends(current_user), s: Session = Depends(get_session)):
    return P.list_limits(s, uid)


@router.put("/health-limits")
def put_health_limits(body: HealthLimitIn, uid: uuid.UUID = Depends(current_user),
                      s: Session = Depends(get_session)):
    lid = P.upsert_limits(s, uid, body.condition.value if body.condition else None, body.limits, body.source)
    return next(x for x in P.list_limits(s, uid) if x["id"] == lid)


@router.delete("/health-limits/{limit_id}", status_code=204)
def delete_health_limit(limit_id: int, uid: uuid.UUID = Depends(current_user), s: Session = Depends(get_session)):
    P.delete_limit(s, uid, limit_id)


_FILE = File(None)
_TEXT = Form(None)
_CONSENT = Form(False)


@router.post("/health-limits/extract")
def extract_health_limits(file: UploadFile | None = _FILE, text: str | None = _TEXT, consent_ai_processing: bool = _CONSENT,
                          uid: uuid.UUID = Depends(current_user), lang: Lang = LANG):
    """Đọc ảnh/văn bản chỉ định của bác sĩ bằng LLM ⇒ BẢN NHÁP (không lưu gì). Người dùng duyệt rồi PUT /health-limits."""
    if not consent_ai_processing:
        raise AppError(422, "AI_CONSENT_REQUIRED")
    image = file.file.read(LX.MAX_IMAGE_BYTES + 1) if file is not None else None
    text = (text or "").strip() or None
    if (image is None) == (text is None):  # đúng MỘT nguồn: ảnh hoặc văn bản
        raise AppError(422, "EXTRACT_INPUT_REQUIRED")
    if text is not None and len(text) > LX.MAX_TEXT_CHARS:
        raise AppError(422, "TEXT_TOO_LONG", params={"max": LX.MAX_TEXT_CHARS})
    # kiểm tra + bỏ metadata ảnh trước khi tính lượt (ảnh hỏng không tốn lượt); ảnh chỉ nằm trong bộ nhớ
    image_b64 = LX.prepare_image(image) if image is not None else None
    limiter.hit(f"extract:{uid}", *RL.EXTRACT)  # mỗi lần gọi LLM vision trả phí
    settings = get_settings()
    return LX.extract(get_provider(settings), text=text, image_b64=image_b64, lang=lang,
                      max_retries=settings.llm_max_retries)


# ---------------- nguyên liệu ----------------
@router.get("/foods")
def foods(uid: uuid.UUID = Depends(current_user), s: Session = Depends(get_session)):
    return FS.list_foods(s, uid)


@router.get("/dishes")
def dishes(uid: uuid.UUID = Depends(current_user), s: Session = Depends(get_session)):
    return FS.list_dishes(s)


@router.post("/foods/custom", status_code=201)
def custom_food(body: FS.CustomFoodIn, uid: uuid.UUID = Depends(current_user), s: Session = Depends(get_session),
                lang: Lang = LANG):
    ing = FS.create_custom_food(s, uid, body, lang)
    return {"code": ing.code, "name_vi": ing.name_vi}


# ---------------- thực đơn ----------------
def _menus_out(s: Session, uid: uuid.UUID, days: list[date], lang: Lang = "vi", c: MS.Ctx | None = None) -> list:
    """Thực đơn nhiều ngày; `Ctx` (giải mã hồ sơ, lọc catalog) dựng MỘT lần, chỉ khi có ít nhất một ngày có thực đơn."""
    out = []
    for day in days:
        md = MS.get_day(s, uid, day)
        if md is not None:
            c = c or MS.Ctx(s, uid)
        out.append(_day_out(s, uid, md, lang, c) if md is not None else None)
    return out


def _menu_out(s: Session, uid: uuid.UUID, day: date, lang: Lang = "vi", c: MS.Ctx | None = None) -> dict | None:
    return _menus_out(s, uid, [day], lang, c)[0]


def _day_out(s: Session, uid: uuid.UUID, md: M.MenuDay, lang: Lang, c: MS.Ctx) -> dict:
    day = md.day
    plan = MS.to_plan(md, c.full, c.tol)
    recipes = {m.slot: {**m.recipe.content, "source": m.recipe.source} for m in md.meals if m.recipe and m.active}
    inactive = [m.slot for m in md.meals if not m.active]
    intake = IN.summary(s, uid, day, c.full)
    return {"day": day.isoformat(), "version": md.version, "plan": plan.model_dump(mode="json"),
            "targets": md.targets, "recipes": recipes, "inactive_meals": inactive,
            "intake": {"entries": intake["entries"], "totals": intake["totals"]},
            "eaten_slots": intake["eaten_slots"],
            "energy_adjustment_kcal": MS.energy_delta(s, uid, day),
            "notices": menu_notices(c.profile.conditions, c.profile.uses_insulin_or_glucose_meds, lang, c.no_limits)}


@router.get("/menu")
def get_menu(start: date, days: int = 1, uid: uuid.UUID = Depends(current_user), s: Session = Depends(get_session),
             lang: Lang = LANG):
    if not 1 <= days <= 14:
        raise AppError(422, "DAYS_RANGE", key="error.DAYS_RANGE.view")
    return _menus_out(s, uid, [start + timedelta(days=i) for i in range(days)], lang)


class GenerateIn(BaseModel):
    start: date
    days: int = Field(1, ge=1, le=7)


@router.post("/menu/generate")
def generate(body: GenerateIn, uid: uuid.UUID = Depends(current_user), s: Session = Depends(get_session),
             lang: Lang = LANG):
    c = MS.Ctx(s, uid)
    MS.generate(s, uid, body.start, body.days, c)
    return _menus_out(s, uid, [body.start + timedelta(days=i) for i in range(body.days)], lang, c)


class AdjustIn(BaseModel):
    slot: IN.Slot
    food_code: str
    delta_g: float


@router.post("/menu/{day}/adjust")
def adjust(day: date, body: AdjustIn, uid: uuid.UUID = Depends(current_user), s: Session = Depends(get_session),
           lang: Lang = LANG):
    limiter.hit(f"adjust:{uid}", *RL.ADJUST)  # mỗi lần chạy solver
    c = MS.Ctx(s, uid)
    MS.adjust(s, uid, day, body.slot, body.food_code, body.delta_g, c)
    return _menu_out(s, uid, day, lang, c)


class UnlockIn(BaseModel):
    slot: IN.Slot
    food_code: str


@router.post("/menu/{day}/unlock")
def unlock(day: date, body: UnlockIn, uid: uuid.UUID = Depends(current_user), s: Session = Depends(get_session),
           lang: Lang = LANG):
    limiter.hit(f"adjust:{uid}", *RL.ADJUST)  # mỗi lần chạy solver (chung hạn mức với +/−)
    c = MS.Ctx(s, uid)
    MS.unlock(s, uid, day, body.slot, body.food_code, c)
    return _menu_out(s, uid, day, lang, c)


# ---------------- nhật ký "đã ăn" ----------------
class EatenIn(BaseModel):
    eaten: bool


@router.post("/menu/{day}/meals/{slot}/eaten")
def eaten(day: date, slot: IN.Slot, body: EatenIn, uid: uuid.UUID = Depends(current_user),
          s: Session = Depends(get_session), lang: Lang = LANG):
    IN.mark_eaten(s, uid, day, slot, body.eaten)
    return _menu_out(s, uid, day, lang)


@router.get("/summary/week")
def summary_week(end: date, uid: uuid.UUID = Depends(current_user), s: Session = Depends(get_session),
                 lang: Lang = LANG):
    """7 ngày kết thúc ở `end`: mục tiêu / kế hoạch / đã ăn mỗi ngày, trung bình, chất hay thiếu kèm gợi ý."""
    return SUM.week(s, uid, end, lang)


_PHOTO_FILE = File(...)
_PHOTO_DAY = Form(...)
_PHOTO_SLOT = Form(None)


@router.post("/intake/photo")
def intake_photo(file: UploadFile = _PHOTO_FILE, day: date = _PHOTO_DAY,
                 slot: IN.Slot | None = _PHOTO_SLOT,
                 consent_ai_processing: bool = _CONSENT, uid: uuid.UUID = Depends(current_user),
                 s: Session = Depends(get_session), lang: Lang = LANG):
    """Ảnh bữa ăn ⇒ BẢN NHÁP nhật ký (không lưu ảnh, không ghi DB). Người dùng sửa rồi POST /intake/batch."""
    if not consent_ai_processing:
        raise AppError(422, "AI_CONSENT_REQUIRED")
    image_b64 = LX.prepare_image(file.file.read(LX.MAX_IMAGE_BYTES + 1))  # ảnh hỏng không tốn lượt
    limiter.hit(f"photo:{uid}", *RL.PHOTO)
    settings = get_settings()
    draft = PH.analyze(s, uid, get_provider(settings), image_b64, lang, settings.llm_max_retries)
    return {**draft, "day": day.isoformat(), "slot": slot or PH.guess_slot(datetime.now())}


class BatchEntry(BaseModel):
    slot: IN.Slot
    food_code: str = Field(min_length=1, max_length=64)
    grams: float
    source: Literal["ai_estimate", "manual"] = "manual"  # "chat" chỉ ghi từ service (áp dụng đề xuất chat)


class BatchIn(BaseModel):
    day: date
    entries: list[BatchEntry]


@router.post("/intake/batch", status_code=201)
def add_intake_batch(body: BatchIn, uid: uuid.UUID = Depends(current_user), s: Session = Depends(get_session)):
    return {"ids": IN.add_entries(s, uid, body.day, [e.model_dump() for e in body.entries])}


@router.delete("/intake/{entry_id}", status_code=204)
def delete_intake(entry_id: int, uid: uuid.UUID = Depends(current_user), s: Session = Depends(get_session)):
    IN.delete_entry(s, uid, entry_id)


@router.post("/menu/{day}/rebalance")
def rebalance(day: date, uid: uuid.UUID = Depends(current_user), s: Session = Depends(get_session),
              lang: Lang = LANG):
    """Cân lại các bữa CHƯA ăn theo nhật ký thực tế (giữ sàn mỗi bữa, tôn trọng guardrail rối loạn ăn uống)."""
    limiter.hit(f"swap:{uid}", *RL.SWAP)  # cùng hạn mức với đổi bữa (đều chạy solver)
    c = MS.Ctx(s, uid)
    IN.rebalance(s, uid, day, c)
    return _menu_out(s, uid, day, lang, c)


# ---------------- danh sách đi chợ ----------------
@router.get("/shopping-list")
def shopping_list(start: date, days: int = 1, servings: int = 1, uid: uuid.UUID = Depends(current_user),
                  s: Session = Depends(get_session), lang: Lang = LANG):
    return SH.shopping_list(s, uid, start, days, servings, lang)


@router.post("/menu/{day}/meals/{slot}/swap")
def swap(day: date, slot: IN.Slot, uid: uuid.UUID = Depends(current_user), s: Session = Depends(get_session),
         lang: Lang = LANG):
    """Đổi một bữa: sinh lại bữa đó, giữ nguyên các bữa khác."""
    limiter.hit(f"swap:{uid}", *RL.SWAP)  # mỗi lần chạy solver
    c = MS.Ctx(s, uid)
    MS.swap(s, uid, day, slot, c)
    return _menu_out(s, uid, day, lang, c)


# ---------------- món / nguyên liệu không thích ----------------
class DislikeIn(BaseModel):
    kind: Literal["food", "dish", "text"]  # text: thứ chưa có trong catalog (≤ 40 ký tự)
    code: str = Field(min_length=1, max_length=64)


@router.get("/preferences/dislikes")
def get_dislikes(uid: uuid.UUID = Depends(current_user), s: Session = Depends(get_session), lang: Lang = LANG):
    return PREF.list_dislikes(s, uid, lang)


@router.post("/preferences/dislikes", status_code=201)
def add_dislike(body: DislikeIn, uid: uuid.UUID = Depends(current_user), s: Session = Depends(get_session),
                lang: Lang = LANG):
    pid = PREF.add_dislike(s, uid, body.kind, body.code)
    return next(x for x in PREF.list_dislikes(s, uid, lang) if x["id"] == pid)


@router.delete("/preferences/dislikes/{pref_id}", status_code=204)
def delete_dislike(pref_id: int, uid: uuid.UUID = Depends(current_user), s: Session = Depends(get_session)):
    PREF.delete_dislike(s, uid, pref_id)


@router.post("/menu/{day}/meals/{slot}/recipe")
def recipe(day: date, slot: IN.Slot, uid: uuid.UUID = Depends(current_user), s: Session = Depends(get_session),
           lang: Lang = LANG):
    """AI đề xuất cách chế biến. Lỗi/timeout LLM ⇒ giữ công thức cũ nếu có, nếu không dùng template."""
    limiter.hit(f"recipe:{uid}", *RL.RECIPE)  # mỗi lần gọi LLM trả phí
    return MS.recipe(s, uid, day, slot, lang)


# ---------------- nguyên liệu có sẵn ----------------
class PantryIn(BaseModel):
    day: date
    food_code: str
    grams: float


@router.get("/pantry")
def pantry(day: date, uid: uuid.UUID = Depends(current_user), s: Session = Depends(get_session)):
    return MS.list_pantry(s, uid, day)


@router.post("/pantry", status_code=201)
def add_pantry(body: PantryIn, uid: uuid.UUID = Depends(current_user), s: Session = Depends(get_session)):
    return {"warnings": MS.add_pantry(s, uid, body.day, body.food_code, body.grams)}


@router.delete("/pantry/{item_id}", status_code=204)
def del_pantry(item_id: int, uid: uuid.UUID = Depends(current_user), s: Session = Depends(get_session)):
    MS.delete_pantry(s, uid, item_id)


# ---------------- chatbot ----------------
class ChatIn(BaseModel):
    message: str
    # Lựa chọn sau câu hỏi lại (clarify): mention → "food:<mã>" | "dish:<mã>" (mã phải có trong catalog)
    resolved: dict[str, str] | None = Field(None, max_length=5)


@router.post("/chat")
def chat(body: ChatIn, uid: uuid.UUID = Depends(current_user), s: Session = Depends(get_session), lang: Lang = LANG):
    limiter.hit(f"chat:{uid}", *RL.CHAT)  # mỗi tin nhắn có thể gọi LLM trả phí
    return CS.send(s, uid, body.message, lang=lang, resolved=body.resolved)


@router.get("/chat/history")
def chat_history(uid: uuid.UUID = Depends(current_user), s: Session = Depends(get_session)):
    return CS.history(s, uid)


@router.post("/chat/proposals/{proposal_id}/apply")
def apply(proposal_id: uuid.UUID, uid: uuid.UUID = Depends(current_user), s: Session = Depends(get_session),
          lang: Lang = LANG):
    res = CS.apply_proposal(s, uid, proposal_id)
    return {**res, "menu": _menu_out(s, uid, date.fromisoformat(res["day"]), lang) if res["day"] else None}
