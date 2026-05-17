import OpenAI from "openai";
import { ModelAdapter, ModelResponse, ToolCall, Message } from "./base.js";
import { ToolDef, toOpenAITools } from "../tools/definitions.js";

export class OpenAICompatAdapter implements ModelAdapter {
  private client: OpenAI;
  private model: string;

  constructor(apiKey: string, model: string, baseURL?: string) {
    this.client = new OpenAI({
      apiKey: apiKey === "none" ? "none" : apiKey,
      ...(baseURL ? { baseURL } : {}),
    });
    this.model = model;
  }

  async chat(messages: Message[], tools: ToolDef[], system: string): Promise<ModelResponse> {
    const allMessages: OpenAI.ChatCompletionMessageParam[] = [];
    if (system) allMessages.push({ role: "system", content: system });
    allMessages.push(...(messages as OpenAI.ChatCompletionMessageParam[]));

    const resp = await this.client.chat.completions.create({
      model: this.model,
      messages: allMessages,
      tools: toOpenAITools(tools) as OpenAI.ChatCompletionTool[],
      tool_choice: "auto",
    });

    const msg = resp.choices[0].message;
    const toolCalls: ToolCall[] = (msg.tool_calls ?? []).map((tc) => ({
      id: tc.id,
      name: tc.function.name,
      args: (() => { try { return JSON.parse(tc.function.arguments); } catch { return {}; } })(),
    }));

    return {
      text: msg.content ?? "",
      stopReason: toolCalls.length > 0 ? "tool_use" : "end_turn",
      toolCalls,
      inputTokens: resp.usage?.prompt_tokens ?? 0,
      outputTokens: resp.usage?.completion_tokens ?? 0,
    };
  }

  buildToolResultMessages(toolCalls: ToolCall[], results: [string, boolean][]): Message[] {
    const assistantMsg: Message = {
      role: "assistant",
      content: null,
    };
    (assistantMsg as any).tool_calls = toolCalls.map((tc) => ({
      id: tc.id,
      type: "function",
      function: { name: tc.name, arguments: JSON.stringify(tc.args) },
    }));
    const toolMsgs: Message[] = toolCalls.map((tc, i) => ({
      role: "tool",
      content: results[i][0],
      tool_call_id: tc.id,
    } as any));
    return [assistantMsg, ...toolMsgs];
  }
}
