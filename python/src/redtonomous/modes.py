"""Cross-cutting machinery for the autonomy modes (moonlight / red / goal).

These primitives are intentionally light-weight and synchronous — the
existing CLI agent loop is synchronous and we want zero behavior change
when the wrappers are inactive.
"""
from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

# Per-million-token pricing in USD. When a model id isn't in this table we
# fall back to the conservative ``UNKNOWN_PRICE`` (Opus-tier) so the budget
# guard errs on the side of stopping early rather than overrunning the cap.
#
# Keep ids in sync with ``models/registry.py:KNOWN_MODELS``.
MODEL_PRICING_USD_PER_MTOK: dict[str, tuple[float, float]] = {
    # Anthropic
    "claude-opus-4-7":           (15.0, 75.0),
    "claude-sonnet-4-6":         (3.0,  15.0),
    "claude-haiku-4-5":          (0.8,   4.0),
    # OpenAI
    "gpt-4o":                    (2.5,  10.0),
    "gpt-4o-mini":               (0.15,  0.6),
    "o1":                       (15.0,  60.0),
    "o3-mini":                   (1.1,   4.4),
    # Gemini
    "gemini-2.5-pro":            (1.25,  5.0),
    "gemini-2.0-flash":          (0.1,   0.4),
    # Groq (rough)
    "llama-3.3-70b-versatile":   (0.59,  0.79),
    "mixtral-8x7b-32768":        (0.24,  0.24),
    "gemma2-9b-it":              (0.2,   0.2),
    # Mistral
    "mistral-large-latest":      (2.0,   6.0),
    "codestral-latest":          (0.3,   0.9),
    # Cohere
    "command-r-plus":            (2.5,  10.0),
    "command-r":                 (0.15,  0.6),
    # DeepSeek
    "deepseek-chat":             (0.27,  1.10),
    "deepseek-coder":            (0.27,  1.10),
    # xAI
    "grok-3":                    (3.0,  15.0),
    "grok-3-mini":               (0.3,   1.0),
    # Local / unpriced
    "llama3.2":                  (0.0,   0.0),
    "codellama":                 (0.0,   0.0),
    "local-model":               (0.0,   0.0),
    "deepseek-coder-v2":         (0.0,   0.0),
}

# Fall-back price for an unknown model id. Opus-tier on purpose.
UNKNOWN_PRICE: tuple[float, float] = (15.0, 75.0)


def price_for(model: str) -> tuple[float, float]:
    """Return ``(usd_per_mtok_in, usd_per_mtok_out)`` for the given model id."""
    if model in MODEL_PRICING_USD_PER_MTOK:
        return MODEL_PRICING_USD_PER_MTOK[model]
    # Match by prefix for variants like "openai/gpt-4o" or "anthropic/claude-...".
    base = model.split("/")[-1]
    if base in MODEL_PRICING_USD_PER_MTOK:
        return MODEL_PRICING_USD_PER_MTOK[base]
    return UNKNOWN_PRICE


class BudgetExceeded(RuntimeError):
    """Raised when accumulated spend crosses the configured cap."""


@dataclass
class Budget:
    """Tracks USD spend across an agent loop.

    ``charge()`` accumulates cost and raises :class:`BudgetExceeded` when the
    cap is hit. ``snapshot()`` returns a copy of the running totals for the
    heartbeat/status line.
    """

    cap_usd: float
    model: str
    spent_usd: float = 0.0
    tokens_in: int = 0
    tokens_out: int = 0
    price_in: float = 0.0
    price_out: float = 0.0

    def __post_init__(self) -> None:
        self.price_in, self.price_out = price_for(self.model)

    def charge(self, tokens_in: int, tokens_out: int) -> None:
        self.tokens_in += int(tokens_in or 0)
        self.tokens_out += int(tokens_out or 0)
        cost = (
            (tokens_in or 0) * self.price_in / 1_000_000
            + (tokens_out or 0) * self.price_out / 1_000_000
        )
        self.spent_usd += cost
        if self.cap_usd and self.spent_usd >= self.cap_usd:
            raise BudgetExceeded(
                f"Budget exceeded: ${self.spent_usd:.4f} spent, cap ${self.cap_usd:.2f}"
            )

    def remaining_usd(self) -> float:
        if not self.cap_usd:
            return float("inf")
        return max(0.0, self.cap_usd - self.spent_usd)

    def snapshot(self) -> dict[str, Any]:
        return {
            "spent_usd": round(self.spent_usd, 6),
            "cap_usd": self.cap_usd,
            "tokens_in": self.tokens_in,
            "tokens_out": self.tokens_out,
            "model": self.model,
        }


class WallClockExceeded(RuntimeError):
    """Raised when the configured wall-clock cap is exceeded."""


@dataclass
class WallClock:
    """Wall-clock deadline checker. ``cap_seconds <= 0`` disables it."""

    cap_seconds: float
    started_at: float = field(default_factory=time.monotonic)

    @classmethod
    def from_hours(cls, hours: float) -> "WallClock":
        return cls(cap_seconds=max(0.0, float(hours) * 3600.0))

    def elapsed(self) -> float:
        return time.monotonic() - self.started_at

    def check(self) -> None:
        if self.cap_seconds and self.elapsed() >= self.cap_seconds:
            raise WallClockExceeded(
                f"Wall-clock cap exceeded: {self.elapsed():.1f}s "
                f"(cap {self.cap_seconds:.0f}s)"
            )


@dataclass
class Heartbeat:
    """Emit a status line every ``period_s`` seconds via ``emit``."""

    emit: Callable[[str], None]
    period_s: float = 300.0
    last_at: float = field(default_factory=time.monotonic)

    def tick(self, payload: dict[str, Any]) -> None:
        now = time.monotonic()
        if now - self.last_at < self.period_s:
            return
        self.last_at = now
        parts = [f"{k}={v}" for k, v in payload.items()]
        self.emit("[heartbeat] " + " ".join(parts))


# Hooks ----------------------------------------------------------------------


HOOKS_FILE_ENV = "REDTONOMOUS_HOOKS_FILE"
HOOKS_DEFAULT_PATH = Path.home() / ".redtonomous" / "hooks.json"

_HOOK_EVENTS = ("pre_tool", "post_tool", "on_error", "on_done")


def _hooks_path() -> Path:
    override = os.environ.get(HOOKS_FILE_ENV)
    if override:
        return Path(override).expanduser()
    return HOOKS_DEFAULT_PATH


def load_hooks() -> dict[str, str]:
    """Load the user's hook commands. Missing file → no hooks (return {})."""
    path = _hooks_path()
    if not path.exists():
        return {}
    try:
        with open(path) as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}
    return {k: v for k, v in data.items() if k in _HOOK_EVENTS and isinstance(v, str) and v.strip()}


def fire_hook(event: str, context: dict[str, str]) -> None:
    """Invoke the user-configured shell command for ``event`` if any.

    The command is executed with ``shell=True`` (the user wrote it; same
    trust level as the agent's own ``execute_command``). Each context value
    is exported as ``REDTONOMOUS_<KEY>``. Hooks are best-effort and never
    raise — failures are swallowed but recorded in the calling code via
    return value.
    """
    cmd = load_hooks().get(event)
    if not cmd:
        return
    env = os.environ.copy()
    for k, v in context.items():
        env[f"REDTONOMOUS_{k.upper()}"] = str(v)
    try:
        import subprocess
        subprocess.run(cmd, shell=True, env=env, timeout=30, check=False)
    except (OSError, ValueError):
        pass
