import os
import sys
import time
from pathlib import Path

import click
from rich.prompt import Confirm

from . import display
from . import config as cfg_module
from .models import get_adapter, list_models


def _resolve_run_params(model, provider, workdir):
    """Shared helper: resolve provider/model/cwd from args + config."""
    cfg = cfg_module.load()
    provider = provider or cfg.get("default_provider", "claude")
    model = model or cfg.get("default_model") or cfg_module.get_default_model_for_provider(provider)
    cwd = os.path.abspath(workdir or os.getcwd())
    return cfg, provider, model, cwd


# ── root group — bare invocation enters REPL ──────────────────────────────────

@click.group(invoke_without_command=True)
@click.option("--model", "-m", default=None, hidden=True)
@click.option("--provider", "-p", default=None, hidden=True)
@click.option("--dir", "-d", "workdir", default=None, hidden=True)
@click.pass_context
def main(ctx, model, provider, workdir):
    """Redtonomous — autonomous multi-model coding agent CLI.

    Run without a subcommand to enter interactive REPL mode.
    """
    if ctx.invoked_subcommand is not None:
        return  # a subcommand was given — let it handle things

    # ── REPL mode ──────────────────────────────────────────────────────────
    display.print_banner()
    cfg, provider, model, cwd = _resolve_run_params(model, provider, workdir)

    wake = cfg_module.get_wake_word(cfg) or "red"
    display.warn_autonomous(cwd, provider, model)
    display.print_info(
        f"Interactive mode — type your task and press Enter. "
        f"'exit' or Ctrl-C to quit. (wake word: [bold]{wake}[/bold])"
    )
    display.console.rule()

    try:
        adapter = get_adapter(provider, model, cfg)
    except (ValueError, Exception) as e:
        display.print_error(str(e))
        sys.exit(1)

    from .agent import run as agent_run
    from .repl_commands import dispatch_slash, REPLState

    state = REPLState(provider=provider, model=model, cwd=cwd, cfg=cfg)

    while True:
        try:
            display.print_repl_prompt(state.provider, state.model, state.cwd)
            task = input(f"{wake}> ").strip()
        except (EOFError, KeyboardInterrupt):
            display.console.print("\n[dim]Goodbye.[/dim]")
            break

        if not task:
            continue
        if task.lower() in ("exit", "quit", "q", ":q"):
            display.console.print("[dim]Goodbye.[/dim]")
            break

        # Slash commands (Claude-Code-style): /help, /clear, /resume, /init,
        # /model, /dir, /cost, /plans, /compact, plus user-defined under
        # ~/.redtonomous/commands/*.md
        if task.startswith("/"):
            handled = dispatch_slash(task, state)
            if handled is None:
                continue  # command processed inline, no agent run
            task = handled  # the slash command expanded into a regular task

        # If state changed (e.g. /model), rebuild the adapter.
        if state.provider != provider or state.model != model:
            try:
                adapter = get_adapter(state.provider, state.model, state.cfg)
                provider, model = state.provider, state.model
            except ValueError as e:
                display.print_error(str(e))
                continue

        agent_run(
            task=task,
            adapter=adapter,
            provider=state.provider,
            model=state.model,
            cwd=state.cwd,
            max_iterations=100,
            backup=False,
            log=True,
        )
        display.console.rule()


# ── run ───────────────────────────────────────────────────────────────────────

def _build_adapter(provider, model, cfg, fallback: str | None = None):
    """Construct an adapter, optionally wrapped in a ProviderChain."""
    primary = get_adapter(provider, model, cfg)
    if not fallback:
        return primary
    fallbacks = []
    for spec in [s.strip() for s in fallback.split(",") if s.strip()]:
        if ":" in spec:
            fp, fm = spec.split(":", 1)
        else:
            fp = spec
            fm = cfg_module.get_default_model_for_provider(fp)
        try:
            fallbacks.append(get_adapter(fp, fm, cfg))
        except ValueError as e:
            display.print_info(f"Fallback {fp}/{fm} skipped: {e}")
    if not fallbacks:
        return primary
    from .provider_chain import ProviderChain
    return ProviderChain(primary=primary, fallbacks=fallbacks)


def _split_csv(s: str | None) -> list[str] | None:
    if not s:
        return None
    return [x.strip() for x in s.split(",") if x.strip()]


