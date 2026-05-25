import json
import shutil
import subprocess
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

from . import display
from .models.base import ModelAdapter, ToolCall
from .modes import (
    Budget,
    BudgetExceeded,
    Heartbeat,
    WallClock,
    WallClockExceeded,
    fire_hook,
)
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


# Exit-code constants used by callers (CLI subcommands map these to sys.exit).
EXIT_OK = 0
EXIT_BUDGET = 3
EXIT_WALLCLOCK = 124
EXIT_MAX_ITER = 4


def _ts() -> str:
    """ISO-8601 basic timestamp (no separators) — matches the TS + Go ports."""
    return datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")


# Tool sets that mutate the filesystem / outside world. Used by ``--dry-run``
# and the diff feature.
DESTRUCTIVE_TOOLS = {
    "write_file",
    "append_file",
    "delete_file",
    "move_file",
    "create_directory",
    "execute_command",
}


@dataclass
class RunResult:
    """Structured result so the moonlight/goal wrappers can introspect."""

    completed: bool = False
    final_text: str = ""
    tokens_in: int = 0
    tokens_out: int = 0
    iterations: int = 0
    session_log: list[dict] = field(default_factory=list)
    exit_code: int = EXIT_OK
    messages: list[dict] = field(default_factory=list)


def load_resume(session_id: str) -> dict[str, Any]:
    """Load a persisted session log for ``--resume``."""
    from . import config as cfg_module
    logs_dir = cfg_module.ensure_logs_dir()
    candidate = logs_dir / (session_id if session_id.endswith(".json") else f"{session_id}.json")
    if not candidate.exists():
        candidate = logs_dir / f"session_{session_id}.json"
    if not candidate.exists():
        raise FileNotFoundError(f"No session log matching {session_id!r}")
    with open(candidate) as f:
        return json.load(f)


def _hydrate_messages(task: str, resumed: dict[str, Any] | None) -> list[dict]:
    messages: list[dict] = [{"role": "user", "content": task}]
    if not resumed:
        return messages
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


def _filter_tools(allow: list[str] | None, deny: list[str] | None) -> list[dict]:
    pool = list(TOOLS)
    if allow:
        names = {n.strip() for n in allow if n.strip()}
        pool = [t for t in pool if t["name"] in names]
    if deny:
        names = {n.strip() for n in deny if n.strip()}
        pool = [t for t in pool if t["name"] not in names]
    return pool


def _dry_run_tool(name: str, args: dict) -> tuple[str, bool]:
    """Stub destructive tools in --dry-run mode."""
    if name in DESTRUCTIVE_TOOLS:
        return (f"OK: [dry-run] would have called {name}({json.dumps(args)[:200]})", False)
    return execute_tool(name, args)


def _checkpoint_path(run_id: str) -> Path:
    from . import config as cfg_module
    sessions = Path(cfg_module.ensure_logs_dir()).parent / "sessions"
    sessions.mkdir(parents=True, exist_ok=True)
    return sessions / f"{run_id}.checkpoint.json"


def _write_checkpoint(run_id: str, payload: dict) -> None:
    try:
        with open(_checkpoint_path(run_id), "w") as f:
            json.dump(payload, f, indent=2)
    except OSError:
        pass


def _print_diff(cwd: str, files: set[str]) -> None:
    """Run ``git diff -- <files>`` against ``cwd`` and pretty-print it."""
    if not files:
        return
    try:
        # Only show diffs for files inside the cwd that are actually in git.
        scoped = [f for f in files if Path(f).exists()]
        if not scoped:
            return
        proc = subprocess.run(
            ["git", "-C", cwd, "diff", "--", *scoped],
            capture_output=True, text=True, timeout=30,
        )
        if proc.returncode == 0 and proc.stdout.strip():
            display.console.rule("[bold]Diff[/bold]")
            display.console.print(proc.stdout)
    except (OSError, subprocess.TimeoutExpired):
        pass


def _git_commit(cwd: str, message: str) -> None:
    try:
        subprocess.run(["git", "-C", cwd, "add", "-A"], check=False, timeout=30)
        proc = subprocess.run(
            ["git", "-C", cwd, "commit", "-m", message],
            capture_output=True, text=True, check=False, timeout=30,
        )
        if proc.returncode == 0:
            display.print_info(f"Committed: {message}")
        else:
            display.print_info(f"git commit skipped: {proc.stderr.strip() or proc.stdout.strip()}")
    except (OSError, subprocess.TimeoutExpired) as e:
        display.print_info(f"git commit skipped: {e}")


