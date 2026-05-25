import { ToolDef } from "../tools/definitions.js";

export interface ToolCall {
  id: string;
  name: string;
  args: Record<string, unknown>;
}

export interface ModelResponse {
  text: string;
  stopReason: "end_turn" | "tool_use";
  toolCalls: ToolCall[];
  inputTokens: number;
  outputTokens: number;
}

export type Message = { role: string; content: unknown };

export interface ModelAdapter {
  chat(messages: Message[], tools: ToolDef[], system: string): Promise<ModelResponse>;
  buildToolResultMessages(toolCalls: ToolCall[], results: [string, boolean][]): Message[];
}
