import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

from . import display
from .models.base import ModelAdapter
from .tools.definitions import TOOLS
from .tools.executor import execute_tool

SYSTEM_PROMPT = """\
You are Redtonomous — a fully autonomous software engineering agent.
You have unrestricted permission to read/write files, execute shell commands,
install packages, run builds, and fetch URLs within the working directory.

Rules:
1. Complete every task FULLY. Never stop halfway.
2. Make real changes. Do not just plan or describe.
3. Install missing dependencies with the shell tool if needed.
4. After writing code, run it to verify it works. Fix any errors before finishing.
5. Think through the full dependency and execution order before starting.
6. Never ask the user for confirmation. Just do it.
7. When done, summarize exactly what was built/changed.

Working directory: {cwd}
Provider: {provider} | Model: {model}
"""


def _ts() -> str:
    """ISO-8601 basic timestamp (no separators) — matches the TS + Go ports."""
    return datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")


def load_resume(session_id: str) -> dict[str, Any]:
    """Load a persisted session log for ``--resume``.

    Returns the raw dict (``task``, ``provider``, ``model``, ``cwd``, ``log``).
    Raises FileNotFoundError if the session is missing.
    """
    from . import config as cfg_module
    logs_dir = cfg_module.ensure_logs_dir()
    candidate = logs_dir / (session_id if session_id.endswith(".json") else f"{session_id}.json")
    if not candidate.exists():
        # Try the unprefixed form (the on-disk files are named "session_<ts>.json")
        candidate = logs_dir / f"session_{session_id}.json"
    if not candidate.exists():
        raise FileNotFoundError(f"No session log matching {session_id!r}")
    with open(candidate) as f:
        return json.load(f)


def _hydrate_messages(task: str, resumed: dict[str, Any] | None) -> list[dict]:
    messages: list[dict] = [{"role": "user", "content": task}]
    if not resumed:
        return messages
    # Replay tool calls/results as plain text so any provider can continue.
    prior = "\n".join(
        f"[iter {step['iter']}] {step['tool']}({json.dumps(step.get('args', {}))}) "
        f"→ {'error' if step.get('error') else 'ok'}: {step.get('result', '')[:200]}"
        for step in resumed.get("log", [])[-20:]
    )
    if prior:
        messages.insert(0, {
            "role": "user",
            "content": (
                "Resuming a previous session. Here are the last actions taken:\n\n"
                f"{prior}\n\nContinue from where you left off."
            ),
        })
    return messages


def run(
    task: str,
    adapter: ModelAdapter,
    provider: str,
    model: str,
    cwd: str,
    max_iterations: int = 100,
    backup: bool = True,
    log: bool = True,
    resume: dict[str, Any] | None = None,
) -> None:
    if backup:
        ts = _ts()
        dst = f"{cwd.rstrip('/')}_backup_{ts}"
        try:
            shutil.copytree(cwd, dst, dirs_exist_ok=False)
            display.print_backup(cwd, dst)
        except Exception as e:
            display.print_info(f"Backup skipped: {e}")

    system = SYSTEM_PROMPT.format(cwd=cwd, provider=provider, model=model)
    messages = _hydrate_messages(task, resume)
    session_log: list[dict] = list(resume.get("log", [])) if resume else []
    total_in = total_out = 0

    display.console.rule("[bold red]Redtonomous[/bold red]")
    display.print_info(f"Task: {task}")
    if resume:
        display.print_info(f"Resumed from session ({len(session_log)} prior steps)")
    display.print_info(f"Model: {provider}/{model}  |  Dir: {cwd}  |  Max iterations: {max_iterations}")
    display.console.rule()

    for iteration in range(max_iterations):
        resp = adapter.chat(messages=messages, tools=TOOLS, system=system)
        total_in += resp.input_tokens
        total_out += resp.output_tokens

        if resp.text:
            display.print_thinking(resp.text[:120])

        if resp.stop_reason in ("end_turn", "stop") and not resp.tool_calls:
            display.print_final(resp.text or "(Task complete)")
            break

        if not resp.tool_calls:
            display.print_final(resp.text or "(Task complete — no more tool calls)")
            break

        results: list[tuple[str, bool]] = []
        for tc in resp.tool_calls:
            display.print_tool_call(tc.name, tc.args)
            result, is_error = execute_tool(tc.name, tc.args)
            display.print_tool_result(tc.name, result, is_error)
            results.append((result, is_error))
            session_log.append({
                "iter": iteration,
                "tool": tc.name,
                "args": tc.args,
                "result": result[:500],
                "error": is_error,
            })

        new_msgs = adapter.build_tool_result_messages(resp.tool_calls, results)
        messages.extend(new_msgs)

    else:
        display.print_error(f"Reached max iterations ({max_iterations}). Task may be incomplete.")

    display.print_info(f"Tokens used — input: {total_in}  output: {total_out}")

    if log and session_log:
        from . import config as cfg_module
        logs_dir = cfg_module.ensure_logs_dir()
        log_file = Path(logs_dir) / f"session_{_ts()}.json"
        with open(log_file, "w") as f:
            json.dump({"task": task, "provider": provider, "model": model, "cwd": cwd, "log": session_log}, f, indent=2)
        display.print_info(f"Session log: {log_file}")
