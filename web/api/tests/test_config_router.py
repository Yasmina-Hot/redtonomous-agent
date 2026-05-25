from pathlib import Path

from fastapi.testclient import TestClient

from web.api.main import app


def test_config_get_masks_api_keys(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("HOME", str(tmp_path))
    # Write a config with a fake API key, then read it back through the API.
    import importlib

    from redtonomous import config as cfg
    importlib.reload(cfg)
    cfg.save_config({
        "default_provider": "claude",
        "default_model": "claude-sonnet-4-6",
        "providers": {"claude": {"api_key": "sk-abcdefghijklmnop"}},
    })

    client = TestClient(app)
    r = client.get("/config")
    assert r.status_code == 200
    body = r.json()
    masked = body["providers"]["claude"]["api_key"]
    assert masked != "sk-abcdefghijklmnop"
    assert masked.endswith("…")


def test_config_post_rejects_unknown_keys(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("HOME", str(tmp_path))
    client = TestClient(app)
    r = client.post("/config", json={"raw": {"hax": "yes"}})
    assert r.status_code == 400
    assert "hax" in r.text


def test_config_post_round_trip(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("HOME", str(tmp_path))
    client = TestClient(app)
    payload = {
        "raw": {
            "default_provider": "claude",
            "default_model": "claude-opus-4-7",
            "providers": {"claude": {"api_key": "k"}},
        }
    }
    r = client.post("/config", json=payload)
    assert r.status_code == 200
    r2 = client.get("/config")
    assert r2.json()["default_model"] == "claude-opus-4-7"


def test_raw_endpoint_removed(monkeypatch, tmp_path: Path):
    """The /config/raw endpoint leaked unmasked secrets and must not exist."""
    monkeypatch.setenv("HOME", str(tmp_path))
    client = TestClient(app)
    r = client.get("/config/raw")
    assert r.status_code == 404
