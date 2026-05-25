"""Tests for WallClock + Heartbeat + hooks + dry-run + judge parsing."""
import json
import time

import pytest

from redtonomous import modes
from redtonomous.judge import _parse
from redtonomous.agent import _dry_run_tool


def test_wallclock_check_raises():
    wc = modes.WallClock(cap_seconds=0.001)
    time.sleep(0.01)
    with pytest.raises(modes.WallClockExceeded):
        wc.check()


def test_wallclock_no_cap_never_raises():
    wc = modes.WallClock(cap_seconds=0.0)
    wc.check()  # must not raise


def test_heartbeat_only_emits_after_period():
    calls: list[str] = []
    hb = modes.Heartbeat(emit=calls.append, period_s=10.0)
    hb.tick({"iter": 1})
    assert calls == []  # too soon
    hb.last_at -= 11  # fast-forward
    hb.tick({"iter": 2, "tokens": 42})
    assert len(calls) == 1
    assert "iter=2" in calls[0] and "tokens=42" in calls[0]


def test_hooks_fire(monkeypatch, tmp_path):
    sentinel = tmp_path / "hook-ran.txt"
    hooks_file = tmp_path / "hooks.json"
    hooks_file.write_text(json.dumps({
        "post_tool": f'echo "$REDTONOMOUS_TOOL" > {sentinel}',
    }))
    monkeypatch.setenv(modes.HOOKS_FILE_ENV, str(hooks_file))

    modes.fire_hook("post_tool", {"tool": "write_file", "args": "{}"})
    assert sentinel.exists()
    assert sentinel.read_text().strip() == "write_file"


def test_hooks_missing_file_is_silent(monkeypatch, tmp_path):
    monkeypatch.setenv(modes.HOOKS_FILE_ENV, str(tmp_path / "nope.json"))
    # Must not raise.
    modes.fire_hook("on_error", {"tool": "x"})


def test_dry_run_stubs_destructive_tools(tmp_path):
    target = tmp_path / "should-not-exist.txt"
    out, is_error = _dry_run_tool("write_file", {"path": str(target), "content": "hi"})
    assert "dry-run" in out
    assert is_error is False
    assert not target.exists()


def test_dry_run_passes_through_readonly_tools(tmp_path):
    src = tmp_path / "a.txt"
    src.write_text("hello")
    out, is_error = _dry_run_tool("read_file", {"path": str(src)})
    assert is_error is False
    assert "hello" in out


def test_judge_parse_strict_json():
    v = _parse('{"achieved": true, "missing": "", "confidence": 0.9}')
    assert v.achieved is True
    assert v.confidence == 0.9


def test_judge_parse_extracts_from_markdown():
    text = 'Here is my verdict:\n```\n{"achieved": false, "missing": "no tests", "confidence": 0.4}\n```'
    v = _parse(text)
    assert v.achieved is False
    assert v.missing == "no tests"


def test_judge_parse_handles_garbage():
    v = _parse("I am not JSON.")
    assert v.achieved is False
    assert "could not parse" in v.missing