# Extra options shared by ``run`` and the mode subcommands.
def _common_options(f):
    for decorator in reversed([
        click.option("--budget", "budget_usd", type=float, default=0.0,
                     help="Stop when accumulated cost reaches USD amount (0 = no cap)"),
        click.option("--max-hours", type=float, default=0.0,
                     help="Stop after this many wall-clock hours (0 = no cap)"),
        click.option("--dry-run", is_flag=True, default=False,
                     help="Stub destructive tools — no writes or shell execution"),
        click.option("--plan-first", is_flag=True, default=False,
                     help="Ask the model for a numbered plan and confirm before running"),
        click.option("--diff", "show_diff", is_flag=True, default=False,
                     help="After the run, git-diff files the agent touched"),
        click.option("--git-commit", "git_commit_msg", default=None,
                     help="If the run completes, run 'git commit -m <msg>' in cwd"),
        click.option("--git-branch", default=None,
                     help="Create + check out this branch in cwd before the run"),
        click.option("--tools", "tools_allow", default=None,
                     help="Comma-separated allow-list of tool names"),
        click.option("--no-tools", "tools_deny", default=None,
                     help="Comma-separated deny-list of tool names"),
        click.option("--fallback", default=None,
                     help="Comma list of provider[:model] failovers, e.g. openai:gpt-4o,gemini"),
        click.option("--style",
                     type=click.Choice(["default", "concise", "verbose", "json"]),
                     default="default", show_default=True,
                     help="Response style"),
        click.option("--sandbox",
                     type=click.Choice(["full", "workdir", "readonly"]),
                     default="full", show_default=True,
                     help="full = all tools; readonly = remove destructive tools"),
        click.option("--test", "test_cmd", default=None,
                     help="Run this command after the model declares done; "
                          "on non-zero exit the model is asked to fix.")
        ,
        click.option("--repo-map", is_flag=True, default=False,
                     help="Inject an Aider-style repo map into the system prompt"),
        click.option("--with-url", "with_url", multiple=True,
                     help="Fetch URL(s) and inject contents as context (repeatable)"),
        click.option("--image", "image_paths", multiple=True,
                     type=click.Path(exists=True, dir_okay=False),
                     help="Attach an image to the first message (repeatable)"),
        click.option("--architect", default=None,
                     help="Use this 'provider[:model]' for the planning step "
                          "before the editor model executes"),
        click.option("--worktree", is_flag=True, default=False,
                     help="Run inside a fresh git worktree; merge back on success"),
        click.option("--notify/--no-notify", default=False,
                     help="Fire a desktop notification when the task completes"),
    ]):
        f = decorator(f)
    return f


@main.command()
@click.argument("task")
@click.option("--model", "-m", default=None, help="Model ID override")
@click.option("--provider", "-p", default=None, help="Provider override")
@click.option("--dir", "-d", "workdir", default=None, help="Working directory (default: cwd)")
@click.option("--backup/--no-backup", default=True, show_default=True, help="Auto-backup before run")
@click.option("--max-iter", default=100, show_default=True, help="Max tool-call iterations")
@click.option("--log/--no-log", default=True, show_default=True, help="Save session log")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation prompt")
@click.option("--resume", "resume_id", default=None,
              help="Resume from a prior session log")
@_common_options
def run(task, model, provider, workdir, backup, max_iter, log, yes, resume_id,
        budget_usd, max_hours, dry_run, plan_first, show_diff, git_commit_msg,
        git_branch, tools_allow, tools_deny, fallback,
        style, sandbox, test_cmd, repo_map, with_url, image_paths,
        architect, worktree, notify):
    """Run TASK autonomously using the configured model."""
    display.print_banner()

    cfg, provider, model, cwd = _resolve_run_params(model, provider, workdir)

    # Worktree isolation: spawn a fresh git worktree off HEAD and run there.
    cleanup_wt = None
    if worktree:
        cwd, cleanup_wt = _make_worktree(cwd)
        display.print_info(f"Running inside worktree: {cwd}")

    display.warn_autonomous(cwd, provider, model)

    if not yes:
        if not Confirm.ask("[yellow]Proceed?[/yellow]", default=True):
            display.print_info("Aborted.")
            sys.exit(0)

    try:
        adapter = _build_adapter(provider, model, cfg, fallback=fallback)
        architect_adapter = _maybe_architect(architect, cfg)
    except ValueError as e:
        display.print_error(str(e))
        sys.exit(1)

    resumed = None
    if resume_id:
        from .agent import load_resume
        try:
            resumed = load_resume(resume_id)
            display.print_info(f"Resuming session {resume_id} ({len(resumed.get('log', []))} prior steps)")
        except FileNotFoundError as e:
            display.print_error(str(e))
            sys.exit(1)

    # Desktop notification = a synthetic on_done hook for this run.
    if notify:
        _install_notify_hook()

    from .agent import run as agent_run
    result = agent_run(
        task=task, adapter=adapter, provider=provider, model=model, cwd=cwd,
        max_iterations=max_iter, backup=backup, log=log, resume=resumed,
        yes=yes, budget_usd=budget_usd, max_hours=max_hours, dry_run=dry_run,
        plan_first=plan_first, diff=show_diff, git_commit_msg=git_commit_msg,
        git_branch=git_branch,
        tools_allow=_split_csv(tools_allow), tools_deny=_split_csv(tools_deny),
        style=style, sandbox=sandbox, test_cmd=test_cmd,
        include_repo_map=repo_map,
        extra_urls=list(with_url) if with_url else None,
        image_paths=list(image_paths) if image_paths else None,
        architect=architect_adapter,
    )
    if cleanup_wt:
        cleanup_wt(success=result.completed)
    sys.exit(result.exit_code)


