class AppError(Exception):
    """Lỗi nghiệp vụ trả về client: `code` ổn định + thông điệp dịch theo Accept-Language (khóa `error.<code>`
    hoặc `key` riêng). `params` điền vào thông điệp và trả kèm body (đã dịch). Không chứa dữ liệu sức khỏe."""

    def __init__(self, status: int, code: str, *, key: str | None = None, params: dict | None = None, **extra):
        self.status, self.code, self.extra = status, code, extra
        self.key = key or f"error.{code}"
        self.params = params or {}
        super().__init__(code)

    def body(self, lang) -> dict:
        from app.core.i18n import resolve, tr

        params = {k: resolve(v, lang) for k, v in self.params.items()}
        out = {"code": self.code, "message": tr(self.key, lang, **self.params), **self.extra}
        if params:
            out["params"] = params
        return out


class KeyedValueError(ValueError):
    """ValueError mang khóa i18n (dùng trong validator Pydantic); exception handler dịch theo ngôn ngữ."""

    def __init__(self, key: str, **params):
        self.key, self.params = key, params
        super().__init__(key)
