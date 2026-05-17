import os
import sys

import click
from rich.prompt import Confirm

from . import display
from . import config as cfg_module
from .models import get_adapter, list_models


@click.group()
def main():
    """Redtonomous — autonomous multi-model coding agent CLI."""


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

    cfg = cfg_module.load()
    provider = provider or cfg.get("default_provider", "claude")
    model = model or cfg.get("default_model") or cfg_module.get_default_model_for_provider(provider)
    cwd = os.path.abspath(workdir or os.getcwd())

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
    # mask keys
    for pdata in cfg.get("providers", {}).values():
        if "api_key" in pdata and pdata["api_key"] not in ("none", "", None):
            pdata["api_key"] = pdata["api_key"][:8] + "…"
    display.console.print_json(json.dumps(cfg, indent=2))


# ── models ────────────────────────────────────────────────────────────────────

@main.command()
def models():
    """List all known models grouped by provider."""
    display.models_table(list_models())


# ── auth ──────────────────────────────────────────────────────────────────────

@main.command()
def auth():
    """OAuth login for Claude (coming soon)."""
    display.print_info("OAuth login is on the roadmap. Use 'config set-key claude <key>' for now.")


if __name__ == "__main__":
    main()
