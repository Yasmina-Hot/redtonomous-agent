"""Bearer-token auth shared by HTTP and WebSocket routes.

Behavior:
  * If ``REDTONOMOUS_API_TOKEN`` is set in the environment, every protected
    endpoint requires a matching ``Authorization: Bearer <token>`` header
    (HTTP) or ``?token=<token>`` query param (WebSocket).
  * If unset, the API runs in "open dev" mode and prints a warning at startup.
  * The ``/health`` endpoint is always public.
"""
from __future__ import annotations

import hmac
import os

from fastapi import Header, HTTPException, WebSocket, status

ENV_VAR = "REDTONOMOUS_API_TOKEN"


def configured_token() -> str | None:
    tok = os.environ.get(ENV_VAR, "").strip()
    return tok or None


def auth_warning_banner() -> str | None:
    if configured_token() is None:
        return (
            "REDTONOMOUS_API_TOKEN is not set — the API is running in OPEN DEV MODE. "
            "Do NOT expose this port to untrusted networks. Set the env var to require "
            "bearer auth on all sensitive endpoints."
        )
    return None


def _check(token: str | None) -> None:
    expected = configured_token()
    if expected is None:
        return  # open dev mode
    if token is None or not hmac.compare_digest(token, expected):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API token",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def require_token(
    authorization: str | None = Header(default=None),
) -> None:
    """FastAPI dependency for HTTP routes."""
    token: str | None = None
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization.split(" ", 1)[1].strip()
    _check(token)


async def require_ws_token(ws: WebSocket, token: str = "") -> bool:
    """Validate a WebSocket handshake. Closes the socket on failure.

    Returns True if the connection should proceed, False if it has been closed.
    """
    expected = configured_token()
    if expected is None:
        return True
    # Allow either query param ?token=... or Authorization header.
    candidate = token
    if not candidate:
        auth_hdr = ws.headers.get("authorization", "")
        if auth_hdr.lower().startswith("bearer "):
            candidate = auth_hdr.split(" ", 1)[1].strip()
    if not candidate or not hmac.compare_digest(candidate, expected):
        await ws.close(code=4401, reason="unauthorized")
        return False
    return True
