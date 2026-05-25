export async function fetchUrl(args: {
  url: string;
  method?: string;
  body?: string;
  headers?: Record<string, string>;
}): Promise<string> {
  const { default: fetch } = await import("node-fetch");
  try {
    const resp = await fetch(args.url, {
      method: args.method ?? "GET",
      headers: { "User-Agent": "redtonomous/0.1", ...(args.headers ?? {}) },
      body: args.body ?? undefined,
    });
    let text = await resp.text();
    if (text.length > 8000) text = text.slice(0, 8000) + `\n… (truncated, ${text.length} bytes total)`;
    return `STATUS: ${resp.status}\nCONTENT-TYPE: ${resp.headers.get("content-type") ?? ""}\n\n${text}`;
  } catch (e) {
    return `ERROR: ${String(e)}`;
  }
}
