import uuid

from fastapi import Depends, Header
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.core.security import decode_access_token
from app.db import models as M
from app.db.session import get_session


def current_user(authorization: str | None = Header(None), s: Session = Depends(get_session)) -> uuid.UUID:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise AppError(401, "UNAUTHENTICATED")
    uid = decode_access_token(authorization.split(" ", 1)[1])
    if uid is None or s.get(M.User, uid) is None:
        raise AppError(401, "INVALID_TOKEN")
    return uid
