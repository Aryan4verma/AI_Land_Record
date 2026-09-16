"""Error-envelope contract: every failure uses the standard shape and
validation errors never echo submitted values."""


def test_unknown_route_uses_envelope(client):
    response = client.get("/no-such-route")
    assert response.status_code == 404
    error = response.json()["error"]
    assert error["code"] == "NOT_FOUND"
    assert error["request_id"]


def test_login_validation_error_never_echoes_password(client):
    response = client.post("/api/v1/auth/login", json={"email": "a@b.co"})
    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "VALIDATION_ERROR"
    assert "secret" not in body["error"]["message"].lower()
