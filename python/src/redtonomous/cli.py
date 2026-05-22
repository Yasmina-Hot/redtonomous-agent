import os
import sys

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

    while True:
        try:
            display.print_repl_prompt(provider, model, cwd)
            task = input(f"{wake}> ").strip()
        except (EOFError, KeyboardInterrupt):
            display.console.print("\n[dim]Goodbye.[/dim]")
            break

        if not task:
            continue
        if task.lower() in ("exit", "quit", "q", ":q"):
            display.console.print("[dim]Goodbye.[/dim]")
            break

        agent_run(
            task=task,
            adapter=adapter,
            provider=provider,
            model=model,
            cwd=cwd,
            max_iterations=100,
            backup=False,   # no backup per-task in REPL — would spam backups
            log=True,
        )
        display.console.rule()


# ── run ───────────────────────────────────────────────────────────────────────

@main.command()
@click.argument("task")
@click.option("--model", "-m", default=None, help="Model ID override")
@click.option("--provider", "-p", default=None, help="Provider override")
@click.option("--dir", "-d", "workdir", default=None, help="Working directory (default: cwd)")
@click.option("--backup/--no-backup", default=True, show_default=True, help="Auto-backup before run")
@click.option("--max-iter", default=100, show_default=True, help="Max tool-call iterations")
@click.option("--log/--no-log", default=True, show_default=True, help="Save session log")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation prompt")
def run(task, model, provider, workdir, backup, max_iter, log, yes):
    """Run TASK autonomously using the configured model."""
    display.print_banner()

    cfg, provider, model, cwd = _resolve_run_params(model, provider, workdir)

    display.warn_autonomous(cwd, provider, model)

    if not yes:
        if not Confirm.ask("[yellow]Proceed?[/yellow]", default=True):
            display.print_info("Aborted.")
            sys.exit(0)

    try:
        adapter = get_adapter(provider, model, cfg)
    except ValueError as e:
        display.print_error(str(e))
        sys.exit(1)

    from .agent import run as agent_run
    agent_run(
        task=task,
        adapter=adapter,
        provider=provider,
        model=model,
        cwd=cwd,
        max_iterations=max_iter,
        backup=backup,
        log=log,
    )


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


if __name__ == "__main__":
    main()
