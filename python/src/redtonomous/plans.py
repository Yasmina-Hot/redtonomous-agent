"""Subscription plan catalog — single source of truth shared by the CLI and the
FastAPI backend (the latter re-exports this via ``GET /plans``).

Pricing here is informational only; we don't enforce anything at the wire
level today. The intent is to let the frontend render a pricing page and the
CLI surface "what tier are you on?" hints.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class Plan:
    id: str
    name: str
    price_usd: float
    period: str = "month"
    tagline: str = ""
    features: tuple[str, ...] = field(default_factory=tuple)
    sessions_per_month: int | None = None  # None = unlimited
    max_iterations: int | None = None      # None = no cap
    providers: tuple[str, ...] = ("claude", "openai", "gemini", "groq", "ollama", "lmstudio")
    cli_modes: tuple[str, ...] = ("run", "moonlight", "goal")
    support: str = "community"
    badge: str = ""

    def as_public(self) -> dict[str, Any]:
        d = asdict(self)
        # Convert tuples to lists for JSON-friendliness.
        for k, v in list(d.items()):
            if isinstance(v, tuple):
                d[k] = list(v)
        return d


PLANS: tuple[Plan, ...] = (
    Plan(
        id="free",
        name="Free",
        price_usd=0.0,
        tagline="Bring your own keys. Run locally. Always free.",
        features=(
            "All three CLIs (Python / TypeScript / Go)",
            "Bring-your-own-key for any provider",
            "Local web UI (Chat + RDX)",
            "Up to 50 cloud-relay sessions / month",
        ),
        sessions_per_month=50,
        max_iterations=100,
        cli_modes=("run", "goal"),
    ),
    Plan(
        id="min",
        name="Min",
        price_usd=4.0,
        tagline="A little headroom for nights and weekends.",
        features=(
            "Everything in Free",
            "100 cloud-relay sessions / month",
            "Priority queue when providers are busy",
            "Email support",
        ),
        sessions_per_month=100,
        max_iterations=200,
        support="email",
    ),
    Plan(
        id="starter",
        name="Starter",
        price_usd=9.0,
        tagline="For solo devs who use the agent daily.",
        features=(
            "Everything in Min",
            "250 cloud-relay sessions / month",
            "Hosted Chat UI (no setup)",
            "Session history sync across devices",
        ),
        sessions_per_month=250,
        max_iterations=300,
        support="email",
        badge="Popular",
    ),
    Plan(
        id="pro",
        name="Pro",
        price_usd=19.0,
        tagline="The everyday workhorse plan.",
        features=(
            "Everything in Starter",
            "Unlimited sessions",
            "All providers + prompt caching included",
            "moonlight mode (overnight runs)",
            "Goal mode with strong-judge model",
        ),
        sessions_per_month=None,
        max_iterations=1000,
        cli_modes=("run", "moonlight", "goal"),
        support="email",
    ),
    Plan(
        id="dev",
        name="Dev",
        price_usd=39.0,
        tagline="For teams shipping production code.",
        features=(
            "Everything in Pro",
            "Team workspaces + shared sessions",
            "Audit logs (90-day retention)",
            "Custom MCP server connections",
            "Slack / Discord notifications",
        ),
        sessions_per_month=None,
        max_iterations=2000,
        support="email + chat",
    ),
    Plan(
        id="max",
        name="Max",
        price_usd=99.0,
        tagline="For power users who let it cook all night.",
        features=(
            "Everything in Dev",
            "Dedicated compute capacity",
            "Priority routing (P0 issues < 4h response)",
            "Early access to new providers + features",
            "Custom system-prompt presets",
        ),
        sessions_per_month=None,
        max_iterations=5000,
        support="priority",
    ),
    Plan(
        id="red",
        name="Red",
        price_usd=499.0,
        tagline="No guardrails. No limits. You signed the waiver.",
        features=(
            "Everything in Max",
            "/red dangerous-bypass mode — unlimited",
            "Self-host / on-prem option",
            "Custom retention policies",
            "24/7 SLA, named engineer on call",
            "Indemnification rider available",
        ),
        sessions_per_month=None,
        max_iterations=None,
        cli_modes=("run", "moonlight", "goal", "red"),
        support="24/7 dedicated",
        badge="Most dangerous",
    ),
)


def plan_by_id(plan_id: str) -> Plan | None:
    for p in PLANS:
        if p.id == plan_id:
            return p
    return None


def public_catalog() -> list[dict[str, Any]]:
    """Return the plan list as JSON-friendly dicts (for the API endpoint)."""
    return [p.as_public() for p in PLANS]
