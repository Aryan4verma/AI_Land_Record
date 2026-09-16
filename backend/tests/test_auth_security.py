"""Unit checks for password hashing and JWT handling. No DB involved."""
import asyncio
import time

import jwt
import pytest

from app.auth.dependencies import require_role
from app.auth.security import create_access_token, decode_access_token, hash_password, verify_password
from app.errors import AppError

SECRET = "unit-test-secret-0123456789abcdef-unit"


def test_password_roundtrip():
    hashed = hash_password("correct horse")
    assert hashed != "correct horse"
    assert verify_password("correct horse", hashed) is True
    assert verify_password("wrong horse", hashed) is False


def test_password_verify_handles_garbage_hash():
    assert verify_password("anything", "not-a-valid-hash") is False


def test_token_roundtrip():
    token = create_access_token(user_id="u1", role="verifier", secret=SECRET, expires_minutes=60)
    claims = decode_access_token(token, SECRET)
    assert claims["sub"] == "u1"
    assert claims["role"] == "verifier"


def test_token_rejected_with_wrong_secret():
    token = create_access_token(user_id="u1", role="operator", secret=SECRET, expires_minutes=60)
    with pytest.raises(AppError) as exc_info:
        decode_access_token(token, "a-different-secret-0123456789abcdef")
    assert exc_info.value.status == 401


def test_expired_token_rejected():
    payload = {"sub": "u1", "role": "operator", "iat": int(time.time()) - 3600, "exp": int(time.time()) - 10}
    token = jwt.encode(payload, SECRET, algorithm="HS256")
    with pytest.raises(AppError) as exc_info:
        decode_access_token(token, SECRET)
    assert exc_info.value.code == "TOKEN_EXPIRED"


def test_tampered_token_rejected():
    token = create_access_token(user_id="u1", role="admin", secret=SECRET, expires_minutes=60)
    with pytest.raises(AppError):
        decode_access_token(token + "tampered", SECRET)


class _StubStore:
    """Stands in for the user store require_role now consults."""

    def __init__(self, role="operator", status="active", missing=False):
        self.role, self.status, self.missing = role, status, missing

    def get_by_id(self, user_id):
        if self.missing:
            return None
        return {"id": user_id, "role": self.role, "status": self.status}


def _authorize(minimum, claim_role, store):
    return asyncio.run(require_role(minimum)({"id": "x", "role": claim_role}, store))


def test_require_role_hierarchy():
    """Ladder is user < operator < admin (admin internal-only)."""
    assert _authorize("operator", "operator", _StubStore("operator"))["role"] == "operator"
    assert _authorize("operator", "admin", _StubStore("admin"))["role"] == "admin"
    with pytest.raises(AppError) as exc_info:
        _authorize("operator", "user", _StubStore("user"))
    assert exc_info.value.status == 403

    for role in ("user", "operator", "admin"):
        assert _authorize("user", role, _StubStore(role))["role"] == role


def test_require_role_normalizes_case_and_whitespace():
    assert _authorize("operator", "  OPERATOR ", _StubStore("  OPERATOR "))["role"] == "operator"


def test_privileged_action_uses_the_stored_role_not_the_token():
    """A token minted before a demotion must not still authorize the action."""
    with pytest.raises(AppError) as exc_info:
        _authorize("operator", "operator", _StubStore(role="user"))
    assert exc_info.value.status == 403
    assert exc_info.value.code == "INSUFFICIENT_ROLE"


def test_privileged_action_rejects_a_deactivated_account():
    for status in ("inactive", "suspended"):
        with pytest.raises(AppError) as exc_info:
            _authorize("operator", "operator", _StubStore(status=status))
        assert exc_info.value.status == 401


def test_privileged_action_rejects_a_deleted_account():
    with pytest.raises(AppError) as exc_info:
        _authorize("operator", "operator", _StubStore(missing=True))
    assert exc_info.value.status == 401


def test_retired_verifier_role_is_not_authorized():
    """`verifier` is retired: it fails closed rather than being reinterpreted."""
    with pytest.raises(KeyError):
        _authorize("operator", "verifier", _StubStore("verifier"))
    with pytest.raises(ValueError):
        require_role("verifier")
