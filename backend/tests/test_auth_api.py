"""Auth endpoint checks against an in-memory user store (no live DB)."""
import uuid

from tests.conftest import OP_ID


def test_login_success_returns_bearer_token(client):
    response = client.post("/api/v1/auth/login", json={"email": "op@example.com", "password": "op-pass"})
    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]
    assert "password_hash" not in response.text


def test_login_wrong_password_rejected_without_enumeration(client):
    bad_password = client.post(
        "/api/v1/auth/login", json={"email": "op@example.com", "password": "nope"}
    )
    unknown_user = client.post(
        "/api/v1/auth/login", json={"email": "nobody@example.com", "password": "nope"}
    )
    assert bad_password.status_code == 401
    assert unknown_user.status_code == 401
    # Identical code + message (request_id is unique per request by design).
    assert bad_password.json()["error"]["code"] == "INVALID_CREDENTIALS"
    assert bad_password.json()["error"]["message"] == unknown_user.json()["error"]["message"]


def test_login_inactive_user_rejected(client):
    response = client.post("/api/v1/auth/login", json={"email": "off@example.com", "password": "off-pass"})
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "INVALID_CREDENTIALS"


def test_me_returns_current_user_without_password_hash(client):
    login = client.post("/api/v1/auth/login", json={"email": "op@example.com", "password": "op-pass"})
    token = login.json()["access_token"]
    response = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    body = response.json()
    assert body == {
        "id": OP_ID,
        "name": "Op",
        "email": "op@example.com",
        "role": "operator",
        "status": "active",
        "id_number": None,
    }


def test_deactivated_account_token_is_rejected_on_read_routes(client):
    from tests.conftest import _USERS

    login = client.post("/api/v1/auth/login", json={"email": "op@example.com", "password": "op-pass"})
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    original_status = _USERS["op@example.com"]["status"]
    _USERS["op@example.com"]["status"] = "suspended"
    try:
        response = client.get("/api/v1/records", headers=headers)
        assert response.status_code == 401
        assert response.json()["error"]["code"] == "INVALID_TOKEN"
    finally:
        _USERS["op@example.com"]["status"] = original_status


def test_logout_ok(client):
    response = client.post("/api/v1/auth/logout")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_repeated_failed_logins_are_throttled_then_reset_on_success(client):
    """Login abuse protection: only FAILED attempts count, and a real sign-in
    clears the counter so ordinary users are never locked out."""
    from app.auth.rate_limit import get_login_limiter

    limiter = get_login_limiter()
    limiter.clear()
    try:
        for _ in range(limiter.max_attempts):
            bad = client.post("/api/v1/auth/login",
                              json={"email": "op@example.com", "password": "wrong"})
            assert bad.status_code == 401

        blocked = client.post("/api/v1/auth/login",
                              json={"email": "op@example.com", "password": "wrong"})
        assert blocked.status_code == 429
        assert blocked.json()["error"]["code"] == "TOO_MANY_ATTEMPTS"

        # Even the correct password is refused while the window is open.
        assert client.post("/api/v1/auth/login",
                           json={"email": "op@example.com", "password": "op-pass"}
                           ).status_code == 429

        limiter.clear()
        ok = client.post("/api/v1/auth/login",
                         json={"email": "op@example.com", "password": "op-pass"})
        assert ok.status_code == 200
        # A success resets the counter, so failures do not accumulate forever.
        assert not limiter.is_blocked(next(iter(limiter._hits), "unused"))
    finally:
        limiter.clear()


def test_successful_logins_are_never_throttled(client):
    """Valid credentials must not trip the limiter, however many times used."""
    from app.auth.rate_limit import get_login_limiter

    limiter = get_login_limiter()
    limiter.clear()
    try:
        for _ in range(limiter.max_attempts + 5):
            ok = client.post("/api/v1/auth/login",
                             json={"email": "op@example.com", "password": "op-pass"})
            assert ok.status_code == 200
    finally:
        limiter.clear()


def test_throttling_is_scoped_per_account(client):
    """One throttled account must not lock out a different one."""
    from app.auth.rate_limit import get_login_limiter

    limiter = get_login_limiter()
    limiter.clear()
    try:
        for _ in range(limiter.max_attempts):
            client.post("/api/v1/auth/login",
                        json={"email": "op@example.com", "password": "wrong"})
        assert client.post("/api/v1/auth/login",
                           json={"email": "op@example.com", "password": "wrong"}
                           ).status_code == 429
        # Different email, same client: unaffected.
        assert client.post("/api/v1/auth/login",
                           json={"email": "user@example.com", "password": "user-pass"}
                           ).status_code == 200
    finally:
        limiter.clear()


def _new_email():
    return f"new-{uuid.uuid4().hex[:8]}@example.com"


def _register_body(**overrides):
    body = {
        "name": "New Officer",
        "id_number": "ID-2026-001",
        "email": _new_email(),
        "password": "correct-horse-42",
    }
    body.update(overrides)
    return body


def test_register_creates_read_only_user_account_without_secrets(client):
    response = client.post("/api/v1/auth/register", json=_register_body())
    assert response.status_code == 201
    body = response.json()
    assert body["email"] in response.text
    assert body["name"] == "New Officer"
    assert body["id_number"] == "ID-2026-001"
    assert body["role"] == "user"  # never operator: registration is least-privilege
    assert body["status"] == "active"
    assert body["id"] and body["created_at"]
    assert "password" not in response.text
    assert "hash" not in response.text