def _maybe_architect(spec: str | None, cfg: dict):
    """Build a planning adapter from a 'provider[:model]' string."""
    if not spec:
        return None
    if ":" in spec:
        p, m = spec.split(":", 1)
    else:
        p, m = spec, cfg_module.get_default_model_for_provider(spec)
    try:
        return get_adapter(p, m, cfg)
    except ValueError as e:
        display.print_info(f"Architect adapter unavailable: {e}")
        return None


def _make_worktree(cwd: str):
    """Create a fresh git worktree off HEAD; return (worktree_path, cleanup_fn).

    The cleanup function removes the worktree after the run unless
    ``success=True`` is passed, in which case the caller is responsible for
    merging the changes back. We print the worktree path so the user can
    inspect and merge manually.
    """
    import subprocess
    import tempfile

    if not os.path.isdir(os.path.join(cwd, ".git")):
        display.print_info("Not a git repo — skipping --worktree.")
        return cwd, None
    tmp = tempfile.mkdtemp(prefix="redtonomous-wt-")
    proc = subprocess.run(
        ["git", "-C", cwd, "worktree", "add", "--detach", tmp],
        capture_output=True, text=True,
    )
    if proc.returncode != 0:
        display.print_info(f"worktree add failed: {proc.stderr.strip()} — running in cwd instead")
        return cwd, None

    def _cleanup(success: bool) -> None:
        if success:
            display.print_info(f"Worktree kept at {tmp}.  Inspect + merge: cd {tmp}")
            return
        try:
            subprocess.run(
                ["git", "-C", cwd, "worktree", "remove", "--force", tmp],
                capture_output=True, text=True, check=False,
            )
        except OSError:
            pass

    return tmp, _cleanup


def _install_notify_hook() -> None:
    """Wire up a temporary on_done hook that fires a desktop notification."""
    import platform
    import json as _json
    from . import modes
    hooks_file = Path(modes._hooks_path())  # pylint: disable=protected-access
    existing: dict = {}
    if hooks_file.exists():
        try:
            existing = _json.loads(hooks_file.read_text())
        except (OSError, _json.JSONDecodeError):
            existing = {}
    sys_name = platform.system()
    if sys_name == "Darwin":
        existing["on_done"] = 'osascript -e "display notification \\"Redtonomous task done\\" with title \\"Redtonomous\\""'
    elif sys_name == "Linux":
        existing["on_done"] = 'command -v notify-send >/dev/null && notify-send Redtonomous "Task done"'
    else:
        existing["on_done"] = 'echo "[notify] Redtonomous task done"'
    hooks_file.parent.mkdir(parents=True, exist_ok=True)
    hooks_file.write_text(_json.dumps(existing, indent=2))


# ── moonlight ─────────────────────────────────────────────────────────────────

@main.command()
@click.argument("task")
@click.option("--model", "-m", default=None)
@click.option("--provider", "-p", default=None)
@click.option("--dir", "-d", "workdir", default=None)
@click.option("--max-iter", default=1000, show_default=True)
@click.option("--max-hours", type=float, default=8.0, show_default=True,
              help="Hard wall-clock cap. The run will halt cleanly when reached.")
@click.option("--budget", "budget_usd", type=float, default=50.0, show_default=True,
              help="Stop when accumulated cost reaches USD amount")
@click.option("--checkpoint-every", default=30, show_default=True,
              help="Persist checkpoint every N iterations")
@click.option("--heartbeat-min", "heartbeat_min", default=5.0, show_default=True,
              help="Heartbeat status line every N minutes")
