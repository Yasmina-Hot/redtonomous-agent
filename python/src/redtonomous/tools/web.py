import requests


def fetch_url(url: str, method: str = "GET", body: str | None = None, headers: dict | None = None) -> str:
    try:
        h = {"User-Agent": "redtonomous/0.1", **(headers or {})}
        resp = requests.request(method, url, data=body, headers=h, timeout=30)
        content_type = resp.headers.get("content-type", "")
        text = resp.text
        if len(text) > 8000:
            text = text[:8000] + f"\n… (truncated, total {len(resp.content)} bytes)"
        return f"STATUS: {resp.status_code}\nCONTENT-TYPE: {content_type}\n\n{text}"
    except Exception as e:
        return f"ERROR: {e}"
