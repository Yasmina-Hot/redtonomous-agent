import fs from "fs";
import path from "path";
import { ModelAdapter, ToolCall } from "./models/base.js";
import { TOOLS } from "./tools/definitions.js";
import { executeTool } from "./tools/executor.js";
import * as display from "./display.js";
import { ensureLogsDir } from "./config.js";

const SYSTEM_PROMPT = `You are Redtonomous — a fully autonomous software engineering agent.
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
Provider: {provider} | Model: {model}`;

function copyDir(src: string, dest: string): void {
  fs.mkdirSync(dest, { recursive: true });
  for (const entry of fs.readdirSync(src, { withFileTypes: true })) {
    const srcPath = path.join(src, entry.name);
    const destPath = path.join(dest, entry.name);
    if (entry.isDirectory()) copyDir(srcPath, destPath);
    else fs.copyFileSync(srcPath, destPath);
  }
}

export async function runAgent(opts: {
  task: string;
  adapter: ModelAdapter;
  provider: string;
  model: string;
  cwd: string;
  maxIterations?: number;
  backup?: boolean;
  log?: boolean;
}): Promise<void> {
  const { task, adapter, provider, model, cwd } = opts;
  const maxIterations = opts.maxIterations ?? 100;

  if (opts.backup !== false) {
    const ts = new Date().toISOString().replace(/[:.]/g, "-");
    const dst = `${cwd}_backup_${ts}`;
    try {
      copyDir(cwd, dst);
      display.printBackup(dst);
    } catch (e) {
      display.printInfo(`Backup skipped: ${String(e)}`);
    }
  }

  const system = SYSTEM_PROMPT
    .replace("{cwd}", cwd)
    .replace("{provider}", provider)
    .replace("{model}", model);

  const messages: { role: string; content: unknown }[] = [
    { role: "user", content: task },
  ];

  const sessionLog: unknown[] = [];
  let totalIn = 0, totalOut = 0;

  display.printRule("Redtonomous");
  display.printInfo(`Task: ${task}`);
  display.printInfo(`Model: ${provider}/${model}  |  Dir: ${cwd}  |  Max iterations: ${maxIterations}`);
  display.printRule();

  for (let iter = 0; iter < maxIterations; iter++) {
    const resp = await adapter.chat(messages, TOOLS, system);
    totalIn += resp.inputTokens;
    totalOut += resp.outputTokens;

    if (resp.text) display.printThinking(resp.text);

    if (resp.stopReason === "end_turn" || resp.toolCalls.length === 0) {
      display.printFinal(resp.text || "(Task complete)");
      break;
    }

    const results: [string, boolean][] = [];
    for (const tc of resp.toolCalls) {
      display.printToolCall(tc.name, tc.args);
      const [result, isError] = await executeTool(tc.name, tc.args);
      display.printToolResult(tc.name, result, isError);
      results.push([result, isError]);
      sessionLog.push({ iter, tool: tc.name, args: tc.args, result: result.slice(0, 500), error: isError });
    }

    const newMsgs = adapter.buildToolResultMessages(resp.toolCalls, results);
    messages.push(...newMsgs);

    if (iter === maxIterations - 1) {
      display.printError(`Reached max iterations (${maxIterations}). Task may be incomplete.`);
    }
  }

  display.printInfo(`Tokens used — input: ${totalIn}  output: ${totalOut}`);

  if (opts.log !== false && sessionLog.length > 0) {
    const logsDir = ensureLogsDir();
    const ts = new Date().toISOString().replace(/[:.]/g, "-");
    const logFile = path.join(logsDir, `session_${ts}.json`);
    fs.writeFileSync(logFile, JSON.stringify({ task, provider, model, cwd, log: sessionLog }, null, 2));
    display.printInfo(`Session log: ${logFile}`);
  }
}