def test_register_duplicate_email_rejected_with_exact_message(client):
    first = _register_body(email="dup@example.com")
    assert client.post("/api/v1/auth/register", json=first).status_code == 201
    second = client.post("/api/v1/auth/register", json=_register_body(email="dup@example.com"))
    assert second.status_code == 409
    assert second.json()["error"]["code"] == "USER_EXISTS"
    assert second.json()["error"]["message"] == "An account with this email already exists."


def test_register_existing_seed_email_rejected(client):
    response = client.post("/api/v1/auth/register", json=_register_body(email="op@example.com"))
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "USER_EXISTS"


def test_register_rejects_blank_name_id_and_bad_email(client):
    assert client.post("/api/v1/auth/register", json=_register_body(name="   ")).status_code == 422
    assert client.post("/api/v1/auth/register", json=_register_body(id_number="  ")).status_code == 422
    bad_email = client.post("/api/v1/auth/register", json=_register_body(email="not-an-email"))
    assert bad_email.status_code == 422


def test_register_rejects_short_password(client):
    response = client.post("/api/v1/auth/register", json=_register_body(password="short7"))
    assert response.status_code == 422


def test_register_ignores_client_supplied_role(client):
    for attempted in ("admin", "operator", "verifier"):
        response = client.post("/api/v1/auth/register",
                               json={**_register_body(), "role": attempted, "status": "active"})
        assert response.status_code == 201
        assert response.json()["role"] == "user"


def test_register_ignores_client_supplied_status(client):
    """`status` is server-controlled: a client cannot self-suspend or
    pre-activate anything, and cannot smuggle a privileged state in."""
    for attempted in ("suspended", "inactive", "ACTIVE"):
        response = client.post("/api/v1/auth/register",
                               json={**_register_body(), "status": attempted})
        assert response.status_code == 201
        assert response.json()["status"] == "active"


def test_register_ignores_unknown_and_privileged_body_keys(client):
    """Extra keys are ignored, never persisted as-is."""
    response = client.post("/api/v1/auth/register", json={
        **_register_body(),
        "role": "admin",
        "status": "suspended",
        "id": "00000000-0000-4000-8000-000000000000",
        "password_hash": "injected",
        "auth_id": "00000000-0000-4000-8000-000000000001",
    })
    assert response.status_code == 201
    body = response.json()
    assert body["role"] == "user"
    assert body["status"] == "active"
    assert body["id"] != "00000000-0000-4000-8000-000000000000"
    assert "injected" not in response.text


def test_register_email_uniqueness_is_case_insensitive(client):
    """Emails are normalized to lowercase, so casing cannot bypass the
    duplicate check and create a second account for the same address."""
    assert client.post("/api/v1/auth/register",
                       json=_register_body(email="Case@Example.com")).status_code == 201
    duplicate = client.post("/api/v1/auth/register",
                            json=_register_body(email="CASE@EXAMPLE.COM"))
    assert duplicate.status_code == 409
    assert duplicate.json()["error"]["code"] == "USER_EXISTS"


def test_register_stores_a_verifying_bcrypt_hash_not_the_password(client):
    """The password is hashed with bcrypt and never round-trips in cleartext."""
    from app.auth.security import verify_password
    from tests.conftest import _USERS

    email = _new_email()
    password = "correct-horse-42"
    assert client.post("/api/v1/auth/register",
                       json=_register_body(email=email, password=password)).status_code == 201
    stored = _USERS[email]["password_hash"]
    assert stored != password
    assert stored.startswith("$2b$")
    assert verify_password(password, stored) is True
    assert verify_password("wrong-password", stored) is False


def test_registered_user_is_read_only_end_to_end(client):
    """Signup -> login -> /me(role=user) -> denied on the privileged surface."""
    email = _new_email()
    assert client.post("/api/v1/auth/register",
                       json=_register_body(email=email)).status_code == 201
    login = client.post("/api/v1/auth/login",
                        json={"email": email, "password": "correct-horse-42"})
    assert login.status_code == 200
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    me = client.get("/api/v1/auth/me", headers=headers)
    assert me.status_code == 200 and me.json()["role"] == "user"

    rec = "00000000-0000-4000-8000-0000000000aa"
    assert client.post("/api/v1/documents", headers=headers, files={
        "file": ("x.pdf", b"%PDF-1.4 ", "application/pdf")}).status_code == 403
    assert client.post(f"/api/v1/documents/{rec}/process", headers=headers).status_code == 403
    assert client.get("/api/v1/reviews", headers=headers).status_code == 403
    assert client.post(f"/api/v1/records/{rec}/approve", json={}, headers=headers).status_code == 403
    assert client.post(f"/api/v1/records/{rec}/reject", json={"reason": "r"},
                       headers=headers).status_code == 403
    assert client.get(f"/api/v1/records/{rec}/audit", headers=headers).status_code == 403

    assert client.post("/api/v1/auth/logout", headers=headers).status_code == 200


def test_login_is_case_insensitive_for_email(client):
    """A registered address logs in regardless of the casing typed."""
    email = _new_email()
    assert client.post("/api/v1/auth/register",
                       json=_register_body(email=email)).status_code == 201
    login = client.post("/api/v1/auth/login",
                        json={"email": email.upper(), "password": "correct-horse-42"})
    assert login.status_code == 200


def test_registered_account_logs_in_with_same_credentials(client):
    email = _new_email()
    assert client.post("/api/v1/auth/register", json=_register_body(email=email)).status_code == 201
    login = client.post("/api/v1/auth/login", json={"email": email, "password": "correct-horse-42"})
    assert login.status_code == 200
    assert login.json()["access_token"]
    me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {login.json()['access_token']}"})
    assert me.status_code == 200
    assert me.json()["email"] == email
    assert me.json()["role"] == "user"
