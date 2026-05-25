import { execSync } from "child_process";

const MAX_TIMEOUT_S = 600;

// See python/src/redtonomous/tools/shell.py for the canonical list — keep
// these patterns in sync across CLI implementations.
const DANGEROUS_PATTERNS: RegExp[] = [
  /\brm\s+-rf\s+\/\S*/,
  /\bmkfs(\.\w+)?\b/,
  /\bdd\s+if=/,
  /:\(\)\s*\{/,
  />\s*\/dev\/sd[a-z]/,
  /\bchmod\s+(-R\s+)?0?777\b/,
  /\bchown\s+(-R\s+)?root\b/,
  /\bcurl\b[^|]*\|\s*(?:sudo\s+)?(?:ba)?sh/,
  /\bwget\b[^|]*\|\s*(?:sudo\s+)?(?:ba)?sh/,
];

function isDangerous(command: string): string | null {
  for (const pat of DANGEROUS_PATTERNS) {
    if (pat.test(command)) return pat.source;
  }
  return null;
}

export function executeCommand(args: { command: string; cwd?: string; timeout?: number }): string {
  if (!args.command || !args.command.trim()) {
    return "ERROR: command must be a non-empty string";
  }
  const timeoutS = Math.max(1, Math.min(args.timeout ?? 120, MAX_TIMEOUT_S));

  const confirm = (process.env.REDTONOMOUS_CONFIRM_DANGEROUS ?? "").toLowerCase();
  if (confirm === "1" || confirm === "true" || confirm === "yes") {
    const match = isDangerous(args.command);
    if (match) {
      return (
        `ERROR: command matched a dangerous pattern (/${match}/) ` +
        "and REDTONOMOUS_CONFIRM_DANGEROUS is enabled. " +
        "Re-issue with a narrower scope or unset the env var to proceed."
      );
    }
  }

  const timeoutMs = timeoutS * 1000;
  try {
    const stdout = execSync(args.command, {
      cwd: args.cwd ?? process.cwd(),
      timeout: timeoutMs,
      encoding: "utf-8",
      env: { ...process.env, TERM: "dumb" },
      stdio: ["pipe", "pipe", "pipe"],
    });
    return `STDOUT:\n${stdout.trimEnd()}\nEXIT_CODE: 0`;
  } catch (err: unknown) {
    const e = err as { stdout?: string; stderr?: string; status?: number; signal?: string };
    const parts: string[] = [];
    if (e.stdout) parts.push(`STDOUT:\n${String(e.stdout).trimEnd()}`);
    if (e.stderr) parts.push(`STDERR:\n${String(e.stderr).trimEnd()}`);
    if (e.signal === "SIGTERM") parts.push(`ERROR: command timed out after ${timeoutS}s`);
    else parts.push(`EXIT_CODE: ${e.status ?? 1}`);
    return parts.join("\n");
  }
}