def _git_branch(cwd: str, branch: str) -> None:
    try:
        subprocess.run(
            ["git", "-C", cwd, "checkout", "-b", branch],
            check=False, timeout=30,
        )
        display.print_info(f"Switched to branch {branch}")
    except (OSError, subprocess.TimeoutExpired) as e:
        display.print_info(f"git branch skipped: {e}")


def _plan_first(adapter: ModelAdapter, task: str, system: str, yes: bool) -> bool:
    """Ask the model for a numbered plan first. Returns True if the user
    (or --yes) wants to proceed.
    """
    plan_prompt = (
        "Before doing anything, output ONLY a numbered plan for accomplishing "
        f"this task:\n\n{task}\n\nReturn 3-10 short bullet points, no preamble."
    )
    resp = adapter.chat(
        messages=[{"role": "user", "content": plan_prompt}],
        tools=[],
        system=system,
    )
    display.console.rule("[bold]Plan[/bold]")
    display.console.print(resp.text or "(model produced no plan)")
    display.console.rule()
    if yes:
        return True
    try:
        return input("Proceed with this plan? [Y/n] ").strip().lower() not in ("n", "no")
    except (EOFError, KeyboardInterrupt):
        return False


def _chat_with_retry(
    adapter: ModelAdapter,
    messages: list[dict],
    tools: list[dict],
    system: str,
    retries: int = 0,
):
    """Call ``adapter.chat`` with optional exponential-backoff retry on
    transient errors (rate limit, 5xx). ``retries=0`` keeps legacy behavior.
    """
    if retries <= 0:
        return adapter.chat(messages=messages, tools=tools, system=system)

    attempt = 0
    backoff = 1.0
    while True:
        try:
            return adapter.chat(messages=messages, tools=tools, system=system)
        except Exception as e:
            if attempt >= retries or not _is_transient(e):
                raise
            display.print_info(f"transient error ({type(e).__name__}) — retry in {backoff:.0f}s")
            time.sleep(min(backoff, 60.0))
            backoff *= 2
            attempt += 1


