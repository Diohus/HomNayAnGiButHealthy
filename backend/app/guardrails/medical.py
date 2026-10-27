"""Guardrail y tế: disclaimer, bệnh nền nhạy cảm, nhắc nhở insulin/thuốc. Chữ hiển thị nằm trong app/i18n."""

from app.core.i18n import Lang, tr
from app.nutrition.schemas import DIABETES, SENSITIVE_CONDITIONS, Condition


def pending_expert_confirmations(conditions, confirmed: set[str]) -> list[str]:
    """Bệnh nền nhạy cảm chưa có xác nhận chuyên gia (kèm giới hạn) ⇒ chưa được sinh thực đơn."""
    return sorted(str(c) for c in conditions if Condition(c) in SENSITIVE_CONDITIONS and str(c) not in confirmed)


def menu_notices(conditions, uses_meds: bool, lang: Lang = "vi") -> list[dict]:
    codes = ["DISCLAIMER"]
    if {Condition(c) for c in conditions} & DIABETES and uses_meds:
        codes.append("CONSULT_DOCTOR_INSULIN")
    if Condition.hypertension in [Condition(c) for c in conditions]:
        codes.append("SODIUM_SEASONING")
    return [{"code": c, "text": tr(f"notice.{c}", lang)} for c in codes]
