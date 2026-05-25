import subprocess
import os


def execute_command(command: str, cwd: str | None = None, timeout: int = 120) -> str:
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=cwd or os.getcwd(),
            env={**os.environ, "TERM": "dumb"},
        )
        parts = []
        if result.stdout:
            parts.append(f"STDOUT:\n{result.stdout.rstrip()}")
        if result.stderr:
            parts.append(f"STDERR:\n{result.stderr.rstrip()}")
        parts.append(f"EXIT_CODE: {result.returncode}")
        return "\n".join(parts) if parts else f"EXIT_CODE: {result.returncode}"
    except subprocess.TimeoutExpired:
        return f"ERROR: command timed out after {timeout}s"
    except Exception as e:
        return f"ERROR: {e}"
