from google import genai
from google.genai import types

from .base import ModelAdapter, ModelResponse, ToolCall
from ..tools.definitions import to_gemini_declarations


class GeminiAdapter(ModelAdapter):
    def __init__(self, api_key: str, model: str = "gemini-2.0-flash"):
        self.client = genai.Client(api_key=api_key)
        self.model = model

    def chat(self, messages: list[dict], tools: list[dict], system: str = "") -> ModelResponse:
        # Convert canonical messages to Gemini Content objects
        contents = []
        for m in messages:
            role = "user" if m["role"] == "user" else "model"
            content = m["content"]
            if isinstance(content, str):
                contents.append(types.Content(role=role, parts=[types.Part(text=content)]))
            elif isinstance(content, list):
                # tool result messages
                parts = []
                for item in content:
                    if isinstance(item, dict) and item.get("type") == "tool_result":
                        parts.append(
                            types.Part(
                                function_response=types.FunctionResponse(
                                    name=item.get("name", "tool"),
                                    response={"result": item.get("content", "")},
                                )
                            )
                        )
                    elif isinstance(item, dict) and item.get("type") == "function_call":
                        parts.append(
                            types.Part(
                                function_call=types.FunctionCall(
                                    name=item["name"], args=item.get("args", {})
                                )
                            )
                        )
                    else:
                        parts.append(types.Part(text=str(item)))
                if parts:
                    contents.append(types.Content(role=role, parts=parts))

        # Build tools
        gemini_tools = None
        if tools:
            declarations = to_gemini_declarations(tools)
            gemini_tools = [
                types.Tool(
                    function_declarations=[
                        types.FunctionDeclaration(
                            name=d["name"],
                            description=d["description"],
                            parameters=d["parameters"],
                        )
                        for d in declarations
                    ]
                )
            ]

        cfg = types.GenerateContentConfig(
            system_instruction=system or None,
            tools=gemini_tools,
        )

        resp = self.client.models.generate_content(
            model=self.model,
            contents=contents,
            config=cfg,
        )

        tool_calls = []
        text_parts = []
        for part in resp.candidates[0].content.parts:
            if part.function_call:
                fc = part.function_call
                tool_calls.append(
                    ToolCall(
                        id=fc.name,
                        name=fc.name,
                        args=dict(fc.args) if fc.args else {},
                    )
                )
            elif part.text:
                text_parts.append(part.text)

        stop_reason = "tool_use" if tool_calls else "end_turn"
        usage = resp.usage_metadata
        return ModelResponse(
            text="\n".join(text_parts),
            stop_reason=stop_reason,
            tool_calls=tool_calls,
            input_tokens=getattr(usage, "prompt_token_count", 0),
            output_tokens=getattr(usage, "candidates_token_count", 0),
        )

    def build_tool_result_messages(self, tool_calls: list[ToolCall], results: list[tuple[str, bool]]) -> list[dict]:
        # Gemini uses model parts with function_call then user parts with function_response
        model_parts = [
            {"type": "function_call", "name": tc.name, "args": tc.args}
            for tc in tool_calls
        ]
        user_parts = [
            {"type": "tool_result", "name": tc.name, "content": result}
            for tc, (result, _) in zip(tool_calls, results)
        ]
        return [
            {"role": "assistant", "content": model_parts},
            {"role": "user", "content": user_parts},
        ]
