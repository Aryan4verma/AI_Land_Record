"""Same-origin production bundle hosting tests."""

from fastapi.testclient import TestClient

from app import main as main_module


def test_frontend_dist_resolves_container_and_local_layouts(tmp_path, monkeypatch):
    container_root = tmp_path / "container"
    container_file = container_root / "app" / "main.py"
    (container_root / "frontend" / "dist").mkdir(parents=True)
    (container_root / "frontend" / "dist" / "index.html").write_text("bundle", encoding="utf-8")
    monkeypatch.setattr(main_module, "__file__", str(container_file))
    assert main_module._frontend_dist() == container_root / "frontend" / "dist"

    local_root = tmp_path / "checkout"
    local_file = local_root / "backend" / "app" / "main.py"
    (local_root / "frontend" / "dist").mkdir(parents=True)
    (local_root / "frontend" / "dist" / "index.html").write_text("bundle", encoding="utf-8")
    monkeypatch.setattr(main_module, "__file__", str(local_file))
    assert main_module._frontend_dist() == local_root / "frontend" / "dist"


def test_frontend_bundle_and_assets_are_served_without_shadowing_api(tmp_path, monkeypatch):
    dist = tmp_path / "dist"
    assets = dist / "assets"
    assets.mkdir(parents=True)
    (dist / "index.html").write_text("<html><body>bundle</body></html>", encoding="utf-8")
    (assets / "app.js").write_text("console.log('ok')", encoding="utf-8")
    monkeypatch.setattr(main_module, "_frontend_dist", lambda: dist)

    with TestClient(main_module.create_app()) as client:
        root = client.get("/")
        nested = client.get("/app/records", headers={"Accept": "text/html"})
        asset = client.get("/assets/app.js")
        health = client.get("/health")
        auth = client.get("/api/v1/auth/me")
        api = client.get("/api/v1/no-such-route")

    assert root.status_code == 200 and "bundle" in root.text
    assert nested.status_code == 200 and "bundle" in nested.text
    assert asset.status_code == 200 and "console.log" in asset.text
    assert health.status_code == 200
    assert auth.status_code == 401
    assert api.status_code == 404
    assert api.json()["error"]["code"] == "NOT_FOUND"


def test_backend_only_mode_works_without_frontend_build(tmp_path, monkeypatch):
    monkeypatch.setattr(main_module, "_frontend_dist", lambda: tmp_path / "missing-dist")

    with TestClient(main_module.create_app()) as client:
        health = client.get("/health")
        auth = client.get("/api/v1/auth/me")
        root = client.get("/")

    assert health.status_code == 200
    assert auth.status_code == 401
    assert root.status_code == 404
