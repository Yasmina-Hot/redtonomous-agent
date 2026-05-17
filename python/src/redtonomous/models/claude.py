import anthropic

from .base import ModelAdapter, ModelResponse, ToolCall
from ..tools.definitions import to_anthropic_tools


class ClaudeAdapter(ModelAdapter):
    def __init__(self, api_key: str, model: str = "claude-sonnet-4-6"):
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model

    def chat(self, messages: list[dict], tools: list[dict], system: str = "") -> ModelResponse:
        # Anthropic doesn't accept tool_result as first message role
        anthropic_tools = to_anthropic_tools(tools) if tools else []
        kwargs: dict = dict(
            model=self.model,
            max_tokens=8096,
            messages=messages,
        )
        if system:
            kwargs["system"] = system
        if anthropic_tools:
            kwargs["tools"] = anthropic_tools

        resp = self.client.messages.create(**kwargs)

        text_parts = []
        tool_calls = []
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

    @staticmethod
    def build_tool_result_message(tool_calls: list[ToolCall], results: list[tuple[str, bool]]) -> list[dict]:
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
