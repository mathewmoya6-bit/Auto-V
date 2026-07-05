# app/core/security.py
# =============================================================================
# AUTO-V API - Password hashing + JWT access tokens
# Used by app/api/v1/endpoints/auth.py
# =============================================================================

from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Falls back to sane defaults if these aren't already declared on Settings.
_SECRET_KEY = getattr(settings, "secret_key", None) or getattr(settings, "jwt_secret", None) or "change-me"
_ALGORITHM = getattr(settings, "algorithm", "HS256")
_ACCESS_TOKEN_EXPIRE_MINUTES = int(getattr(settings, "access_token_expire_minutes", 1440))


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, password_hash: str) -> bool:
    try:
        return pwd_context.verify(plain_password, password_hash)
    except Exception:
        return False


def create_access_token(subject: str, expires_minutes: Optional[int] = None) -> str:
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=expires_minutes if expires_minutes is not None else _ACCESS_TOKEN_EXPIRE_MINUTES
    )
    to_encode: dict[str, Any] = {"sub": subject, "exp": expire}
    return jwt.encode(to_encode, _SECRET_KEY, algorithm=_ALGORITHM)


def decode_access_token(token: str) -> Optional[dict]:
    try:
        return jwt.decode(token, _SECRET_KEY, algorithms=[_ALGORITHM])
    except JWTError:
        return None
