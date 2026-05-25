"""CLI-level tests for the new subcommands: red gate, undo behavior."""
from __future__ import annotations

from pathlib import Path

from click.testing import CliRunner

from redtonomous.cli import main


def test_red_refuses_without_env_var(monkeypatch):
    monkeypatch.delenv("REDTONOMOUS_I_KNOW_WHAT_IM_DOING", raising=False)
    runner = CliRunner()
    res = runner.invoke(main, ["red", "build a thing"])
    assert res.exit_code == 1
    assert "REDTONOMOUS_I_KNOW_WHAT_IM_DOING" in (res.output or "")


def test_undo_restores_from_latest_backup(tmp_path: Path, monkeypatch):
    work = tmp_path / "proj"
    work.mkdir()
    (work / "keep.txt").write_text("orig")
    backup = tmp_path / "proj_backup_20260101T010101Z"
    backup.mkdir()
    (backup / "keep.txt").write_text("restored")
    (backup / "extra.txt").write_text("only in backup")

    runner = CliRunner()
    res = runner.invoke(main, ["undo", "--dir", str(work), "--yes"])
    assert res.exit_code == 0, res.output
    assert (work / "keep.txt").read_text() == "restored"
    assert (work / "extra.txt").read_text() == "only in backup"


def test_undo_errors_when_no_backup(tmp_path: Path):
    work = tmp_path / "lonely"
    work.mkdir()
    runner = CliRunner()
    res = runner.invoke(main, ["undo", "--dir", str(work), "--yes"])
    assert res.exit_code == 1
    assert "No backup" in (res.output or "")
