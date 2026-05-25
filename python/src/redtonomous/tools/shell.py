import os
import re
import subprocess

# Hard ceiling so a buggy or malicious caller can't sit forever.
_MAX_TIMEOUT = 600

# Patterns matched against the raw command string. When matched AND the
# REDTONOMOUS_CONFIRM_DANGEROUS env var is set to a truthy value, we refuse to
# execute and return a structured error so the model can re-issue an explicit
# confirmation. Default behaviour (env var unset) is unchanged.
_DANGEROUS_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"\brm\s+-rf\s+/\S*"),   # rm -rf /, /etc, /home/user, etc.
    re.compile(r"\bmkfs(\.\w+)?\b"),
    re.compile(r"\bdd\s+if="),
    re.compile(r":\(\)\s*\{"),          # fork bomb
    re.compile(r">\s*/dev/sd[a-z]"),
    re.compile(r"\bchmod\s+(-R\s+)?0?777\b"),
    re.compile(r"\bchown\s+(-R\s+)?root\b"),
    re.compile(r"\bcurl\b[^|]*\|\s*(?:sudo\s+)?(?:ba)?sh"),
    re.compile(r"\bwget\b[^|]*\|\s*(?:sudo\s+)?(?:ba)?sh"),
]


def _is_dangerous(command: str) -> str | None:
    for pat in _DANGEROUS_PATTERNS:
        if pat.search(command):
            return pat.pattern
    return None


def execute_command(command: str, cwd: str | None = None, timeout: int = 120) -> str:
    if not isinstance(command, str) or not command.strip():
        return "ERROR: command must be a non-empty string"
    timeout = max(1, min(int(timeout or 120), _MAX_TIMEOUT))

    if os.environ.get("REDTONOMOUS_CONFIRM_DANGEROUS", "").lower() in ("1", "true", "yes"):
        match = _is_dangerous(command)
        if match:
            return (
                "ERROR: command matched a dangerous pattern "
                f"({match!r}) and REDTONOMOUS_CONFIRM_DANGEROUS is enabled. "
                "Re-issue with a narrower scope or unset the env var to proceed."
            )

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
