import copy
import os

import anthropic

from .base import ModelAdapter, ModelResponse, ToolCall
from ..tools.definitions import to_anthropic_tools


def _env_truthy(name: str, default: bool = True) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.lower() not in ("0", "false", "no", "off")


class ClaudeAdapter(ModelAdapter):
    """Anthropic adapter with optional ephemeral prompt caching.

    Caching is enabled by default and can be disabled by setting
    ``REDTONOMOUS_CLAUDE_PROMPT_CACHE=0``. When enabled we tag the system
    prompt and the most recent user turn with
    ``cache_control={"type": "ephemeral"}``, which produces big savings on
    tool-use loops that re-send a long system prompt every turn.
    """

    def __init__(self, api_key: str, model: str = "claude-sonnet-4-6"):
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model
        self.prompt_cache = _env_truthy("REDTONOMOUS_CLAUDE_PROMPT_CACHE", True)

    def _system_block(self, system: str) -> list[dict] | str | None:
        if not system:
            return None
        if not self.prompt_cache:
            return system
        return [
            {
                "type": "text",
                "text": system,
                "cache_control": {"type": "ephemeral"},
            }
        ]

    def _maybe_cache_last_user(self, messages: list[dict]) -> list[dict]:
        if not self.prompt_cache:
            return messages
        # Find the last user message and tag its final content block.
        out = [copy.deepcopy(m) for m in messages]
        for msg in reversed(out):
            if msg.get("role") != "user":
                continue
            content = msg.get("content")
            if isinstance(content, str):
                msg["content"] = [
                    {
                        "type": "text",
                        "text": content,
                        "cache_control": {"type": "ephemeral"},
                    }
                ]
            elif isinstance(content, list) and content:
                last = content[-1]
                if isinstance(last, dict):
                    last.setdefault("cache_control", {"type": "ephemeral"})
            break
        return out

    def chat(self, messages: list[dict], tools: list[dict], system: str = "") -> ModelResponse:
        anthropic_tools = to_anthropic_tools(tools) if tools else []
        kwargs: dict = dict(
            model=self.model,
            max_tokens=8096,
            messages=self._maybe_cache_last_user(messages),
        )
        sys_block = self._system_block(system)
        if sys_block is not None:
            kwargs["system"] = sys_block
        if anthropic_tools:
            kwargs["tools"] = anthropic_tools

        resp = self.client.messages.create(**kwargs)

        text_parts: list[str] = []
        tool_calls: list[ToolCall] = []
        for block in resp.content:
            if block.type == "text":
                text_parts.append(block.text)
            elif block.type == "tool_use":
                tool_calls.append(ToolCall(id=block.id, name=block.name, args=block.input))

        stop_reason = "tool_use" if tool_calls else "end_turn"
        return ModelResponse(
            text="\n".join(text_parts),
            stop_reason=stop_reason,
            tool_calls=tool_calls,
            input_tokens=resp.usage.input_tokens,
            output_tokens=resp.usage.output_tokens,
        )

    def build_tool_result_messages(self, tool_calls: list[ToolCall], results: list[tuple[str, bool]]) -> list[dict]:
        """Build the Anthropic-format assistant + tool_result message pair."""
        assistant_content = [
            {"type": "tool_use", "id": tc.id, "name": tc.name, "input": tc.args}
            for tc in tool_calls
        ]
        user_content = [
            {
                "type": "tool_result",
                "tool_use_id": tc.id,
                "content": result,
                "is_error": is_err,
            }
            for tc, (result, is_err) in zip(tool_calls, results)
        ]
        return [
            {"role": "assistant", "content": assistant_content},
            {"role": "user", "content": user_content},
        ]
