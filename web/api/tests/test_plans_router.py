from fastapi.testclient import TestClient

from web.api.main import app


def test_list_plans_is_public(monkeypatch):
    """Pricing pages must work without auth even when the token is set."""
    monkeypatch.setenv("REDTONOMOUS_API_TOKEN", "secret")
    import importlib

    import web.api.auth as auth
    import web.api.main as main_module
    importlib.reload(auth)
    importlib.reload(main_module)

    client = TestClient(main_module.app)
    r = client.get("/plans")
    assert r.status_code == 200
    body = r.json()
    assert "plans" in body
    ids = [p["id"] for p in body["plans"]]
    assert "free" in ids and "red" in ids


def test_plan_by_id_includes_pricing():
    client = TestClient(app)
    r = client.get("/plans/pro")
    assert r.status_code == 200
    body = r.json()
    assert body["price_usd"] == 19.0
    assert "moonlight mode" in " ".join(body["features"]).lower() or any(
        "moonlight" in f.lower() for f in body["features"]
    )


def test_unknown_plan_returns_404():
    client = TestClient(app)
    r = client.get("/plans/enterprise-elite")
    assert r.status_code == 404
