import json
import cohere

from .base import ModelAdapter, ModelResponse, ToolCall


def _to_cohere_tools(tools: list[dict]) -> list[dict]:
    result = []
    for t in tools:
        params = {}
        for pname, pdef in t["parameters"].get("properties", {}).items():
            params[pname] = {
                "description": pdef.get("description", ""),
                "type": pdef.get("type", "str").upper(),
                "required": pname in t["parameters"].get("required", []),
            }
        result.append({
            "name": t["name"],
            "description": t["description"],
            "parameter_definitions": params,
        })
    return result


class CohereAdapter(ModelAdapter):
    def __init__(self, api_key: str, model: str = "command-r-plus"):
        self.client = cohere.ClientV2(api_key=api_key)
        self.model = model

    def chat(self, messages: list[dict], tools: list[dict], system: str = "") -> ModelResponse:
        all_messages = []
        if system:
            all_messages.append({"role": "system", "content": system})
        all_messages.extend(messages)

        cohere_tools = _to_cohere_tools(tools) if tools else None

        kwargs: dict = dict(model=self.model, messages=all_messages)
        if cohere_tools:
            kwargs["tools"] = cohere_tools

        resp = self.client.chat(**kwargs)
        msg = resp.message

        tool_calls = []
        text = ""
        for block in msg.content or []:
            if hasattr(block, "text"):
                text += block.text
            elif hasattr(block, "tool_calls"):
                for tc in block.tool_calls:
                    try:
                        args = json.loads(tc.parameters) if isinstance(tc.parameters, str) else tc.parameters
                    except Exception:
                        args = {}
                    tool_calls.append(ToolCall(id=tc.id or tc.name, name=tc.name, args=args or {}))

        stop_reason = "tool_use" if tool_calls else "end_turn"
        return ModelResponse(text=text, stop_reason=stop_reason, tool_calls=tool_calls)

    def build_tool_result_messages(self, tool_calls: list[ToolCall], results: list[tuple[str, bool]]) -> list[dict]:
        # Cohere v2 needs the assistant turn with tool_calls FIRST, then the tool results.
        assistant_msg: dict = {
            "role": "assistant",
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
            {
                "role": "tool",
                "tool_call_id": tc.id,
                "content": result,
            }
            for tc, (result, _) in zip(tool_calls, results)
        ]
        return [assistant_msg, *tool_msgs]
