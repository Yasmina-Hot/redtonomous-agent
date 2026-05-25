import type {
  AppConfig,
  KnownModel,
  SessionLog,
  SessionLogDetail,
  StreamEvent,
} from "./types";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const TOKEN = process.env.NEXT_PUBLIC_API_TOKEN ?? "";

function authHeaders(init?: HeadersInit): HeadersInit {
  const h = new Headers(init);
  if (TOKEN) h.set("Authorization", `Bearer ${TOKEN}`);
  return h;
}

async function getJSON<T>(path: string): Promise<T> {
  const r = await fetch(`${API}${path}`, { headers: authHeaders() });
  if (!r.ok) throw new Error(`GET ${path} → ${r.status} ${r.statusText}`);
  return (await r.json()) as T;
}

export async function fetchConfig(): Promise<AppConfig> {
  return getJSON<AppConfig>("/config");
}

export async function saveConfig(raw: object): Promise<void> {
  const r = await fetch(`${API}/config`, {
    method: "POST",
    headers: authHeaders({ "Content-Type": "application/json" }),
    body: JSON.stringify({ raw }),
  });
  if (!r.ok) throw new Error(`POST /config → ${r.status} ${r.statusText}`);
}

export async function fetchModels(): Promise<KnownModel[]> {
  return getJSON<KnownModel[]>("/models");
}

export interface LogsPage {
  total: number;
  offset: number;
  limit: number;
  items: SessionLog[];
}

export async function fetchLogs(limit = 50, offset = 0): Promise<SessionLog[]> {
  const page = await getJSON<LogsPage>(
    `/logs?limit=${limit}&offset=${offset}`,
  );
  return page.items;
}

export async function fetchLog(id: string): Promise<SessionLogDetail> {
  return getJSON<SessionLogDetail>(`/logs/${encodeURIComponent(id)}`);
}

/**
 * Open the agent WebSocket. Returns a controller exposing `close()` so the
 * caller can cancel a stream. On a clean done/error frame the socket closes
 * normally; on an unclean network drop the helper will retry up to 3 times
 * with exponential backoff before reporting an error.
 */
export interface AgentSocket {
  close: () => void;
}

export function createAgentWebSocket(
  task: string,
  provider: string,
  model: string,
  cwd: string,
  onEvent: (e: StreamEvent) => void,
  onDone: () => void,
): AgentSocket {
  const runId = crypto.randomUUID();
  const base = new URL(`${API.replace(/^http/, "ws")}/ws/${runId}`);
  base.searchParams.set("task", task);
  base.searchParams.set("provider", provider);
  base.searchParams.set("model", model);
  base.searchParams.set("cwd", cwd);
  if (TOKEN) base.searchParams.set("token", TOKEN);

  let ws: WebSocket | null = null;
  let attempt = 0;
  let cleanlyClosed = false;
  let finished = false;
  const maxAttempts = 3;
  const backoffs = [1000, 2000, 4000];

  const finish = (e?: StreamEvent) => {
    if (finished) return;
    finished = true;
    if (e) onEvent(e);
    onDone();
  };

  const connect = () => {
    ws = new WebSocket(base.toString());
    ws.onmessage = (evt) => {
      let event: StreamEvent | null = null;
      try {
        event = JSON.parse(evt.data) as StreamEvent;
      } catch {
        return;
      }
      onEvent(event);
      if (event.type === "done" || event.type === "error") {
        cleanlyClosed = true;
        finish();
        ws?.close();
      }
    };
    ws.onerror = () => {
      // onerror always precedes onclose; let onclose decide whether to retry.
    };
    ws.onclose = (evt) => {
      if (cleanlyClosed || finished) return;
      // 4401 = unauthorized handshake — don't retry.
      if (evt.code === 4401) {
        finish({ type: "error", message: "Unauthorized — check API token." });
        return;
      }
      if (attempt < maxAttempts) {
        const delay = backoffs[attempt] ?? 4000;
        attempt += 1;
        onEvent({
          type: "error",
          message: `Connection lost — retry ${attempt}/${maxAttempts} in ${delay}ms…`,
        });
        setTimeout(connect, delay);
      } else {
        finish({
          type: "error",
          message: "WebSocket connection failed after retries.",
        });
      }
    };
  };

  connect();

  return {
    close: () => {
      cleanlyClosed = true;
      finished = true;
      ws?.close();
    },
  };
}
