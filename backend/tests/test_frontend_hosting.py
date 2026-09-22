"""Same-origin production bundle hosting tests."""

from fastapi.testclient import TestClient

from app import main as main_module


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
        api = client.get("/api/v1/no-such-route")

    assert root.status_code == 200 and "bundle" in root.text
    assert nested.status_code == 200 and "bundle" in nested.text
    assert asset.status_code == 200 and "console.log" in asset.text
    assert api.status_code == 404
    assert api.json()["error"]["code"] == "NOT_FOUND"
