"""
Adapter for OpenAI and all OpenAI-compatible providers:
  openai, groq, ollama, lmstudio, openrouter, deepseek, xai, together, perplexity, and custom.
"""
import json
import openai

from .base import ModelAdapter, ModelResponse, ToolCall
from ..tools.definitions import to_openai_tools


class OpenAICompatAdapter(ModelAdapter):
    def __init__(self, api_key: str, model: str, base_url: str | None = None):
        self.model = model
        client_kwargs: dict = {"api_key": api_key if api_key != "none" else "none"}
        if base_url:
            client_kwargs["base_url"] = base_url
        self.client = openai.OpenAI(**client_kwargs)

    def chat(self, messages: list[dict], tools: list[dict], system: str = "") -> ModelResponse:
        all_messages = []
        if system:
            all_messages.append({"role": "system", "content": system})
        all_messages.extend(messages)

        openai_tools = to_openai_tools(tools) if tools else None

        kwargs: dict = dict(model=self.model, messages=all_messages)
        if openai_tools:
            kwargs["tools"] = openai_tools
            kwargs["tool_choice"] = "auto"

        resp = self.client.chat.completions.create(**kwargs)
        msg = resp.choices[0].message
        stop = resp.choices[0].finish_reason

        tool_calls = []
        if msg.tool_calls:
            for tc in msg.tool_calls:
                try:
                    args = json.loads(tc.function.arguments)
                except json.JSONDecodeError:
                    args = {}
                tool_calls.append(ToolCall(id=tc.id, name=tc.function.name, args=args))

        stop_reason = "tool_use" if tool_calls else "end_turn"
        return ModelResponse(
            text=msg.content or "",
            stop_reason=stop_reason,
            tool_calls=tool_calls,
            input_tokens=getattr(resp.usage, "prompt_tokens", 0),
            output_tokens=getattr(resp.usage, "completion_tokens", 0),
        )

    def build_tool_result_messages(self, tool_calls: list[ToolCall], results: list[tuple[str, bool]]) -> list[dict]:
        assistant_msg: dict = {
            "role": "assistant",
            "content": None,
            "tool_calls": [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {"name": tc.name, "arguments": json.dumps(tc.args)},
                }
                for tc in tool_calls
            ],
        }
        tool_msgs = [
            {"role": "tool", "tool_call_id": tc.id, "content": result}
            for tc, (result, _) in zip(tool_calls, results)
        ]
        return [assistant_msg, *tool_msgs]
