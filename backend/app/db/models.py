"""Schema PostgreSQL. Dữ liệu sức khỏe (hồ sơ, giới hạn chuyên gia, nội dung chat, đề xuất) lưu dạng mã hóa.
Mọi bảng của người dùng có ON DELETE CASCADE từ users ⇒ "xóa toàn bộ dữ liệu" = xóa 1 dòng users.
"""

import uuid
from datetime import UTC, date, datetime

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    LargeBinary,
    String,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


def _now() -> datetime:
    return datetime.now(UTC)


def _uid() -> Mapped[uuid.UUID]:
    return mapped_column(Uuid, ForeignKey("users.id", ondelete="CASCADE"), index=True)


class User(Base):
    __tablename__ = "users"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(254), unique=True)
    password_hash: Mapped[str] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[uuid.UUID] = _uid()
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked: Mapped[bool] = mapped_column(Boolean, default=False)
    # Thời điểm token bị xoay vòng (NULL = chưa xoay hoặc bị thu hồi do đăng xuất). Dùng cho khoảng ân hạn reuse.
    rotated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class HealthProfile(Base):
    __tablename__ = "health_profiles"
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    encrypted_payload: Mapped[bytes] = mapped_column(LargeBinary)  # HealthProfileIn (giới tính, tuổi, bệnh nền, dị ứng...)
    version: Mapped[int] = mapped_column(Integer, default=1)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)


class HealthLimit(Base):
    """Giới hạn sức khỏe do người dùng cung cấp (thay bảng expert_confirmations từ vòng 4)."""

    __tablename__ = "health_limits"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[uuid.UUID] = _uid()
    condition_code: Mapped[str | None] = mapped_column(String(32), nullable=True)  # NULL = áp dụng chung
    encrypted_payload: Mapped[bytes] = mapped_column(LargeBinary)  # HealthLimits
    source: Mapped[str] = mapped_column(String(16), default="manual")  # manual | document
    confirmed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    # NULL không bị UNIQUE chặn ⇒ upsert theo (user, condition) do service đảm bảo
    __table_args__ = (UniqueConstraint("user_id", "condition_code"),)


class Nutrient(Base):
    __tablename__ = "nutrients"
    code: Mapped[str] = mapped_column(String(32), primary_key=True)
    unit: Mapped[str] = mapped_column(String(8))


class Ingredient(Base):
    __tablename__ = "ingredients"
    code: Mapped[str] = mapped_column(String(64), primary_key=True)
    owner_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)  # nhập từ nhãn
    name_vi: Mapped[str] = mapped_column(String(120))
    name_en: Mapped[str] = mapped_column(String(160))  # mô tả USDA (dữ liệu nguồn)
    display_en: Mapped[str | None] = mapped_column(String(80), nullable=True)  # tên hiển thị tiếng Anh
    category: Mapped[str] = mapped_column(String(16))
    tags: Mapped[list] = mapped_column(JSON, default=list)
    aliases: Mapped[list] = mapped_column(JSON, default=list)
    min_g: Mapped[float] = mapped_column(Float)
    max_g: Mapped[float] = mapped_column(Float)
    step_g: Mapped[float] = mapped_column(Float)
    slots: Mapped[str] = mapped_column(String(4))
    gi: Mapped[float | None] = mapped_column(Float, nullable=True)
    gi_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    source: Mapped[dict] = mapped_column(JSON)
    portion: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    unverified_nutrients: Mapped[list] = mapped_column(JSON, default=list)
    nutrients: Mapped[list["IngredientNutrient"]] = relationship(cascade="all, delete-orphan", lazy="selectin")


class IngredientNutrient(Base):
    __tablename__ = "ingredient_nutrients"
    ingredient_code: Mapped[str] = mapped_column(String(64), ForeignKey("ingredients.code", ondelete="CASCADE"),
                                                 primary_key=True)
    nutrient_code: Mapped[str] = mapped_column(String(32), ForeignKey("nutrients.code"), primary_key=True)
    amount_per_100g: Mapped[float | None] = mapped_column(Float, nullable=True)  # NULL = chưa xác minh
    source_ref: Mapped[str] = mapped_column(String(200))


class Dish(Base):
    __tablename__ = "dishes"
    code: Mapped[str] = mapped_column(String(64), primary_key=True)
    name_vi: Mapped[str] = mapped_column(String(120))
    name_en: Mapped[str | None] = mapped_column(String(160), nullable=True)
    slots: Mapped[str] = mapped_column(String(4))
    components: Mapped[list["DishComponent"]] = relationship(cascade="all, delete-orphan", lazy="selectin")


class DishComponent(Base):
    __tablename__ = "dish_components"
    dish_code: Mapped[str] = mapped_column(String(64), ForeignKey("dishes.code", ondelete="CASCADE"), primary_key=True)
    ingredient_code: Mapped[str] = mapped_column(String(64), ForeignKey("ingredients.code"), primary_key=True)
    role: Mapped[str] = mapped_column(String(16), default="main")


