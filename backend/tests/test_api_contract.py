"""Focused API contract checks: versioning, status classes, envelopes, IDs."""

import time

import jwt


def _token(client, email="user@example.com", password="user-pass"):
    return client.post("/api/v1/auth/login", json={"email": email, "password": password}).json()["access_token"]


def test_protected_api_uses_v1_and_401_envelope_with_request_id(client):
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401
    assert response.headers["X-Request-ID"] == response.json()["error"]["request_id"]
    assert response.json()["error"]["code"] == "UNAUTHENTICATED"

    paths = set(client.app.openapi()["paths"])
    assert "/api/v1/auth/login" in paths
    assert "/api/v1/records" in paths
    assert "/api/auth/login" not in paths


def test_authenticated_but_forbidden_is_403_enveloped(client):
    response = client.get("/api/v1/reviews", headers={"Authorization": f"Bearer {_token(client)}"})
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "INSUFFICIENT_ROLE"
    assert response.json()["error"]["request_id"] == response.headers["X-Request-ID"]


def test_expired_bearer_token_is_rejected_at_the_api_boundary(client):
    # Keep this deterministic: replace the signed expiry with an already
    # expired token rather than depending on a wall-clock sleep.
    expired = jwt.encode(
        {"sub": "11111111-1111-4111-8111-111111111111", "role": "operator",
         "iat": int(time.time()) - 120, "exp": int(time.time()) - 60},
        "test-only-secret-0123456789abcdef-test", algorithm="HS256",
    )
    assert expired
    response = client.get("/api/v1/reviews", headers={"Authorization": f"Bearer {expired}"})
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "TOKEN_EXPIRED"


def test_validation_and_rate_limit_contracts_are_422_and_429(client):
    invalid = client.post("/api/v1/auth/register", json={"name": "A"})
    assert invalid.status_code == 422
    assert invalid.json()["error"]["code"] == "VALIDATION_ERROR"
    assert invalid.json()["error"]["request_id"] == invalid.headers["X-Request-ID"]

    from app.auth.rate_limit import get_login_limiter

    limiter = get_login_limiter()
    limiter.clear()
    try:
        for _ in range(limiter.max_attempts):
            assert client.post(
                "/api/v1/auth/login",
                json={"email": "contract@example.com", "password": "wrong"},
            ).status_code == 401
        limited = client.post(
            "/api/v1/auth/login",
            json={"email": "contract@example.com", "password": "wrong"},
        )
        assert limited.status_code == 429
        assert limited.json()["error"]["code"] == "TOO_MANY_ATTEMPTS"
        assert limited.json()["error"]["request_id"] == limited.headers["X-Request-ID"]
    finally:
        limiter.clear()


def test_dependency_unavailable_is_503_without_internal_details(client):
    response = client.get("/health/database")
    assert response.status_code == 503
    error = response.json()["error"]
    assert error["code"] == "SERVICE_NOT_CONFIGURED"
    assert error["request_id"] == response.headers["X-Request-ID"]
    assert "supabase" not in response.text.lower()
