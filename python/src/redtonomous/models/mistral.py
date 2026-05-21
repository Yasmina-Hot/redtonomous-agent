import json
from mistralai import Mistral

from .base import ModelAdapter, ModelResponse, ToolCall
from ..tools.definitions import to_openai_tools  # Mistral uses same format


class MistralAdapter(ModelAdapter):
    def __init__(self, api_key: str, model: str = "mistral-large-latest"):
        self.client = Mistral(api_key=api_key)
        self.model = model

    def chat(self, messages: list[dict], tools: list[dict], system: str = "") -> ModelResponse:
        all_messages = []
        if system:
            all_messages.append({"role": "system", "content": system})
        all_messages.extend(messages)

        mistral_tools = to_openai_tools(tools) if tools else None

        kwargs: dict = dict(model=self.model, messages=all_messages)
        if mistral_tools:
            kwargs["tools"] = mistral_tools
            kwargs["tool_choice"] = "auto"

        resp = self.client.chat.complete(**kwargs)
        msg = resp.choices[0].message
        tool_calls = []
        if msg.tool_calls:
            for tc in msg.tool_calls:
                try:
                    args = json.loads(tc.function.arguments)
                except Exception:
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
            "content": "",
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
