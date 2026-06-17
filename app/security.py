"""Password hashing (bcrypt) and JWT token helpers.

We use the `bcrypt` library directly instead of passlib because passlib 1.7.x
is incompatible with bcrypt >= 4.1 (it crashes reading the removed
``bcrypt.__about__`` module).
"""
from datetime import timedelta

import bcrypt
from jose import jwt

from app.config import settings
from app.utils import utcnow

# bcrypt rejects secrets longer than 72 bytes; truncate consistently.
_BCRYPT_MAX_BYTES = 72


def _truncate(password: str) -> bytes:
    return password.encode("utf-8")[:_BCRYPT_MAX_BYTES]


def hash_password(password: str) -> str:
    return bcrypt.hashpw(_truncate(password), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(_truncate(plain), hashed.encode("utf-8"))
    except (ValueError, TypeError):
        return False


def create_access_token(*, subject: int, role: str, expires_minutes: int | None = None) -> str:
    expire = utcnow() + timedelta(
        minutes=expires_minutes or settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    payload = {"sub": str(subject), "role": role, "exp": expire}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_token(token: str) -> dict:
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
