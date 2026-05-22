from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.table import Table
from rich import box
from rich.markup import escape

console = Console()

BANNER = """[bold red]
██████╗ ███████╗██████╗ ████████╗ ██████╗ ███╗   ██╗ ██████╗ ███╗   ███╗ ██████╗ ██╗   ██╗███████╗
██╔══██╗██╔════╝██╔══██╗╚══██╔══╝██╔═══██╗████╗  ██║██╔═══██╗████╗ ████║██╔═══██╗██║   ██║██╔════╝
██████╔╝█████╗  ██║  ██║   ██║   ██║   ██║██╔██╗ ██║██║   ██║██╔████╔██║██║   ██║██║   ██║███████╗
██╔══██╗██╔══╝  ██║  ██║   ██║   ██║   ██║██║╚██╗██║██║   ██║██║╚██╔╝██║██║   ██║██║   ██║╚════██║
██║  ██║███████╗██████╔╝   ██║   ╚██████╔╝██║ ╚████║╚██████╔╝██║ ╚═╝ ██║╚██████╔╝╚██████╔╝███████║
╚═╝  ╚═╝╚══════╝╚═════╝    ╚═╝    ╚═════╝ ╚═╝  ╚═══╝ ╚═════╝ ╚═╝     ╚═╝ ╚═════╝  ╚═════╝ ╚══════╝[/bold red]"""


def print_banner() -> None:
    console.print(BANNER)
    console.print(
        "[dim]Autonomous multi-model coding agent — BYOK, no permission prompts[/dim]\n"
    )


def warn_autonomous(cwd: str, provider: str, model: str) -> None:
    console.print(
        Panel(
            f"[bold yellow]⚡ AUTONOMOUS MODE ACTIVE[/bold yellow]\n\n"
            f"[yellow]All actions execute WITHOUT confirmation.[/yellow]\n"
            f"Files will be created, modified, and deleted.\n"
            f"Shell commands will run in: [bold]{escape(cwd)}[/bold]\n\n"
            f"[dim]Provider: {provider}  |  Model: {model}[/dim]",
            border_style="yellow",
            title="[bold yellow]WARNING[/bold yellow]",
        )
    )


def print_backup(src: str, dst: str) -> None:
    console.print(f"[dim]📦 Backup created: {escape(dst)}[/dim]")


def print_tool_call(name: str, args: dict) -> None:
    args_text = "  ".join(f"[cyan]{escape(k)}[/cyan]=[green]{escape(repr(v))[:80]}[/green]" for k, v in args.items())
    console.print(f"[bold blue]▶ {escape(name)}[/bold blue]  {args_text}")


def print_tool_result(name: str, result: str, is_error: bool = False) -> None:
    color = "red" if is_error else "dim"
    prefix = "✗" if is_error else "✓"
    preview = escape(result[:200]) + ("…" if len(result) > 200 else "")
    console.print(f"[{color}]{prefix} {escape(name)}: {preview}[/{color}]")


def print_thinking(text: str) -> None:
    console.print(f"[dim italic]  {escape(text[:120])}[/dim italic]")


def print_final(text: str) -> None:
    console.print(Panel(text, title="[bold green]✅ Done[/bold green]", border_style="green"))


def print_error(msg: str) -> None:
    console.print(f"[bold red]Error:[/bold red] {escape(msg)}")


def print_info(msg: str) -> None:
    console.print(f"[dim]{escape(msg)}[/dim]")


def print_repl_prompt(provider: str, model: str, cwd: str) -> str:
    """Return the REPL prompt string (caller uses input() with it)."""
    short_cwd = Path(cwd).name or cwd
    console.print(
        f"[dim]({provider}/{model} · {escape(short_cwd)})[/dim]",
        end="  ",
    )
    return ""


def models_table(models: list[dict]) -> None:
    t = Table(title="Available Models", box=box.ROUNDED)
    t.add_column("Provider", style="cyan")
    t.add_column("Model ID", style="white")
    t.add_column("Type", style="dim")
    for m in models:
        t.add_row(m["provider"], m["model"], m.get("type", ""))
    console.print(t)
