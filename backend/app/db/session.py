from collections.abc import Iterator

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import get_settings


class Base(DeclarativeBase):
    pass


_engine = None
_SessionLocal: sessionmaker | None = None


def _sqlite_fk_on(dbapi_conn, _):
    # SQLite chỉ thực thi FK (ON DELETE CASCADE khi xóa tài khoản) khi bật pragma trên từng kết nối
    dbapi_conn.execute("PRAGMA foreign_keys=ON")


def init_engine(url: str | None = None, **kwargs):
    global _engine, _SessionLocal
    url = url or get_settings().database_url
    _engine = create_engine(url, pool_pre_ping=True, **kwargs)
    if url.startswith("sqlite"):
        event.listen(_engine, "connect", _sqlite_fk_on)
    _SessionLocal = sessionmaker(bind=_engine, expire_on_commit=False)
    return _engine


def get_engine():
    return _engine or init_engine()


def get_session() -> Iterator[Session]:
    if _SessionLocal is None:
        init_engine()
    with _SessionLocal() as s:
        yield s