@click.option("--fallback", default=None,
              help="Comma list of provider[:model] failovers for rate-limit drops")
@click.option("--resume", "resume_id", default=None)
def moonlight(task, model, provider, workdir, max_iter, max_hours, budget_usd,
              checkpoint_every, heartbeat_min, fallback, resume_id):
    """Overnight long-run mode: heartbeat, checkpoints, auto-retry, hard cap."""
    display.print_banner()
    cfg, provider, model, cwd = _resolve_run_params(model, provider, workdir)

    display.print_info(
        f"[moonlight] iter≤{max_iter} cap={max_hours}h budget=${budget_usd:.2f} "
        f"checkpoint every {checkpoint_every} iter"
    )

    try:
        adapter = _build_adapter(provider, model, cfg, fallback=fallback)
    except ValueError as e:
        display.print_error(str(e))
        sys.exit(1)

    resumed = None
    if resume_id:
        from .agent import load_resume
        try:
            resumed = load_resume(resume_id)
        except FileNotFoundError as e:
            display.print_error(str(e))
            sys.exit(1)

    from .agent import run as agent_run
    result = agent_run(
        task=task, adapter=adapter, provider=provider, model=model, cwd=cwd,
        max_iterations=max_iter, backup=True, log=True, resume=resumed,
        yes=True, budget_usd=budget_usd, max_hours=max_hours,
        retry_transient=10,
        heartbeat_period_s=float(heartbeat_min) * 60.0,
        checkpoint_every=checkpoint_every,
    )
    sys.exit(result.exit_code)


# ── red ───────────────────────────────────────────────────────────────────────

_RED_BANNER = """\
[bold red]
╔══════════════════════════════════════════════════════════════════╗
║   ░█▀█░█▀▀░█▀▄░░░░█▄█░█▀█░█▀▄░█▀▀                                ║
║   ░█▀▄░█▀▀░█░█░░░░█░█░█░█░█░█░█▀▀                                ║
║   ░▀░▀░▀▀▀░▀▀░░░░░▀░▀░▀▀▀░▀▀░░▀▀▀                                ║
║                                                                  ║
║   No guardrails. No prompts. No backup. No undo.                 ║
║                                                                  ║
║   Hit Ctrl-C in the next 5 seconds to abort.                     ║
╚══════════════════════════════════════════════════════════════════╝
[/bold red]"""


@main.command()
@click.argument("task")
@click.option("--model", "-m", default=None)
@click.option("--provider", "-p", default=None)
@click.option("--dir", "-d", "workdir", default=None)
@click.option("--max-iter", default=200, show_default=True)
@click.option("--max-hours", type=float, default=2.0, show_default=True)
@click.option("--budget", "budget_usd", type=float, default=20.0, show_default=True)
@click.option("--fallback", default=None)
def red(task, model, provider, workdir, max_iter, max_hours, budget_usd, fallback):
    """Dangerous-bypass mode. Disables prompts, backups, and the dangerous-command gate."""
    if os.environ.get("REDTONOMOUS_I_KNOW_WHAT_IM_DOING") != "1":
        display.print_error(
            "Refusing to run in /red mode without REDTONOMOUS_I_KNOW_WHAT_IM_DOING=1.\n"
            "This mode bypasses every safety. Set the env var if you really mean it."
        )
        sys.exit(1)

    display.console.print(_RED_BANNER)
    # Forensics: log every red-mode invocation.
    try:
        red_log = cfg_module.CONFIG_DIR / "red.log"
        cfg_module.CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        with open(red_log, "a") as f:
            from datetime import datetime as _dt
            f.write(f"{_dt.utcnow().isoformat()}Z task={task!r}\n")
    except OSError:
        pass

    if sys.stdout.isatty() and not os.environ.get("REDTONOMOUS_SKIP_COUNTDOWN"):
        for n in range(5, 0, -1):
            display.console.print(f"[red bold]Starting in {n}…[/red bold]")
            time.sleep(1)

    # Make sure the dangerous-command gate is OFF inside this process.
    os.environ.pop("REDTONOMOUS_CONFIRM_DANGEROUS", None)

    cfg, provider, model, cwd = _resolve_run_params(model, provider, workdir)
    try:
        adapter = _build_adapter(provider, model, cfg, fallback=fallback)
    except ValueError as e:
        display.print_error(str(e))
        sys.exit(1)

    from .agent import run as agent_run
    result = agent_run(
        task=task, adapter=adapter, provider=provider, model=model, cwd=cwd,
        max_iterations=max_iter, backup=False, log=True,
        yes=True, budget_usd=budget_usd, max_hours=max_hours,
    )
    sys.exit(result.exit_code)