class MenuDay(Base):
    __tablename__ = "menu_days"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[uuid.UUID] = _uid()
    day: Mapped[date] = mapped_column(Date)
    version: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[str] = mapped_column(String(16))  # ok | partial | conflict
    targets: Mapped[list] = mapped_column(JSON)  # snapshot mục tiêu khi sinh
    report: Mapped[dict] = mapped_column(JSON)  # deviations, shortfalls, suggestions, conflicts, warnings
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)
    meals: Mapped[list["Meal"]] = relationship(cascade="all, delete-orphan", lazy="selectin", order_by="Meal.id")
    __table_args__ = (UniqueConstraint("user_id", "day"),)


class Meal(Base):
    __tablename__ = "meals"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    menu_day_id: Mapped[int] = mapped_column(Integer, ForeignKey("menu_days.id", ondelete="CASCADE"), index=True)
    slot: Mapped[str] = mapped_column(String(16))
    active: Mapped[bool] = mapped_column(Boolean, default=True)  # False: giữ dữ liệu khi đổi 3↔2 bữa
    dish_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    items: Mapped[list["MealItem"]] = relationship(cascade="all, delete-orphan", lazy="selectin",
                                                   order_by="MealItem.id")
    recipe: Mapped["Recipe | None"] = relationship(cascade="all, delete-orphan", lazy="selectin", uselist=False)


class MealItem(Base):
    __tablename__ = "meal_items"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    meal_id: Mapped[int] = mapped_column(Integer, ForeignKey("meals.id", ondelete="CASCADE"), index=True)
    ingredient_code: Mapped[str] = mapped_column(String(64), ForeignKey("ingredients.code"))
    grams: Mapped[float] = mapped_column(Float)
    locked: Mapped[bool] = mapped_column(Boolean, default=False)
    origin: Mapped[str] = mapped_column(String(16), default="optimizer")


class Recipe(Base):
    __tablename__ = "recipes"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    meal_id: Mapped[int] = mapped_column(Integer, ForeignKey("meals.id", ondelete="CASCADE"), unique=True)
    content: Mapped[dict] = mapped_column(JSON)  # steps, seasonings, tip
    source: Mapped[str] = mapped_column(String(16))  # llm | template
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class FoodPreference(Base):
    """Món / nguyên liệu không thích (ràng buộc mềm của planner). Không phải dữ liệu sức khỏe ⇒ không mã hóa."""

    __tablename__ = "food_preferences"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[uuid.UUID] = _uid()
    kind: Mapped[str] = mapped_column(String(8))  # food | dish
    code: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    __table_args__ = (UniqueConstraint("user_id", "kind", "code"),)


class IntakeEntry(Base):
    """Nhật ký "đã ăn". Không mã hóa — nhất quán với menu_days (món + gram, không phải hồ sơ sức khỏe)."""

    __tablename__ = "intake_entries"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[uuid.UUID] = _uid()
    day: Mapped[date] = mapped_column(Date, index=True)
    slot: Mapped[str] = mapped_column(String(16))  # breakfast | lunch | dinner | snack
    food_code: Mapped[str] = mapped_column(String(64))
    grams: Mapped[float] = mapped_column(Float)
    source: Mapped[str] = mapped_column(String(16))  # plan | chat | manual | ai_estimate
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class PantryItem(Base):
    __tablename__ = "pantry_items"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[uuid.UUID] = _uid()
    day: Mapped[date] = mapped_column(Date)
    ingredient_code: Mapped[str] = mapped_column(String(64), ForeignKey("ingredients.code"))
    grams: Mapped[float] = mapped_column(Float)


class EnergyAdjustment(Base):
    __tablename__ = "energy_adjustments"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[uuid.UUID] = _uid()
    day: Mapped[date] = mapped_column(Date)
    delta_kcal: Mapped[float] = mapped_column(Float)
    reason: Mapped[str] = mapped_column(String(32))  # cheat_day_compensation
    source_day: Mapped[date | None] = mapped_column(Date, nullable=True)


class SafetyEvent(Base):
    """Chỉ loại sự kiện + thời điểm. Không lưu nội dung."""

    __tablename__ = "safety_events"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[uuid.UUID] = _uid()
    kind: Mapped[str] = mapped_column(String(32))
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class ChatMessage(Base):
    __tablename__ = "chat_messages"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[uuid.UUID] = _uid()
    role: Mapped[str] = mapped_column(String(16))  # user | assistant
    encrypted_content: Mapped[bytes] = mapped_column(LargeBinary)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, index=True)


class ChatProposal(Base):
    __tablename__ = "chat_proposals"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = _uid()
    message_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("chat_messages.id", ondelete="CASCADE"),
                                                   nullable=True)
    encrypted_payload: Mapped[bytes] = mapped_column(LargeBinary)  # Proposal
    base_version: Mapped[int] = mapped_column(Integer)  # version của menu_day lúc đề xuất (0 = chưa có)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    applied: Mapped[bool] = mapped_column(Boolean, default=False)
