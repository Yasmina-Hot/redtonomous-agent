import { GoogleGenerativeAI, FunctionDeclarationSchema } from "@google/generative-ai";
import { ModelAdapter, ModelResponse, ToolCall, Message } from "./base.js";
import { ToolDef } from "../tools/definitions.js";

export class GeminiAdapter implements ModelAdapter {
  private genAI: GoogleGenerativeAI;
  private model: string;

  constructor(apiKey: string, model: string) {
    this.genAI = new GoogleGenerativeAI(apiKey);
    this.model = model;
  }

  async chat(messages: Message[], tools: ToolDef[], system: string): Promise<ModelResponse> {
    const geminiModel = this.genAI.getGenerativeModel({
      model: this.model,
      systemInstruction: system,
      tools: [
        {
          functionDeclarations: tools.map((t) => ({
            name: t.name,
            description: t.description,
            parameters: t.parameters as FunctionDeclarationSchema,
          })),
        },
      ],
    });

    // Convert messages to Gemini history format
    const history = messages.slice(0, -1).map((m) => ({
      role: m.role === "user" ? "user" : "model",
      parts: typeof m.content === "string"
        ? [{ text: m.content }]
        : (m.content as any[]),
    }));

    const lastMsg = messages[messages.length - 1];
    const chat = geminiModel.startChat({ history });
    const resp = await chat.sendMessage(
      typeof lastMsg.content === "string" ? lastMsg.content : JSON.stringify(lastMsg.content)
    );

    const candidate = resp.response.candidates?.[0];
    const toolCalls: ToolCall[] = [];
    const textParts: string[] = [];

    for (const part of candidate?.content?.parts ?? []) {
      if (part.functionCall) {
        toolCalls.push({
          id: part.functionCall.name,
          name: part.functionCall.name,
          args: (part.functionCall.args as Record<string, unknown>) ?? {},
        });
      } else if (part.text) {
        textParts.push(part.text);
      }
    }

    const usage = resp.response.usageMetadata;
    return {
      text: textParts.join("\n"),
      stopReason: toolCalls.length > 0 ? "tool_use" : "end_turn",
      toolCalls,
      inputTokens: usage?.promptTokenCount ?? 0,
      outputTokens: usage?.candidatesTokenCount ?? 0,
    };
  }

  buildToolResultMessages(toolCalls: ToolCall[], results: [string, boolean][]): Message[] {
    return [
      {
        role: "model",
        content: toolCalls.map((tc) => ({
          functionCall: { name: tc.name, args: tc.args },
        })),
      },
      {
        role: "user",
        content: toolCalls.map((tc, i) => ({
          functionResponse: { name: tc.name, response: { result: results[i][0] } },
        })),
      },
    ];
  }
}
