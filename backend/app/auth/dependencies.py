"""Authentication dependencies. Identity is established ONLY from the
verified Bearer token — never from client-supplied fields (11 section 2).

Role ladder (02_PRD section 7):

    user < operator   [< admin, internal only]

`user` is the read-only floor; `operator` owns the full document and
review/approval workflow (the capabilities formerly gated as `verifier`).
`admin` is retained as an INTERNAL escalation rank only — it is never
user-facing, never offered at registration, and no endpoint requires it.
Role values are normalized to lowercase before any comparison.
"""
from typing import Any

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer

from ..config import get_settings
from ..errors import AppError
from .security import decode_access_token
from .store import get_user_store

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=True)

ROLE_HIERARCHY = {"user": 1, "operator": 2, "admin": 3}

# Roles a client may hold in a token. `verifier` is deliberately absent:
# its capabilities moved to `operator`, so a legacy verifier token now
# fails closed (401) instead of being silently reinterpreted.
CANONICAL_ROLES = frozenset(ROLE_HIERARCHY)


def normalize_role(value: object) -> str:
    """Lowercase/trim a stored or claimed role. Returns '' when unusable."""
    return value.strip().lower() if isinstance(value, str) else ""


async def get_current_user(token: str = Depends(oauth2_scheme)) -> dict:
    claims = decode_access_token(token, get_settings().auth_secret)
    role = normalize_role(claims.get("role"))
    if role not in ROLE_HIERARCHY:
        raise AppError(401, "INVALID_TOKEN", "Invalid authentication token.")
    return {"id": claims["sub"], "role": role}


def require_role(minimum: str):
    """Authorize a privileged action against the DATABASE, not just the token.

    A JWT carries the role held when it was issued. Re-reading the user here
    means a demotion or a deactivation takes effect on the next privileged
    request instead of lingering until the token expires. The extra lookup is
    deliberately confined to privileged actions — plain reads still authorize
    from the verified token alone and cost no round trip.

    If the user store is unavailable the request fails closed.
    """
    if minimum not in ROLE_HIERARCHY:
        raise ValueError(f"unknown role: {minimum}")

    async def checker(user: dict = Depends(get_current_user),
                      store: Any = Depends(get_user_store)) -> dict:
        claimed = normalize_role(user["role"])
        if ROLE_HIERARCHY[claimed] < ROLE_HIERARCHY[minimum]:
            raise AppError(403, "INSUFFICIENT_ROLE", "This action requires a higher role.")

        current = store.get_by_id(user["id"])
        if current is None or current.get("status") != "active":
            raise AppError(401, "INVALID_TOKEN", "Invalid authentication token.")
        role = normalize_role(current.get("role"))
        if role not in ROLE_HIERARCHY or ROLE_HIERARCHY[role] < ROLE_HIERARCHY[minimum]:
            # The stored role no longer permits this, whatever the token says.
            raise AppError(403, "INSUFFICIENT_ROLE", "This action requires a higher role.")
        # Hand downstream code the canonical, freshly-read value.
        return {**user, "role": role}

    return checker
