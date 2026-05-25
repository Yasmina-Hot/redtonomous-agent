"""Regression tests for the path-traversal fix in files_router."""
from pathlib import Path

from fastapi.testclient import TestClient

from web.api.main import app


def test_list_files_within_root(tmp_path: Path, monkeypatch):
    (tmp_path / "hello.txt").write_text("hi")
    monkeypatch.setenv("REDTONOMOUS_FILES_ROOT", str(tmp_path))
    client = TestClient(app)
    r = client.get("/files", params={"path": "."})
    assert r.status_code == 200
    names = [e["name"] for e in r.json()]
    assert "hello.txt" in names


def test_read_file_within_root(tmp_path: Path, monkeypatch):
    (tmp_path / "ok.txt").write_text("payload")
    monkeypatch.setenv("REDTONOMOUS_FILES_ROOT", str(tmp_path))
    client = TestClient(app)
    r = client.get("/file", params={"path": "ok.txt"})
    assert r.status_code == 200
    assert r.text == "payload"


def test_traversal_blocked(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("REDTONOMOUS_FILES_ROOT", str(tmp_path))
    client = TestClient(app)
    r = client.get("/file", params={"path": "../../etc/passwd"})
    assert r.status_code == 403


def test_absolute_path_blocked(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("REDTONOMOUS_FILES_ROOT", str(tmp_path))
    client = TestClient(app)
    # An absolute path outside the root must be rejected, not silently followed.
    r = client.get("/file", params={"path": "/etc/passwd"})
    assert r.status_code == 403
