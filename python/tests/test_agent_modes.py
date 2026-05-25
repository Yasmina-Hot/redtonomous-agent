"""End-to-end tests of the agent loop with a mocked adapter — exercises
budget cap, wall-clock cap, tool allow/deny lists, and the dry-run path.
"""
from __future__ import annotations

from pathlib import Path
from typing import Iterator

from redtonomous.agent import EXIT_BUDGET, EXIT_WALLCLOCK, run
from redtonomous.models.base import ModelAdapter, ModelResponse, ToolCall


class _ScriptedAdapter(ModelAdapter):
    """Replay a fixed list of responses, charging fixed token counts."""

    def __init__(self, responses: list[ModelResponse]):
        self._iter: Iterator[ModelResponse] = iter(responses)
        self._calls = 0

    def chat(self, messages, tools, system=""):
        self._calls += 1
        try:
            return next(self._iter)
        except StopIteration:
            # Default: stop cleanly.
            return ModelResponse(text="(done)", stop_reason="end_turn", tool_calls=[],
                                 input_tokens=10, output_tokens=10)

    def build_tool_result_messages(self, tool_calls, results):
        return [
            {"role": "assistant", "content": "..."},
            {"role": "user", "content": f"tool_results: {results}"},
        ]


def _file_write(path: str, content: str = "hi"):
    return ModelResponse(
        text="working",
        stop_reason="tool_use",
        tool_calls=[ToolCall(id="t1", name="write_file", args={"path": path, "content": content})],
        input_tokens=1_000_000,  # 1M input tokens per call
        output_tokens=500_000,   # to make budget arithmetic obvious
    )


def _done(text="all done"):
    return ModelResponse(text=text, stop_reason="end_turn", tool_calls=[],
                         input_tokens=100, output_tokens=100)


def test_run_completes_cleanly(tmp_path: Path):
    target = tmp_path / "out.txt"
    adapter = _ScriptedAdapter([_file_write(str(target), "hello"), _done()])
    res = run(
        task="write a file", adapter=adapter,
        provider="claude", model="claude-sonnet-4-6",
        cwd=str(tmp_path), max_iterations=5, backup=False, log=False,
    )
    assert res.completed is True
    assert res.exit_code == 0
    assert target.read_text() == "hello"
    assert res.iterations >= 1


def test_run_dry_run_skips_writes(tmp_path: Path):
    target = tmp_path / "skipped.txt"
    adapter = _ScriptedAdapter([_file_write(str(target), "x"), _done()])
    res = run(
        task="t", adapter=adapter,
        provider="claude", model="claude-sonnet-4-6",
        cwd=str(tmp_path), max_iterations=5, backup=False, log=False,
        dry_run=True,
    )
    assert res.completed is True
    assert not target.exists()


def test_run_budget_cap_halts(tmp_path: Path):
    # claude-sonnet-4-6 is $3/MTok in. With 1M in per call, each call costs ~$3.
    # Cap at $1 means budget should blow on the very first call.
    adapter = _ScriptedAdapter([_file_write(str(tmp_path / "x"), "x"), _done()])
    res = run(
        task="t", adapter=adapter,
        provider="claude", model="claude-sonnet-4-6",
        cwd=str(tmp_path), max_iterations=5, backup=False, log=False,
        budget_usd=1.0,
    )
    assert res.exit_code == EXIT_BUDGET
    assert res.completed is False


def test_run_wallclock_cap_halts(tmp_path: Path):
    """The wall-clock cap is checked at the top of each iteration. We give
    the first iteration a chat that sleeps long enough to push us past the
    cap; the *next* iteration's check trips ``WallClockExceeded``.
    """
    import time

    class _SlowAdapter(_ScriptedAdapter):
        def chat(self, messages, tools, system=""):
            time.sleep(0.05)
            # First call: do a write so the loop continues. Subsequent calls
            # default to ``_done`` via the base class, but we should hit the
            # wall-clock cap before that fires.
            return _file_write(str(tmp_path / "x"), "x")

    adapter = _SlowAdapter([])
    res = run(
        task="t", adapter=adapter,
        provider="claude", model="claude-sonnet-4-6",
        cwd=str(tmp_path), max_iterations=5, backup=False, log=False,
        max_hours=0.05 / 3600,  # 50ms — second iteration's check trips it.
    )
    assert res.exit_code == EXIT_WALLCLOCK


def test_run_tool_deny_list_filters(tmp_path: Path):
    """If write_file is denied, the model never sees it. We can't easily
    assert the model behavior, but we *can* assert _filter_tools removes it.
    """
    from redtonomous.agent import _filter_tools
    filtered = _filter_tools(allow=None, deny=["write_file"])
    names = [t["name"] for t in filtered]
    assert "write_file" not in names
    assert "read_file" in names


def test_run_tool_allow_list_filters(tmp_path: Path):
    from redtonomous.agent import _filter_tools
    filtered = _filter_tools(allow=["read_file", "list_directory"], deny=None)
    assert {t["name"] for t in filtered} == {"read_file", "list_directory"}


def test_run_with_hooks_records_on_done(tmp_path: Path, monkeypatch):
    """`on_done` hook should fire even when the run completes cleanly."""
    import json
    import redtonomous.modes as modes

    sentinel = tmp_path / "done.flag"
    hooks_file = tmp_path / "hooks.json"
    hooks_file.write_text(json.dumps({
        "on_done": f'echo "$REDTONOMOUS_COMPLETED" > {sentinel}',
    }))
    monkeypatch.setenv(modes.HOOKS_FILE_ENV, str(hooks_file))

    adapter = _ScriptedAdapter([_done()])
    run(
        task="t", adapter=adapter,
        provider="claude", model="claude-sonnet-4-6",
        cwd=str(tmp_path), max_iterations=2, backup=False, log=False,
    )
    assert sentinel.exists()
    assert sentinel.read_text().strip() == "1"
