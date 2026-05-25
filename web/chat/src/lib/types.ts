export type Theme = "cyberpunk" | "professional" | "bold" | "warm";
export type LayoutMode = "split" | "terminal" | "dashboard" | "float";
export type CanvasTab = "code" | "doc" | "files" | "diagram";

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

export interface KnownModel {
  provider: string;
  model: string;
  type: string;
}

export type StreamEventType =
  | "thinking"
  | "tool_call"
  | "tool_result"
  | "done"
  | "error";

export interface StreamEvent {
  type: StreamEventType;
  text?: string;
  message?: string;
  id?: string;
  name?: string;
  args?: Record<string, unknown>;
  result?: string;
  error?: boolean;
  tokens_in?: number;
  tokens_out?: number;
}

export type MessageRole = "user" | "assistant";

export interface ChatMessage {
  id: string;
  role: MessageRole;
  content: string;
  events?: StreamEvent[];
  tokensIn?: number;
  tokensOut?: number;
  status?: "streaming" | "done" | "error";
  timestamp: number;
}

export interface SessionLog {
  id: string;
  file: string;
  task: string;
  provider: string;
  model: string;
  cwd: string;
  steps: number;
  mtime: number;
}

export interface SessionLogDetail {
  task: string;
  provider: string;
  model: string;
  cwd: string;
  log: Array<{
    iter: number;
    tool: string;
    args: Record<string, unknown>;
    result: string;
    error: boolean;
  }>;
}