# ── goal ──────────────────────────────────────────────────────────────────────

@main.command()
@click.argument("criteria")
@click.option("--model", "-m", default=None)
@click.option("--provider", "-p", default=None)
@click.option("--dir", "-d", "workdir", default=None)
@click.option("--max-iter", default=100, show_default=True)
@click.option("--max-retries", default=5, show_default=True,
              help="Re-prompts after a judge says 'not achieved'")
@click.option("--max-hours", type=float, default=1.0, show_default=True)
@click.option("--budget", "budget_usd", type=float, default=20.0, show_default=True)
@click.option("--judge-provider", default=None,
              help="Provider used for the acceptance judge (default: same as agent)")
@click.option("--judge-model", default=None)
@click.option("--threshold", type=float, default=0.7, show_default=True,
              help="Judge confidence required to accept")
def goal(criteria, model, provider, workdir, max_iter, max_retries, max_hours,
         budget_usd, judge_provider, judge_model, threshold):
    """Goal-seeking mode: re-prompt until a judge says the criteria are met."""
    display.print_banner()
    cfg, provider, model, cwd = _resolve_run_params(model, provider, workdir)
    judge_p = judge_provider or provider
    judge_m = judge_model or model

    try:
        adapter = get_adapter(provider, model, cfg)
        judge_adapter = get_adapter(judge_p, judge_m, cfg)
    except ValueError as e:
        display.print_error(str(e))
        sys.exit(1)

    from .agent import run as agent_run
    from .judge import evaluate

    display.print_info(f"[goal] judge={judge_p}/{judge_m}  threshold={threshold}")
    task = criteria
    feedback = ""
    last_verdict = None

    for attempt in range(1, max_retries + 1):
        display.console.rule(f"[bold]Goal attempt {attempt}/{max_retries}[/bold]")
        prompt = task if not feedback else f"{task}\n\nPrevious attempt was missing: {feedback}"
        result = agent_run(
            task=prompt, adapter=adapter, provider=provider, model=model, cwd=cwd,
            max_iterations=max_iter, backup=(attempt == 1), log=True,
            yes=True, budget_usd=budget_usd, max_hours=max_hours,
        )
        if result.exit_code in (3, 124):  # budget or wallclock
            sys.exit(result.exit_code)

        # Condense the trace for the judge.
        trace_lines = [f"FINAL: {result.final_text[:1000]}"]
        for step in result.session_log[-12:]:
            trace_lines.append(
                f"  iter {step['iter']} {step['tool']} "
                f"→ {'error' if step.get('error') else 'ok'}: {step.get('result','')[:160]}"
            )
        verdict = evaluate(criteria, "\n".join(trace_lines), judge_adapter)
        last_verdict = verdict
        display.print_info(
            f"[judge] achieved={verdict.achieved} confidence={verdict.confidence:.2f} "
            f"missing={verdict.missing or '—'}"
        )
        if verdict.achieved and verdict.confidence >= threshold:
            display.print_final(f"Goal achieved on attempt {attempt}.")
            sys.exit(0)
        feedback = verdict.missing or "(no specific reason)"

    display.print_error(
        f"Goal NOT achieved after {max_retries} attempts. "
        f"Last verdict: {last_verdict.missing if last_verdict else '—'}"
    )
    sys.exit(2)


# ── undo ──────────────────────────────────────────────────────────────────────

@main.command()
@click.option("--dir", "-d", "workdir", default=None,
              help="Working directory whose latest backup should be restored (default: cwd)")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation")
def undo(workdir, yes):
    """Restore the most recent backup directory for the given working dir.

    Backups are created by ``redtonomous run`` (when --backup is on) as
    ``<cwd>_backup_<ts>``. This subcommand finds the newest one matching the
    cwd and overwrites the cwd with its contents.
    """
    import glob
    import shutil

    cwd = os.path.abspath(workdir or os.getcwd())
    pattern = f"{cwd.rstrip('/')}_backup_*"
    candidates = sorted(glob.glob(pattern))
    if not candidates:
        display.print_error(f"No backup directory found matching {pattern}")
        sys.exit(1)
    latest = candidates[-1]
    display.print_info(f"Latest backup: {latest}")
    if not yes:
        if not Confirm.ask(f"Restore {latest} → {cwd}? Files will be overwritten", default=False):
            display.print_info("Aborted.")
            sys.exit(0)
    # Copy each entry from the backup over the cwd. We don't blow away the cwd
    # itself — that would invalidate the user's terminal and any open
    # editor's working directory.
    for entry in os.listdir(latest):
        src = os.path.join(latest, entry)
        dst = os.path.join(cwd, entry)
        if os.path.isdir(src):
            if os.path.exists(dst):
                shutil.rmtree(dst)
            shutil.copytree(src, dst)
        else:
            shutil.copy2(src, dst)
    display.print_info(f"Restored from {latest}")


