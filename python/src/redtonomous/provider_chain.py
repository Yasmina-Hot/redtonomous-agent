"""Provider failover — used by ``--fallback claude,openai,gemini``.

The chain wraps a primary adapter plus an ordered list of fallback adapters.
On a transient error (rate limit / 5xx) we transparently switch to the next
adapter, preserving the running conversation. Each provider may use a
different message format, so we keep the original ``task`` and the latest
``tool_result`` summaries as plain text and let each new adapter rebuild
provider-specific structure from there.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .agent import _is_transient
from .models.base import ModelAdapter, ModelResponse


@dataclass
class ProviderChain(ModelAdapter):
    """Adapter that forwards to a primary then falls through to fallbacks.

    Each member must implement the same :class:`ModelAdapter` protocol. The
    chain itself implements ``ModelAdapter`` so callers (``agent.run``) need
    no changes — they just pass the chain in place of a normal adapter.
    """

    primary: ModelAdapter
    fallbacks: list[ModelAdapter] = field(default_factory=list)
    _idx: int = 0

    @property
    def current(self) -> ModelAdapter:
        if self._idx == 0:
            return self.primary
        return self.fallbacks[self._idx - 1]

    def _advance(self) -> bool:
        if self._idx >= len(self.fallbacks):
            return False
        self._idx += 1
        return True

    def chat(self, messages: list[dict], tools: list[dict], system: str = "") -> ModelResponse:
        while True:
            try:
                return self.current.chat(messages=messages, tools=tools, system=system)
            except Exception as exc:
                if not _is_transient(exc) or not self._advance():
                    raise

    def build_tool_result_messages(self, tool_calls, results):
        return self.current.build_tool_result_messages(tool_calls, results)
