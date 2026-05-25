export type Theme = "cyberpunk" | "professional" | "bold" | "warm";

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

export type StreamEventType = "thinking" | "tool_call" | "tool_result" | "done" | "error";

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
  test_id?: string;
  provider?: string;
}

export interface TestCase {
  id: string;
  name: string;
  prompt: string;
  expected: string;
  scoring: "llm" | "exact" | "regex" | "custom";
  rubric: string;
  tags: string[];
  suite: string;
}

export interface TestRun {
  id: string;
  testId: string;
  testName: string;
  provider: string;
  model: string;
  output: string;
  score?: number;
  passed?: boolean;
  durationMs?: number;
  events: StreamEvent[];
  status: "pending" | "running" | "done" | "error";
}

export interface PipelineNode {
  id: string;
  type: "input" | "agent" | "tool" | "router" | "output";
  label: string;
  config: {
    model?: string;
    provider?: string;
    system_prompt?: string;
    tools?: string[];
    condition?: string;
  };
  position: { x: number; y: number };
}

export interface PipelineEdge {
  id: string;
  source: string;
  target: string;
  label?: string;
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