# ── config ────────────────────────────────────────────────────────────────────

@main.group()
def config():
    """Manage configuration and API keys."""


@config.command("set-key")
@click.argument("provider")
@click.argument("key")
def config_set_key(provider, key):
    """Store an API key for PROVIDER."""
    cfg = cfg_module.load()
    cfg.setdefault("providers", {}).setdefault(provider, {})["api_key"] = key
    cfg_module.save(cfg)
    display.print_info(f"API key saved for '{provider}'.")


@config.command("set-model")
@click.argument("model")
@click.option("--provider", "-p", default=None)
def config_set_model(model, provider):
    """Set the default model (and optionally provider)."""
    cfg = cfg_module.load()
    cfg["default_model"] = model
    if provider:
        cfg["default_provider"] = provider
    cfg_module.save(cfg)
    display.print_info(f"Default model set to '{model}'.")


@config.command("set-wake-word")
@click.argument("word")
def config_set_wake_word(word):
    """Set the wake word used in REPL mode and shell-setup."""
    if not word.isidentifier():
        display.print_error(
            f"'{word}' is not a valid shell identifier. Use letters, digits, and underscores only."
        )
        sys.exit(1)
    cfg = cfg_module.load()
    cfg["wake_word"] = word
    cfg_module.save(cfg)
    display.print_info(
        f"Wake word set to '[bold]{word}[/bold]'. "
        f"Run 'redtonomous shell-setup' to get your shell function."
    )


@config.command("add-provider")
@click.argument("name")
@click.argument("base_url")
@click.option("--key", default="none", help="API key (use 'none' for local providers)")
@click.option("--default-model", default="default")
def config_add_provider(name, base_url, key, default_model):
    """Add a custom OpenAI-compatible provider."""
    cfg = cfg_module.load()
    cfg.setdefault("providers", {})[name] = {
        "type": "openai-compat",
        "base_url": base_url,
        "api_key": key,
        "default_model": default_model,
    }
    cfg_module.save(cfg)
    display.print_info(f"Provider '{name}' added (base_url={base_url}).")


@config.command("show")
def config_show():
    """Print current configuration (masks API keys)."""
    import json
    cfg = cfg_module.load()
    for pdata in cfg.get("providers", {}).values():
        if "api_key" in pdata and pdata["api_key"] not in ("none", "", None):
            pdata["api_key"] = pdata["api_key"][:8] + "…"
    display.console.print_json(json.dumps(cfg, indent=2))


# ── models ────────────────────────────────────────────────────────────────────

@main.command()
def models():
    """List all known models grouped by provider."""
    display.models_table(list_models())


# ── shell-setup ───────────────────────────────────────────────────────────────

@main.command("shell-setup")
@click.option("--shell", "shell_name", default=None,
              type=click.Choice(["bash", "zsh", "fish", "pwsh"], case_sensitive=False),
              help="Target shell (default: auto-detect from $SHELL)")
@click.option("--wake-word", "wake_word_override", default=None,
              help="Override the configured wake word")
@click.option("--write", is_flag=True,
              help="Append the function directly to your shell rc file")
