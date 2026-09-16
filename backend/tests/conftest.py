"""Pytest bootstrap. Forces test isolation: fixed AUTH_SECRET and NO live
Supabase access, regardless of the developer's shell environment.
"""
import os

os.environ["AUTH_SECRET"] = "test-only-secret-0123456789abcdef-test"
os.environ["SUPABASE_URL"] = ""
os.environ["SUPABASE_ANON_KEY"] = ""
os.environ["SUPABASE_SERVICE_ROLE_KEY"] = ""
os.environ["ENVIRONMENT"] = "testing"

import pytest  # noqa: E402

from fastapi.testclient import TestClient  # noqa: E402

from app.auth.security import hash_password  # noqa: E402
from app.auth.store import get_user_store  # noqa: E402
from app.main import app  # noqa: E402

# Fixed UUIDs so fakes mirror production rows (DB ids are UUIDs).
OP_ID = "11111111-1111-4111-8111-111111111111"
OFF_ID = "22222222-2222-4222-8222-222222222222"
# Second operator identity (formerly the `verifier` fixture): those
# capabilities moved to `operator`, so the id is kept for
# correction-attribution checks.
VER_ID = "33333333-3333-4333-8333-333333333333"
# Read-only actor: every privileged endpoint must answer 403 for this role.
USER_ID = "44444444-4444-4444-8444-444444444444"

_USERS = {
    "op@example.com": {
        "id": OP_ID,
        "name": "Op",
        "email": "op@example.com",
        "password_hash": hash_password("op-pass"),
        "role": "operator",
        "status": "active",
    },
    "ver@example.com": {
        "id": VER_ID,
        "name": "Ver",
        "email": "ver@example.com",
        "password_hash": hash_password("ver-pass"),
        "role": "operator",
        "status": "active",
    },
    "user@example.com": {
        "id": USER_ID,
        "name": "Reader",
        "email": "user@example.com",
        "password_hash": hash_password("user-pass"),
        "role": "user",
        "status": "active",
    },
    "off@example.com": {
        "id": OFF_ID,
        "name": "Off",
        "email": "off@example.com",
        "password_hash": hash_password("off-pass"),
        "role": "operator",
        "status": "inactive",
    },
}


class InMemoryUserStore:
    def get_by_email(self, email):
        return _USERS.get(email)

    def get_by_id(self, user_id):
        return next((u for u in _USERS.values() if u["id"] == user_id), None)

    def create_user(self, row):
        import uuid as _uuid

        saved = {
            "id": str(_uuid.uuid4()),
            "created_at": "2026-09-05T00:00:00+00:00",
            **row,
        }
        _USERS[saved["email"]] = saved
        return saved


@pytest.fixture(autouse=True)
def _memory_user_store():
    app.dependency_overrides[get_user_store] = lambda: InMemoryUserStore()
    yield
    app.dependency_overrides.clear()


@pytest.fixture()
def client():
    with TestClient(app) as test_client:
        yield test_client
