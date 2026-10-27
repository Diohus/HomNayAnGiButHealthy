import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.routes import router
from app.core.config import get_settings, validate_settings
from app.core.errors import AppError, KeyedValueError
from app.core.i18n import Lang, has_key, request_lang, tr
from app.core.logging import setup_logging

log = logging.getLogger("app")


# Tham số lỗi Pydantic được phép điền vào thông điệp (không bao giờ dùng `input`)
_VALIDATION_PARAMS = ("ge", "gt", "le", "lt", "min_length", "max_length", "expected")


def validation_message(err: dict, lang: Lang) -> str:
    """Thông điệp validation theo ngôn ngữ: KeyedValueError ⇒ khóa riêng; lỗi Pydantic ⇒ `validation.<type>`."""
    ctx = err.get("ctx") or {}
    exc = ctx.get("error")
    if isinstance(exc, KeyedValueError):
        return tr(exc.key, lang, **exc.params)
    key = f"validation.{err['type']}"
    if not has_key(key):
        return tr("validation.invalid", lang)
    return tr(key, lang, **{k: ctx[k] for k in _VALIDATION_PARAMS if k in ctx})


def create_app() -> FastAPI:
    setup_logging()
    validate_settings(get_settings())  # secret yếu/khóa sai ⇒ RuntimeError, app không khởi động
    app = FastAPI(title="HomNayAnGi API", version="0.1.0")
    app.add_middleware(CORSMiddleware, allow_origins=get_settings().cors_origins.split(","), allow_credentials=True,
                       allow_methods=["*"], allow_headers=["*"])

    @app.exception_handler(AppError)
    async def _app_error(request: Request, e: AppError):
        return JSONResponse(status_code=e.status, content=e.body(request_lang(request)))

    @app.exception_handler(RequestValidationError)
    async def _validation(request: Request, e: RequestValidationError):
        # Không trả lại `input` (có thể chứa dữ liệu sức khỏe) và không log nội dung
        lang = request_lang(request)
        errors = [{"field": ".".join(str(x) for x in err["loc"][1:]), "message": validation_message(err, lang)}
                  for err in e.errors()]
        return JSONResponse(status_code=422, content={"code": "VALIDATION_ERROR",
                                                      "message": tr("error.VALIDATION_ERROR", lang), "errors": errors})

    @app.exception_handler(StarletteHTTPException)
    async def _http(request: Request, e: StarletteHTTPException):
        key = "error.HTTP" if e.status_code < 500 else "error.INTERNAL"
        return JSONResponse(status_code=e.status_code,
                            content={"code": f"HTTP_{e.status_code}", "message": tr(key, request_lang(request))})

    @app.exception_handler(Exception)
    async def _unhandled(request: Request, e: Exception):
        log.error("unhandled %s on %s %s", type(e).__name__, request.method, request.url.path)  # không log body
        return JSONResponse(status_code=500, content={"code": "INTERNAL",
                                                      "message": tr("error.INTERNAL", request_lang(request))})

    @app.get("/api/health")
    def health():
        return {"status": "ok"}

    app.include_router(router)
    return app


app = create_app()
