import { AppConfig, getApiKey, getBaseUrl, OPENAI_COMPAT_PROVIDERS } from "../config.js";
import { ModelAdapter } from "./base.js";

export const KNOWN_MODELS = [
  { provider: "claude",     model: "claude-opus-4-7",              type: "claude" },
  { provider: "claude",     model: "claude-sonnet-4-6",            type: "claude" },
  { provider: "claude",     model: "claude-haiku-4-5",             type: "claude" },
  { provider: "openai",     model: "gpt-4o",                       type: "openai-compat" },
  { provider: "openai",     model: "gpt-4o-mini",                  type: "openai-compat" },
  { provider: "openai",     model: "o1",                           type: "openai-compat" },
  { provider: "gemini",     model: "gemini-2.5-pro",               type: "gemini" },
  { provider: "gemini",     model: "gemini-2.0-flash",             type: "gemini" },
  { provider: "groq",       model: "llama-3.3-70b-versatile",      type: "openai-compat" },
  { provider: "groq",       model: "mixtral-8x7b-32768",           type: "openai-compat" },
  { provider: "openrouter", model: "openai/gpt-4o",                type: "openai-compat" },
  { provider: "deepseek",   model: "deepseek-chat",                type: "openai-compat" },
  { provider: "xai",        model: "grok-3",                       type: "openai-compat" },
  { provider: "ollama",     model: "llama3.2",                     type: "openai-compat (local)" },
  { provider: "ollama",     model: "codellama",                    type: "openai-compat (local)" },
  { provider: "lmstudio",   model: "local-model",                  type: "openai-compat (local)" },
];

export async function getAdapter(provider: string, model: string, cfg: AppConfig): Promise<ModelAdapter> {
  const apiKey = getApiKey(cfg, provider);
  const baseUrl = getBaseUrl(cfg, provider);

  if (provider === "claude") {
    if (!apiKey) throw new Error("No API key for claude. Run: redtonomous config set-key claude <key>");
    const { ClaudeAdapter } = await import("./claude.js");
    return new ClaudeAdapter(apiKey, model);
  }

  if (provider === "gemini") {
    if (!apiKey) throw new Error("No API key for gemini. Run: redtonomous config set-key gemini <key>");
    const { GeminiAdapter } = await import("./gemini.js");
    return new GeminiAdapter(apiKey, model);
  }

  // OpenAI-compatible (includes openai, groq, ollama, lmstudio, openrouter, deepseek, xai, etc.)
  const { OpenAICompatAdapter } = await import("./openai-compat.js");
  const isLocal = provider === "ollama" || provider === "lmstudio";
  if (!apiKey && !isLocal) {
    throw new Error(`No API key for ${provider}. Run: redtonomous config set-key ${provider} <key>`);
  }
  return new OpenAICompatAdapter(apiKey ?? "none", model, baseUrl);
}
