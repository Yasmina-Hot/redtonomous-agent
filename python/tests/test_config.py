import importlib
from pathlib import Path


def test_load_save_aliases(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("HOME", str(tmp_path))
    # Re-import config so it picks up the patched HOME for CONFIG_DIR.
    from redtonomous import config as cfg

    importlib.reload(cfg)
    cfg.save_config({"default_provider": "claude", "default_model": "claude-sonnet-4-6", "providers": {}})

    loaded = cfg.load_config()
    assert loaded["default_provider"] == "claude"

    # The short-name aliases must point at the same function objects.
    assert cfg.load is cfg.load_config
    assert cfg.save is cfg.save_config


def test_redact_sensitive():
    from redtonomous.config import redact_sensitive

    payload = {
        "command": "echo hi",
        "api_key": "sk-secret",
        "headers": {"Authorization": "Bearer abc", "claude_api_key": "k"},
        "nested": [{"token": "t", "name": "ok"}],
    }
    out = redact_sensitive(payload)
    assert out["api_key"] == "***"
    assert out["headers"]["claude_api_key"] == "***"
    assert out["nested"][0]["token"] == "***"
    # Keys that aren't sensitive must be preserved verbatim.
    assert out["command"] == "echo hi"
    assert out["nested"][0]["name"] == "ok"
