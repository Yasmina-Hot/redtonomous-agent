const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export async function fetchConfig() {
  const r = await fetch(`${API}/config`);
  return r.json();
}

export async function saveConfig(raw: object) {
  await fetch(`${API}/config`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ raw }),
  });
}

export async function fetchModels() {
  const r = await fetch(`${API}/models`);
  return r.json();
}

export async function fetchLogs() {
  const r = await fetch(`${API}/logs`);
  return r.json();
}

export async function fetchLog(id: string) {
  const r = await fetch(`${API}/logs/${id}`);
  return r.json();
}

export function createAgentWebSocket(
  task: string,
  provider: string,
  model: string,
  cwd: string,
  onEvent: (e: import("./types").StreamEvent) => void,
  onDone: () => void,
) {
  const runId = crypto.randomUUID();
  const wsUrl = new URL(`${API.replace("http", "ws")}/ws/${runId}`);
  wsUrl.searchParams.set("task", task);
  wsUrl.searchParams.set("provider", provider);
  wsUrl.searchParams.set("model", model);
  wsUrl.searchParams.set("cwd", cwd);

  const ws = new WebSocket(wsUrl.toString());

  ws.onmessage = (evt) => {
    try {
      const event = JSON.parse(evt.data) as import("./types").StreamEvent;
      onEvent(event);
      if (event.type === "done" || event.type === "error") {
        onDone();
        ws.close();
      }
    } catch {
      /* ignore malformed frames */
    }
  };

  ws.onerror = () => {
    onEvent({ type: "error", message: "WebSocket connection failed. Is the backend running?" });
    onDone();
  };

  return ws;
}
