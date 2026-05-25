"""Slash-command dispatch for the REPL — inspired by Claude Code, Aider,
and Continue.dev.

Built-in commands:
    /help                — print this list
    /clear               — reset the screen (a fresh session)
    /compact             — summarise recent turns to free up context (stub)
    /resume <id>         — replay a prior session
    /init                — generate REDTONOMOUS.md for this project
    /model <m>           — change the active model (provider auto-resolved)
    /provider <p>        — change the active provider
    /dir <path>          — change the working directory
    /cost                — print known pricing for the active model
    /plans               — print the subscription plan catalog
    /exit                — quit the REPL

Custom commands: any markdown file in ``~/.redtonomous/commands/<name>.md``
becomes ``/<name>`` and expands to the file's contents (with ``{args}``
substituted from anything after the command name).
"""
from __future__ import annotations

import os
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from . import config as cfg_module
from . import display

COMMANDS_DIR = Path.home() / ".redtonomous" / "commands"

# Returning ``None`` from a slash handler means "I handled this inline, do not
# pass anything to the agent." Returning a string means "treat this string as
# a new task and run the agent with it." Returning the original input is a
# no-op.


@dataclass
class REPLState:
    provider: str
    model: str
    cwd: str
    cfg: dict[str, Any] = field(default_factory=dict)


def _print_help() -> None:
    lines = [
        "[bold]Built-in commands[/bold]",
        "  /help              show this list",
        "  /clear             clear the screen",
        "  /compact           hint that the next turn should summarise",
        "  /resume <id>       resume a previous session",
        "  /init              generate REDTONOMOUS.md for this project",
        "  /model <id>        change the active model",
        "  /provider <id>     change the active provider",
        "  /dir <path>        change the working directory",
        "  /cost              show pricing for the active model",
        "  /plans             show the plan catalog",
        "  /exit              quit",
        "",
        "[bold]Custom commands[/bold]",
        f"  Place markdown in {COMMANDS_DIR}/<name>.md → /<name>",
    ]
    for ln in lines:
        display.console.print(ln)


def _list_custom() -> list[str]:
    if not COMMANDS_DIR.exists():
        return []
    return sorted(p.stem for p in COMMANDS_DIR.glob("*.md"))


def _print_plans() -> None:
    from .plans import PLANS
    for p in PLANS:
        badge = f" ({p.badge})" if p.badge else ""
        display.console.print(
            f"  [bold]{p.id:<8}[/bold]  ${p.price_usd:>6.0f}/{p.period}  {p.name}{badge}"
        )
        display.console.print(f"    [dim]{p.tagline}[/dim]")


def _print_cost(state: REPLState) -> None:
    from .modes import price_for, UNKNOWN_PRICE
    p_in, p_out = price_for(state.model)
    if (p_in, p_out) == UNKNOWN_PRICE:
        display.print_info(
            f"{state.model}: pricing unknown — falling back to "
            f"Opus-tier (${p_in}/${p_out} per MTok)"
        )
    else:
        display.print_info(f"{state.model}: ${p_in} in / ${p_out} out per MTok")


def _do_init(cwd: str) -> None:
    target = Path(cwd) / "REDTONOMOUS.md"
    if target.exists():
        display.print_info(f"{target} already exists — leaving it alone.")
        return
    body = _DEFAULT_MEMORY_TEMPLATE.format(name=Path(cwd).name)
    target.write_text(body)
    display.print_info(f"Wrote {target} — Redtonomous will read it on every run in this directory.")


_DEFAULT_MEMORY_TEMPLATE = """\
# Redtonomous memory for `{name}`

This file is auto-loaded by every `redtonomous` invocation in this directory.

## Project overview

(One paragraph: what is this codebase?)

## Conventions

- Language(s):
- Test command:
- Lint command:
- Style guide: (link or notes)

## What to avoid

- (Anything the agent should NOT touch)

## Useful entry points

- (Important files / modules)
"""


def _do_resume(args: str, state: REPLState) -> str | None:
    if not args:
        display.print_error("/resume requires a session id")
        return None
    from .agent import load_resume
    try:
        data = load_resume(args)
    except FileNotFoundError as e:
        display.print_error(str(e))
        return None
    display.print_info(f"Resuming session ({len(data.get('log', []))} prior steps)")
    return data.get("task", "Continue from where the previous session stopped.")


def _do_compact() -> None:
    # Real compaction would summarise the running conversation; the REPL
    # spawns a fresh agent.run per turn so there's nothing to compact here
    # beyond clearing the screen.
    if shutil.which("clear"):
        os.system("clear")
    display.print_info("Context already starts fresh on every REPL turn.")


def dispatch_slash(line: str, state: REPLState) -> str | None:
    """Handle a ``/...`` REPL command.

    Returns:
        * ``None``   — command was handled inline; do NOT run the agent.
        * a string   — treat the return value as the agent's next task.
    """
    parts = line[1:].split(maxsplit=1)
    if not parts:
        return None
    cmd = parts[0].lower()
    args = parts[1].strip() if len(parts) > 1 else ""

    if cmd in ("help", "?"):
        _print_help()
        custom = _list_custom()
        if custom:
            display.console.print("")
            display.console.print("[bold]Your custom commands[/bold]")
            for name in custom:
                display.console.print(f"  /{name}")
        return None

    if cmd == "exit" or cmd == "quit":
        raise SystemExit(0)

    if cmd == "clear":
        if shutil.which("clear"):
            os.system("clear")
        return None

    if cmd == "compact":
        _do_compact()
        return None

    if cmd == "resume":
        return _do_resume(args, state)

    if cmd == "init":
        _do_init(state.cwd)
        return None

    if cmd == "model":
        if not args:
            display.print_info(f"Active model: {state.model}")
            return None
        state.model = args
        display.print_info(f"Switched model → {args}")
        return None

    if cmd == "provider":
        if not args:
            display.print_info(f"Active provider: {state.provider}")
            return None
        state.provider = args
        # Apply provider default model if the current model isn't a fit.
        state.model = cfg_module.get_default_model_for_provider(args)
        display.print_info(f"Switched provider → {args} ({state.model})")
        return None

    if cmd == "dir":
        if not args:
            display.print_info(f"Working dir: {state.cwd}")
            return None
        new_cwd = os.path.abspath(os.path.expanduser(args))
        if not os.path.isdir(new_cwd):
            display.print_error(f"Not a directory: {new_cwd}")
            return None
        state.cwd = new_cwd
        display.print_info(f"Switched cwd → {new_cwd}")
        return None

    if cmd == "cost":
        _print_cost(state)
        return None

    if cmd == "plans":
        _print_plans()
        return None

    # Custom command: ~/.redtonomous/commands/<cmd>.md
    custom_file = COMMANDS_DIR / f"{cmd}.md"
    if custom_file.is_file():
        try:
            template = custom_file.read_text(errors="replace")
        except OSError as e:
            display.print_error(f"Could not read {custom_file}: {e}")
            return None
        # ``{args}`` placeholder is substituted with the trailing string.
        return template.replace("{args}", args)

    display.print_error(f"Unknown command: /{cmd}  (try /help)")
    return None
