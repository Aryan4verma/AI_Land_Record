"""Health endpoint checks. No live database is used."""


def test_health_ok(client):
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["version"] == "0.1.0"
    assert "X-Request-ID" in response.headers


def test_health_database_not_configured(client):
    response = client.get("/health/database")
    assert response.status_code == 503
    error = response.json()["error"]
    assert error["code"] == "SERVICE_NOT_CONFIGURED"
    assert error["request_id"]


def test_health_ai_not_configured_yet(client, monkeypatch):
    import app.routers.health as health_module
    from types import SimpleNamespace

    # Deterministic regardless of the developer's local .env (which may
    # hold real keys): force the unconfigured state for this case.
    monkeypatch.setattr(
        health_module, "get_settings",
        lambda: SimpleNamespace(ai_provider="", ai_model="", gemini_api_key="",
                                openrouter_api_key="", ai_fallbacks="", ai_cache_enabled=False),
    )
    response = client.get("/health/ai")
    assert response.status_code == 200
    assert response.json()["ai"] == "not_configured"


def test_health_ai_reflects_live_configuration(client, monkeypatch):
    from types import SimpleNamespace

    import app.routers.health as health_module

    settings = SimpleNamespace(ai_provider="gemini", ai_model="m", gemini_api_key="k",
                               ai_fallbacks="openrouter:m2", ai_cache_enabled=True)
    monkeypatch.setattr(health_module, "get_settings", lambda: settings)
    body = client.get("/health/ai").json()
    # demo_enabled is an additive capability flag: it tells the UI whether to
    # offer the Demo selector. The server still enforces the rule itself.
    assert body == {"ai": "configured", "provider": "gemini", "model": "m",
                    "lanes": 2, "cache_enabled": True, "demo_enabled": False}
    assert "k" not in str(body)  # keys never leak into health output


def test_protected_endpoint_requires_token(client):
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHENTICATED"
