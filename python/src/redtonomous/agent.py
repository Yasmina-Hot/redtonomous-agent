import json
import shutil
from datetime import datetime
from pathlib import Path

from . import display
from .models.base import ModelAdapter, ToolCall
from .models.claude import ClaudeAdapter
from .models.gemini import GeminiAdapter
from .models.mistral import MistralAdapter
from .models.cohere import CohereAdapter
from .models.openai_compat import OpenAICompatAdapter
from .tools.definitions import TOOLS
from .tools.executor import execute_tool

SYSTEM_PROMPT = """\
You are Redtonomous — a fully autonomous software engineering agent.
You have unrestricted permission to read/write files, execute shell commands,
install packages, run builds, and fetch URLs within the working directory.

Rules:
1. Complete every task FULLY. Never stop halfway.
2. Make real changes. Do not just plan or describe.
3. Install missing dependencies with the shell tool if needed.
4. After writing code, run it to verify it works. Fix any errors before finishing.
5. Think through the full dependency and execution order before starting.
6. Never ask the user for confirmation. Just do it.
7. When done, summarize exactly what was built/changed.

Working directory: {cwd}
Provider: {provider} | Model: {model}
"""


def _build_tool_result_messages(
    adapter: ModelAdapter,
    tool_calls: list[ToolCall],
    results: list[tuple[str, bool]],
) -> list[dict]:
    if isinstance(adapter, ClaudeAdapter):
        return ClaudeAdapter.build_tool_result_message(tool_calls, results)
    if isinstance(adapter, GeminiAdapter):
        return GeminiAdapter.build_tool_result_message(tool_calls, results)
    if isinstance(adapter, MistralAdapter):
        return MistralAdapter.build_tool_result_message(tool_calls, results)
    if isinstance(adapter, CohereAdapter):
        return CohereAdapter.build_tool_result_message(tool_calls, results)
    # Default: OpenAI-compat
    return OpenAICompatAdapter.build_tool_result_message(tool_calls, results)


def run(
    task: str,
    adapter: ModelAdapter,
    provider: str,
    model: str,
    cwd: str,
    max_iterations: int = 100,
    backup: bool = True,
    log: bool = True,
) -> None:
    if backup:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        dst = f"{cwd.rstrip('/')}_backup_{ts}"
        try:
            shutil.copytree(cwd, dst, dirs_exist_ok=False)
            display.print_backup(cwd, dst)
        except Exception as e:
            display.print_info(f"Backup skipped: {e}")

    system = SYSTEM_PROMPT.format(cwd=cwd, provider=provider, model=model)
    messages: list[dict] = [{"role": "user", "content": task}]
    session_log: list[dict] = []
    total_in = total_out = 0

    display.console.rule("[bold red]Redtonomous[/bold red]")
    display.print_info(f"Task: {task}")
    display.print_info(f"Model: {provider}/{model}  |  Dir: {cwd}  |  Max iterations: {max_iterations}")
    display.console.rule()

    for iteration in range(max_iterations):
        resp = adapter.chat(messages=messages, tools=TOOLS, system=system)
        total_in += resp.input_tokens
        total_out += resp.output_tokens

        if resp.text:
            display.print_thinking(resp.text[:120])

        if resp.stop_reason in ("end_turn", "stop") and not resp.tool_calls:
            display.print_final(resp.text or "(Task complete)")
            break

        if not resp.tool_calls:
            display.print_final(resp.text or "(Task complete — no more tool calls)")
            break

        results: list[tuple[str, bool]] = []
        for tc in resp.tool_calls:
            display.print_tool_call(tc.name, tc.args)
            result, is_error = execute_tool(tc.name, tc.args)
            display.print_tool_result(tc.name, result, is_error)
            results.append((result, is_error))
            session_log.append({
                "iter": iteration,
                "tool": tc.name,
                "args": tc.args,
                "result": result[:500],
                "error": is_error,
            })

        new_msgs = _build_tool_result_messages(adapter, resp.tool_calls, results)
        messages.extend(new_msgs)

    else:
        display.print_error(f"Reached max iterations ({max_iterations}). Task may be incomplete.")

    display.print_info(f"Tokens used — input: {total_in}  output: {total_out}")

    if log and session_log:
        from . import config as cfg_module
        logs_dir = cfg_module.ensure_logs_dir()
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = logs_dir / f"session_{ts}.json"
        with open(log_file, "w") as f:
            json.dump({"task": task, "provider": provider, "model": model, "cwd": cwd, "log": session_log}, f, indent=2)
        display.print_info(f"Session log: {log_file}")
