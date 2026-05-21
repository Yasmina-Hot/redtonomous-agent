from dataclasses import dataclass, field
from abc import ABC, abstractmethod


@dataclass
class ToolCall:
    id: str
    name: str
    args: dict


@dataclass
class ModelResponse:
    text: str
    stop_reason: str          # "end_turn" | "tool_use" | "stop"
    tool_calls: list[ToolCall] = field(default_factory=list)
    input_tokens: int = 0
    output_tokens: int = 0


class ModelAdapter(ABC):
    """Unified interface for every provider."""

    @abstractmethod
    def chat(
        self,
        messages: list[dict],
        tools: list[dict],
        system: str = "",
    ) -> ModelResponse:
        ...

    @abstractmethod
    def build_tool_result_messages(
        self,
        tool_calls: list[ToolCall],
        results: list[tuple[str, bool]],
    ) -> list[dict]:
        """Return the provider-specific messages to append after tool execution."""
        ...