def shell_setup(shell_name, wake_word_override, write):
    """Print (or install) the shell function for your wake word.

    After running this, source your shell config or open a new terminal.
    Then just type:  <wake_word> build me a FastAPI app
    """
    cfg = cfg_module.load()
    wake = wake_word_override or cfg_module.get_wake_word(cfg)

    if not wake:
        display.print_error(
            "No wake word configured. Run: redtonomous config set-wake-word <word>"
        )
        sys.exit(1)

    # Auto-detect shell from $SHELL env var
    if not shell_name:
        shell_env = os.environ.get("SHELL", "")
        if "fish" in shell_env:
            shell_name = "fish"
        elif "zsh" in shell_env:
            shell_name = "zsh"
        elif "pwsh" in shell_env or "powershell" in shell_env.lower():
            shell_name = "pwsh"
        else:
            shell_name = "bash"

    # Generate the function body
    snippets = {
        "bash": (
            f'# Redtonomous wake word — add to ~/.bashrc\n'
            f'{wake}() {{\n'
            f'  redtonomous run "$@"\n'
            f'}}'
        ),
        "zsh": (
            f'# Redtonomous wake word — add to ~/.zshrc\n'
            f'{wake}() {{\n'
            f'  redtonomous run "$@"\n'
            f'}}'
        ),
        "fish": (
            f'# Redtonomous wake word — add to ~/.config/fish/functions/{wake}.fish\n'
            f'function {wake}\n'
            f'  redtonomous run $argv\n'
            f'end'
        ),
        "pwsh": (
            f'# Redtonomous wake word — add to $PROFILE\n'
            f'function {wake} {{ redtonomous run @args }}'
        ),
    }

    rc_files = {
        "bash": "~/.bashrc",
        "zsh":  "~/.zshrc",
        "fish": f"~/.config/fish/functions/{wake}.fish",
        "pwsh": "$PROFILE",
    }

    snippet = snippets[shell_name]
    rc_file = rc_files[shell_name]

    display.console.print(f"\n[bold]Wake word:[/bold] [bold red]{wake}[/bold red]  "
                          f"[dim]({shell_name})[/dim]\n")
    display.console.print(f"[dim]Add this to [bold]{rc_file}[/bold]:[/dim]\n")
    display.console.print(f"[green]{snippet}[/green]\n")

    if write:
        _write_snippet(shell_name, wake, snippet, rc_file)
    else:
        source_cmd = f"source {rc_file}" if shell_name != "fish" else f"source {rc_file}"
        display.print_info(
            f"Then run: [bold]{source_cmd}[/bold] (or open a new terminal)\n"
            f"After that: [bold red]{wake}[/bold red] build me a FastAPI app"
        )


def _write_snippet(shell_name: str, wake: str, snippet: str, rc_file: str) -> None:
    import shutil

    if shell_name == "fish":
        fish_dir = os.path.expanduser("~/.config/fish/functions")
        os.makedirs(fish_dir, exist_ok=True)
        target = os.path.join(fish_dir, f"{wake}.fish")
    else:
        target = os.path.expanduser(rc_file)

    marker_start = f"# >>> redtonomous wake word ({wake}) >>>"
    marker_end   = f"# <<< redtonomous wake word ({wake}) <<<"
    block = f"\n{marker_start}\n{snippet}\n{marker_end}\n"

    if os.path.exists(target):
        content = open(target).read()
        if marker_start in content:
            # Already installed — update in place
            import re
            content = re.sub(
                rf"{re.escape(marker_start)}.*?{re.escape(marker_end)}",
                block.strip(),
                content,
                flags=re.DOTALL,
            )
            open(target, "w").write(content)
            display.print_info(f"Updated wake word in {target}")
            return
        # Back up before appending
        shutil.copy(target, target + ".bak")

    with open(target, "a") as f:
        f.write(block)

    display.print_info(f"Written to {target} (backup at {target}.bak if it existed)")
    if shell_name != "fish":
        display.print_info(f"Run: source {target}")


# ── auth ──────────────────────────────────────────────────────────────────────

@main.command()
def auth():
    """OAuth login for Claude (coming soon)."""
    display.print_info("OAuth login is on the roadmap. Use 'config set-key claude <key>' for now.")


# ── init ──────────────────────────────────────────────────────────────────────

@main.command()
@click.option("--dir", "-d", "workdir", default=None,
              help="Project directory (default: cwd)")
def init(workdir):
    """Generate a REDTONOMOUS.md memory file for the current project.

    The agent auto-reads this file on every run in the same directory.
    """
    from .repl_commands import _do_init
    cwd = os.path.abspath(workdir or os.getcwd())
    _do_init(cwd)


# ── chat (no agent loop) ──────────────────────────────────────────────────────

@main.command()
@click.option("--model", "-m", default=None)
@click.option("--provider", "-p", default=None)
def chat(model, provider):
    """Plain back-and-forth chat with the model (no tools, no loop).

    Like Aider's ``/ask`` or Claude's web chat. Useful for design discussions
    where you don't want the agent touching files.
    """
    cfg, provider, model, cwd = _resolve_run_params(model, provider, None)
    try:
        adapter = get_adapter(provider, model, cfg)
    except ValueError as e:
        display.print_error(str(e))
        sys.exit(1)
    display.print_info(f"chat mode — {provider}/{model}   (Ctrl-D to exit)")
    history: list[dict] = []
    while True:
        try:
            line = input("you> ").strip()
        except (EOFError, KeyboardInterrupt):
            display.console.print()
            break
        if not line:
            continue
        if line.lower() in ("exit", "quit", ":q"):
            break
        history.append({"role": "user", "content": line})
        try:
            resp = adapter.chat(messages=history, tools=[], system="You are a helpful coding assistant.")
        except Exception as e:
            display.print_error(str(e))
            continue
        display.console.print(f"[bold]{provider}[/bold]> {resp.text}")
        history.append({"role": "assistant", "content": resp.text or ""})


