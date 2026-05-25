from fastapi.testclient import TestClient


def _app_with_token(monkeypatch, token: str):
    monkeypatch.setenv("REDTONOMOUS_API_TOKEN", token)
    import importlib

    import web.api.auth as auth
    import web.api.main as main_module

    importlib.reload(auth)
    importlib.reload(main_module)
    return main_module.app


def test_health_is_public(monkeypatch):
    app = _app_with_token(monkeypatch, "secret")
    client = TestClient(app)
    r = client.get("/health")
    assert r.status_code == 200


def test_protected_endpoint_requires_token(monkeypatch):
    app = _app_with_token(monkeypatch, "secret")
    client = TestClient(app)
    r = client.get("/config")
    assert r.status_code == 401


def test_protected_endpoint_accepts_bearer(monkeypatch, tmp_path):
    monkeypatch.setenv("HOME", str(tmp_path))  # isolate ~/.redtonomous
    app = _app_with_token(monkeypatch, "secret")
    client = TestClient(app)
    r = client.get("/config", headers={"Authorization": "Bearer secret"})
    assert r.status_code == 200


def test_protected_endpoint_rejects_wrong_token(monkeypatch):
    app = _app_with_token(monkeypatch, "secret")
    client = TestClient(app)
    r = client.get("/config", headers={"Authorization": "Bearer nope"})
    assert r.status_code == 401


def test_open_dev_mode_when_unset(monkeypatch):
    monkeypatch.delenv("REDTONOMOUS_API_TOKEN", raising=False)
    import importlib

    import web.api.auth as auth
    import web.api.main as main_module

    importlib.reload(auth)
    importlib.reload(main_module)
    client = TestClient(main_module.app)
    r = client.get("/config")
    # In open dev mode any request goes through.
    assert r.status_code == 200
