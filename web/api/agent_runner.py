"""Async wrapper around the synchronous redtonomous agent loop."""
import asyncio
import json
import queue
import sys
import os
import threading
from datetime import datetime
from typing import AsyncGenerator

# Make the Python package importable
_PYTHON_SRC = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "python", "src")
)
if _PYTHON_SRC not in sys.path:
    sys.path.insert(0, _PYTHON_SRC)

from redtonomous.models.registry import get_adapter  # noqa: E402
from redtonomous.tools.definitions import TOOLS  # noqa: E402
from redtonomous.tools.executor import execute_tool  # noqa: E402
from redtonomous import config as redtonomous_config  # noqa: E402

SYSTEM_PROMPT = """\
You are Redtonomous — a fully autonomous software engineering agent.
You have unrestricted permission to read/write files, execute shell commands,
install packages, run builds, and fetch URLs within the working directory.

Rules:
1. Complete every task FULLY. Never stop halfway.
2. Make real changes. Do not just plan or describe.
3. Install missing dependencies with the shell tool if needed.
4. After writing code, run it to verify it works. Fix errors before finishing.
5. Think through the full dependency and execution order before starting.
6. Never ask the user for confirmation. Just do it.
7. When done, summarize exactly what was built/changed.

Working directory: {cwd}
Provider: {provider} | Model: {model}
"""

_SENTINEL = object()


async def run_agent_stream(
    task: str,
    provider: str,
    model: str,
    cwd: str,
    config_dict: dict,
    max_iterations: int = 100,
) -> AsyncGenerator[dict, None]:
    """Yield streaming events from the agent loop."""
    event_queue: queue.Queue = queue.Queue()

    def _thread():
        try:
            adapter = get_adapter(provider, model, config_dict)
        except Exception as e:
            event_queue.put({"type": "error", "message": f"Could not load adapter: {e}"})
            event_queue.put(_SENTINEL)
            return

        system = SYSTEM_PROMPT.format(cwd=cwd, provider=provider, model=model)
        messages: list[dict] = [{"role": "user", "content": task}]
        total_in = total_out = 0
        session_log: list[dict] = []

        try:
            for iteration in range(max_iterations):
                try:
                    resp = adapter.chat(messages=messages, tools=TOOLS, system=system)
                except Exception as e:
                    event_queue.put({"type": "error", "message": str(e)})
                    break

                total_in += resp.input_tokens or 0
                total_out += resp.output_tokens or 0

                if resp.text:
                    event_queue.put({"type": "thinking", "text": resp.text})

                no_tools = not resp.tool_calls
                terminal = resp.stop_reason in ("end_turn", "stop")
                if no_tools or (terminal and no_tools):
                    event_queue.put({
                        "type": "done",
                        "text": resp.text or "Task completed.",
                        "tokens_in": total_in,
                        "tokens_out": total_out,
                    })
                    break

                results: list[tuple[str, bool]] = []
                for tc in resp.tool_calls:
                    event_queue.put({
                        "type": "tool_call",
                        "id": tc.id,
                        "name": tc.name,
                        "args": tc.args,
                    })
                    result_str, is_error = execute_tool(tc.name, tc.args)
                    event_queue.put({
                        "type": "tool_result",
                        "id": tc.id,
                        "name": tc.name,
                        "result": result_str[:1000],
                        "error": is_error,
                    })
                    results.append((result_str, is_error))
                    session_log.append({
                        "iter": iteration,
                        "tool": tc.name,
                        "args": tc.args,
                        "result": result_str[:500],
                        "error": is_error,
                    })

                new_msgs = adapter.build_tool_result_messages(resp.tool_calls, results)
                messages.extend(new_msgs)
            else:
                event_queue.put({
                    "type": "error",
                    "message": f"Max iterations ({max_iterations}) reached.",
                })
        except Exception as e:
            import traceback
            event_queue.put({"type": "error", "message": traceback.format_exc()})

        # Persist session log
        if session_log:
            try:
                logs_dir = redtonomous_config.ensure_logs_dir()
                ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                log_path = os.path.join(logs_dir, f"session_{ts}.json")
                with open(log_path, "w") as f:
                    json.dump({
                        "task": task, "provider": provider, "model": model,
                        "cwd": cwd, "log": session_log,
                    }, f, indent=2)
            except Exception:
                pass

        event_queue.put(_SENTINEL)

    thread = threading.Thread(target=_thread, daemon=True)
    thread.start()

    loop = asyncio.get_event_loop()
    while True:
        event = await loop.run_in_executor(None, event_queue.get)
        if event is _SENTINEL:
            break
        yield event
        if event.get("type") in ("done", "error"):
            break
