"""Guardrail y tế: disclaimer, bệnh nền nhạy cảm, nhắc nhở insulin/thuốc. Chữ hiển thị nằm trong app/i18n."""

from app.core.i18n import Lang, tr
from app.nutrition.schemas import DIABETES, SENSITIVE_CONDITIONS, Condition


def sensitive_conditions(conditions) -> list[str]:
    return sorted(str(c) for c in conditions if Condition(c) in SENSITIVE_CONDITIONS)


def conditions_without_limits(conditions, covered: set) -> list[str]:
    """Bệnh nền nhạy cảm chưa có giới hạn do người dùng cung cấp. Giới hạn chung (condition NULL) phủ mọi bệnh.
    KHÔNG chặn sinh thực đơn: chỉ dùng mục tiêu chung + notice NO_LIMITS_* (app không tự đặt giới hạn y khoa)."""
    if None in covered:
        return []
    return [c for c in sensitive_conditions(conditions) if c not in covered]


def menu_notices(conditions, uses_meds: bool, lang: Lang = "vi", no_limits=()) -> list[dict]:
    codes = ["DISCLAIMER"]
    if {Condition(c) for c in conditions} & DIABETES and uses_meds:
        codes.append("CONSULT_DOCTOR_INSULIN")
    if Condition.hypertension in [Condition(c) for c in conditions]:
        codes.append("SODIUM_SEASONING")
    codes += [f"NO_LIMITS_{c.upper()}" for c in no_limits]
    return [{"code": c, "text": tr(f"notice.{c}", lang)} for c in codes]
