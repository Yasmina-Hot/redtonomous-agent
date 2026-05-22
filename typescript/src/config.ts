import fs from "fs";
import os from "os";
import path from "path";

export const CONFIG_DIR = path.join(os.homedir(), ".redtonomous");
export const CONFIG_FILE = path.join(CONFIG_DIR, "config.json");
export const LOGS_DIR = path.join(CONFIG_DIR, "logs");

export interface ProviderConfig {
  api_key?: string;
  base_url?: string;
  default_model?: string;
  type?: string;
}

export interface AppConfig {
  default_provider: string;
  default_model: string;
  wake_word?: string;
  providers: Record<string, ProviderConfig>;
}

export function getWakeWord(cfg: AppConfig): string | undefined {
  return cfg.wake_word || undefined;
}

export const OPENAI_COMPAT_PROVIDERS: Record<string, { base_url: string; default_model: string }> = {
  openai:     { base_url: "https://api.openai.com/v1",          default_model: "gpt-4o" },
  groq:       { base_url: "https://api.groq.com/openai/v1",     default_model: "llama-3.3-70b-versatile" },
  openrouter: { base_url: "https://openrouter.ai/api/v1",       default_model: "openai/gpt-4o" },
  deepseek:   { base_url: "https://api.deepseek.com/v1",        default_model: "deepseek-chat" },
  xai:        { base_url: "https://api.x.ai/v1",               default_model: "grok-3" },
  together:   { base_url: "https://api.together.xyz/v1",        default_model: "meta-llama/Llama-3-70b-chat-hf" },
  perplexity: { base_url: "https://api.perplexity.ai",         default_model: "sonar-pro" },
  ollama:     { base_url: "http://localhost:11434/v1",          default_model: "llama3.2" },
  lmstudio:   { base_url: "http://localhost:1234/v1",           default_model: "local-model" },
};

const DEFAULT_CONFIG: AppConfig = {
  default_provider: "claude",
  default_model: "claude-sonnet-4-6",
  providers: {},
};

export function loadConfig(): AppConfig {
  if (!fs.existsSync(CONFIG_FILE)) return { ...DEFAULT_CONFIG };
  const raw = fs.readFileSync(CONFIG_FILE, "utf-8");
  return { ...DEFAULT_CONFIG, ...JSON.parse(raw) };
}

export function saveConfig(cfg: AppConfig): void {
  fs.mkdirSync(CONFIG_DIR, { recursive: true });
  fs.writeFileSync(CONFIG_FILE, JSON.stringify(cfg, null, 2));
}

export function getApiKey(cfg: AppConfig, provider: string): string | undefined {
  const pdata = cfg.providers[provider] || {};
  return pdata.api_key || process.env[`${provider.toUpperCase()}_API_KEY`];
}

export function getBaseUrl(cfg: AppConfig, provider: string): string | undefined {
  const pdata = cfg.providers[provider] || {};
  if (pdata.base_url) return pdata.base_url;
  return OPENAI_COMPAT_PROVIDERS[provider]?.base_url;
}

export function getDefaultModel(provider: string): string {
  const defaults: Record<string, string> = {
    claude: "claude-sonnet-4-6",
    gemini: "gemini-2.0-flash",
    cohere: "command-r-plus",
    mistral: "mistral-large-latest",
  };
  return defaults[provider] ?? OPENAI_COMPAT_PROVIDERS[provider]?.default_model ?? "default";
}

export function ensureLogsDir(): string {
  fs.mkdirSync(LOGS_DIR, { recursive: true });
  return LOGS_DIR;
}