def _is_transient(exc: BaseException) -> bool:
    name = type(exc).__name__
    if "RateLimit" in name or "Timeout" in name:
        return True
    # OpenAI/Anthropic SDKs expose status_code; treat 429 and 5xx as transient.
    status = getattr(exc, "status_code", None) or getattr(exc, "code", None)
    if isinstance(status, int) and (status == 429 or 500 <= status < 600):
        return True
    return False


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
    *,
    yes: bool = True,
    budget_usd: float = 0.0,
    max_hours: float = 0.0,
    dry_run: bool = False,
    plan_first: bool = False,
    diff: bool = False,
    git_commit_msg: str | None = None,
    git_branch: str | None = None,
    tools_allow: list[str] | None = None,
    tools_deny: list[str] | None = None,
    retry_transient: int = 0,
    heartbeat_period_s: float = 0.0,
    checkpoint_every: int = 0,
    run_id: str | None = None,
    on_iteration: Callable[[int, RunResult], None] | None = None,
) -> RunResult:
    """The single agent loop. All extras default to off — legacy callers
    continue to behave exactly as before.
    """
    result = RunResult()
    run_id = run_id or _ts()

    if git_branch:
        _git_branch(cwd, git_branch)

    if backup and not dry_run:
        ts = _ts()
        dst = f"{cwd.rstrip('/')}_backup_{ts}"
        try:
            shutil.copytree(cwd, dst, dirs_exist_ok=False)
            display.print_backup(cwd, dst)
        except Exception as e:
            display.print_info(f"Backup skipped: {e}")

    system = SYSTEM_PROMPT.format(cwd=cwd, provider=provider, model=model)

    if plan_first:
        if not _plan_first(adapter, task, system, yes=yes):
            display.print_info("Aborted at plan review.")
            return result

    messages = _hydrate_messages(task, resume)
    session_log: list[dict] = list(resume.get("log", [])) if resume else []

    budget = Budget(cap_usd=budget_usd, model=model) if budget_usd > 0 else None
    wallclock = WallClock.from_hours(max_hours) if max_hours > 0 else None
    heartbeat = (
        Heartbeat(emit=display.print_info, period_s=heartbeat_period_s)
        if heartbeat_period_s > 0
        else None
    )

    pool = _filter_tools(tools_allow, tools_deny)
    tool_runner = _dry_run_tool if dry_run else execute_tool
    touched_files: set[str] = set()

    display.console.rule("[bold red]Redtonomous[/bold red]")
    display.print_info(f"Task: {task}")
    if resume:
        display.print_info(f"Resumed from session ({len(session_log)} prior steps)")
    if dry_run:
        display.print_info("[dry-run] destructive tools are stubbed out")
    if budget:
        display.print_info(f"Budget: ${budget.cap_usd:.2f}")
    if wallclock and wallclock.cap_seconds:
        display.print_info(f"Wall-clock cap: {wallclock.cap_seconds/3600:.2f}h")
    display.print_info(f"Model: {provider}/{model}  |  Dir: {cwd}  |  Max iterations: {max_iterations}")
    display.console.rule()

    iteration = 0
    try:
        for iteration in range(max_iterations):
            if wallclock:
                wallclock.check()

            resp = _chat_with_retry(adapter, messages, pool, system, retries=retry_transient)
            result.tokens_in += resp.input_tokens or 0
            result.tokens_out += resp.output_tokens or 0
            if budget:
                budget.charge(resp.input_tokens or 0, resp.output_tokens or 0)

            if resp.text:
                display.print_thinking(resp.text[:120])

            if not resp.tool_calls:
                result.completed = True
                result.final_text = resp.text or "(Task complete)"
                display.print_final(result.final_text)
                break

            results: list[tuple[str, bool]] = []
            for tc in resp.tool_calls:
                display.print_tool_call(tc.name, tc.args)
                fire_hook("pre_tool", {"tool": tc.name, "args": json.dumps(tc.args)[:1000]})
                tool_result, is_error = tool_runner(tc.name, tc.args)
                fire_hook("post_tool", {
                    "tool": tc.name,
                    "result": tool_result[:1000],
                    "error": "1" if is_error else "0",
                })
                if is_error:
                    fire_hook("on_error", {"tool": tc.name, "result": tool_result[:1000]})
                display.print_tool_result(tc.name, tool_result, is_error)
                results.append((tool_result, is_error))
                session_log.append({
                    "iter": iteration,
                    "tool": tc.name,
                    "args": tc.args,
                    "result": tool_result[:500],
                    "error": is_error,
                })
                _collect_touched(touched_files, tc, cwd)

            new_msgs = adapter.build_tool_result_messages(resp.tool_calls, results)
            messages.extend(new_msgs)

            if heartbeat:
                hb_payload: dict[str, Any] = {
                    "iter": iteration,
                    "tokens_in": result.tokens_in,
                    "tokens_out": result.tokens_out,
                }
                if budget:
                    hb_payload["cost"] = f"${budget.spent_usd:.4f}"
                if wallclock:
                    hb_payload["elapsed_s"] = f"{wallclock.elapsed():.0f}"
                heartbeat.tick(hb_payload)

            if checkpoint_every and iteration and iteration % checkpoint_every == 0:
                _write_checkpoint(run_id, {
                    "task": task, "provider": provider, "model": model, "cwd": cwd,
                    "iteration": iteration, "log": session_log,
                })

            if on_iteration:
                result.iterations = iteration + 1
                result.session_log = session_log
                on_iteration(iteration, result)
        else:
            display.print_error(f"Reached max iterations ({max_iterations}). Task may be incomplete.")
            result.exit_code = EXIT_MAX_ITER
    except BudgetExceeded as e:
        display.print_error(str(e))
        result.exit_code = EXIT_BUDGET
    except WallClockExceeded as e:
        display.print_error(str(e))
        result.exit_code = EXIT_WALLCLOCK

    result.iterations = iteration + 1
    result.session_log = session_log
    result.messages = messages

    display.print_info(
        f"Tokens used — input: {result.tokens_in}  output: {result.tokens_out}"
        + (f"  spent: ${budget.spent_usd:.4f}" if budget else "")
    )

    if log and session_log:
        from . import config as cfg_module
        logs_dir = cfg_module.ensure_logs_dir()
        log_file = Path(logs_dir) / f"session_{_ts()}.json"
        with open(log_file, "w") as f:
            json.dump({"task": task, "provider": provider, "model": model, "cwd": cwd, "log": session_log}, f, indent=2)
        display.print_info(f"Session log: {log_file}")

    if diff:
        _print_diff(cwd, touched_files)

    if git_commit_msg and result.completed and not dry_run:
        _git_commit(cwd, git_commit_msg)

    fire_hook("on_done", {
        "completed": "1" if result.completed else "0",
        "iterations": str(result.iterations),
        "tokens_in": str(result.tokens_in),
        "tokens_out": str(result.tokens_out),
    })

    return result


def _collect_touched(files: set[str], tc: ToolCall, cwd: str) -> None:
    """Record file paths touched by a destructive tool, for the diff feature."""
    if tc.name not in DESTRUCTIVE_TOOLS:
        return
    for key in ("path", "source", "dest"):
        p = tc.args.get(key)
        if isinstance(p, str):
            try:
                full = (Path(cwd) / p).resolve()
                files.add(str(full))
            except (OSError, ValueError):
                pass