# ── review (git diff review) ──────────────────────────────────────────────────

def _capture_git_diff(cwd: str, ref: str | None) -> str:
    import subprocess
    args = ["git", "-C", cwd, "diff"]
    if ref:
        args.append(ref)
    try:
        proc = subprocess.run(args, capture_output=True, text=True, timeout=30)
    except OSError as e:
        return f"(could not run git diff: {e})"
    return proc.stdout or "(no diff)"


@main.command()
@click.option("--dir", "-d", "workdir", default=None)
@click.option("--ref", default=None,
              help="Diff this ref vs HEAD (e.g. origin/main); omitted = unstaged changes")
@click.option("--model", "-m", default=None)
@click.option("--provider", "-p", default=None)
def review(workdir, ref, model, provider):
    """Send the current git diff to the model and print a code review."""
    cfg, provider, model, cwd = _resolve_run_params(model, provider, workdir)
    diff_text = _capture_git_diff(cwd, ref)
    if "(no diff)" in diff_text or not diff_text.strip():
        display.print_info("Nothing to review — no diff.")
        return
    try:
        adapter = get_adapter(provider, model, cfg)
    except ValueError as e:
        display.print_error(str(e))
        sys.exit(1)
    resp = adapter.chat(
        messages=[{"role": "user", "content": f"Review this diff:\n\n{diff_text[:80000]}"}],
        tools=[],
        system=(
            "You are a senior code reviewer. Be terse. Focus on correctness, "
            "security, and obvious regressions. Skip style nits unless they "
            "affect behavior. Quote file:line when you call something out."
        ),
    )
    display.console.print(resp.text or "(no review produced)")


# ── bug finder ───────────────────────────────────────────────────────────────

@main.command()
@click.option("--dir", "-d", "workdir", default=None)
@click.option("--ref", default=None)
@click.option("--model", "-m", default=None)
@click.option("--provider", "-p", default=None)
def bug(workdir, ref, model, provider):
    """Send the current git diff to the model and ask for bugs only."""
    cfg, provider, model, cwd = _resolve_run_params(model, provider, workdir)
    diff_text = _capture_git_diff(cwd, ref)
    if "(no diff)" in diff_text or not diff_text.strip():
        display.print_info("Nothing to inspect — no diff.")
        return
    try:
        adapter = get_adapter(provider, model, cfg)
    except ValueError as e:
        display.print_error(str(e))
        sys.exit(1)
    resp = adapter.chat(
        messages=[{"role": "user", "content": f"Find bugs in this diff:\n\n{diff_text[:80000]}"}],
        tools=[],
        system=(
            "You are a bug-hunting reviewer. Output ONLY a numbered list of "
            "concrete bugs with file:line and severity (CRIT / HIGH / MED / LOW). "
            "If you cannot find any real bugs, say 'No bugs found.' exactly."
        ),
    )
    display.console.print(resp.text or "(no bugs reported)")


# ── plans ─────────────────────────────────────────────────────────────────────

@main.command()
def plans():
    """Print the subscription plan catalog (same data as the /plans API)."""
    from .repl_commands import _print_plans
    _print_plans()


# ── completion (shell completion script) ─────────────────────────────────────

@main.command()
@click.argument("shell", type=click.Choice(["bash", "zsh", "fish"]))
def completion(shell):
    """Print the shell-completion script for SHELL.

    Install it like Claude Code / Aider:
        eval "$(redtonomous completion bash)"
    or pipe to a file in your completion dir.
    """
    # Click ships completion via an env var trick — we just print the eval
    # form for each shell.
    snippets = {
        "bash": 'eval "$(_REDTONOMOUS_COMPLETE=bash_source redtonomous)"',
        "zsh":  'eval "$(_REDTONOMOUS_COMPLETE=zsh_source redtonomous)"',
        "fish": '_REDTONOMOUS_COMPLETE=fish_source redtonomous | source',
    }
    display.console.print(snippets[shell])


if __name__ == "__main__":
    main()
