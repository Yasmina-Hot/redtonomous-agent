import Anthropic from "@anthropic-ai/sdk";
import { ModelAdapter, ModelResponse, ToolCall, Message } from "./base.js";
import { ToolDef, toAnthropicTools } from "../tools/definitions.js";

export class ClaudeAdapter implements ModelAdapter {
  private client: Anthropic;
  private model: string;

  constructor(apiKey: string, model: string) {
    this.client = new Anthropic({ apiKey });
    this.model = model;
  }

  async chat(messages: Message[], tools: ToolDef[], system: string): Promise<ModelResponse> {
    const resp = await this.client.messages.create({
      model: this.model,
      max_tokens: 8096,
      system,
      messages: messages as Anthropic.MessageParam[],
      tools: toAnthropicTools(tools) as Anthropic.Tool[],
    });

    const textParts: string[] = [];
    const toolCalls: ToolCall[] = [];
    for (const block of resp.content) {
      if (block.type === "text") textParts.push(block.text);
      else if (block.type === "tool_use") {
        toolCalls.push({ id: block.id, name: block.name, args: block.input as Record<string, unknown> });
      }
    }

    return {
      text: textParts.join("\n"),
      stopReason: toolCalls.length > 0 ? "tool_use" : "end_turn",
      toolCalls,
      inputTokens: resp.usage.input_tokens,
      outputTokens: resp.usage.output_tokens,
    };
  }

  buildToolResultMessages(toolCalls: ToolCall[], results: [string, boolean][]): Message[] {
    const assistantContent = toolCalls.map((tc) => ({
      type: "tool_use",
      id: tc.id,
      name: tc.name,
      input: tc.args,
    }));
    const userContent = toolCalls.map((tc, i) => ({
      type: "tool_result",
      tool_use_id: tc.id,
      content: results[i][0],
      is_error: results[i][1],
    }));
    return [
      { role: "assistant", content: assistantContent },
      { role: "user", content: userContent },
    ];
  }
}
