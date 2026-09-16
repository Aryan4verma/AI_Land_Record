"""Password hashing (bcrypt, SHA-256 pre-hash so long passwords are safe)
and JWT issue/verify. Secrets stay in server environment variables."""
import base64
import hashlib
import time

import bcrypt
import jwt

from ..errors import AppError

_ALGORITHM = "HS256"


def _digest(password: str) -> bytes:
    return base64.b64encode(hashlib.sha256(password.encode("utf-8")).digest())


def hash_password(password: str) -> str:
    return bcrypt.hashpw(_digest(password), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(_digest(password), hashed.encode("utf-8"))
    except Exception:
        return False


def create_access_token(*, user_id: str, role: str, secret: str, expires_minutes: int) -> str:
    now = int(time.time())
    payload = {"sub": user_id, "role": role, "iat": now, "exp": now + expires_minutes * 60}
    return jwt.encode(payload, secret, algorithm=_ALGORITHM)


def decode_access_token(token: str, secret: str) -> dict:
    try:
        return jwt.decode(token, secret, algorithms=[_ALGORITHM], options={"require": ["sub", "role", "exp"]})
    except jwt.ExpiredSignatureError as exc:
        raise AppError(401, "TOKEN_EXPIRED", "Session has expired. Please log in again.") from exc
    except jwt.InvalidTokenError as exc:
        raise AppError(401, "INVALID_TOKEN", "Invalid authentication token.") from exc
