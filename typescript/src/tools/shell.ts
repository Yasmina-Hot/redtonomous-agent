import { execSync } from "child_process";

export function executeCommand(args: { command: string; cwd?: string; timeout?: number }): string {
  const timeout = (args.timeout ?? 120) * 1000;
  try {
    const stdout = execSync(args.command, {
      cwd: args.cwd ?? process.cwd(),
      timeout,
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
    if (e.signal === "SIGTERM") parts.push(`ERROR: command timed out after ${args.timeout ?? 120}s`);
    else parts.push(`EXIT_CODE: ${e.status ?? 1}`);
    return parts.join("\n");
  }
}
