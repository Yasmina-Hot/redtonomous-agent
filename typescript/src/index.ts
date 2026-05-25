#!/usr/bin/env node
import { Command } from "commander";
import * as readline from "readline";
import fs from "fs";
import os from "os";
import path from "path";
import * as display from "./display.js";
import { loadConfig, saveConfig, getDefaultModel, getWakeWord } from "./config.js";
import { getAdapter, KNOWN_MODELS } from "./models/registry.js";
import { runAgent } from "./agent.js";

const program = new Command();

program
  .name("redtonomous")
  .description("Autonomous multi-model coding agent CLI — BYOK, no permission prompts")
  .version("0.1.0");

// ── bare invocation → REPL mode ───────────────────────────────────────────────

program
  .option("-m, --model <model>", "Model ID override (REPL mode)")
  .option("-p, --provider <provider>", "Provider override (REPL mode)")
  .option("-d, --dir <path>", "Working directory override (REPL mode)")
  .action(async (opts) => {
    // Only enter REPL if no subcommand was given
    if (process.argv.slice(2).some((a) => !a.startsWith("-"))) return;

    display.printBanner();

    const cfg = loadConfig();
    const provider = opts.provider ?? cfg.default_provider;
    const model = opts.model ?? cfg.default_model ?? getDefaultModel(provider);
    const cwd = path.resolve(opts.dir ?? process.cwd());
    const wake = getWakeWord(cfg) ?? "red";

    display.warnAutonomous(cwd, provider, model);
    display.printInfo(
      `Interactive mode — type a task and press Enter. 'exit' or Ctrl-C to quit. (wake word: ${wake})`
    );
    display.printRule();

    let adapter;
    try {
      adapter = await getAdapter(provider, model, cfg);
    } catch (e) {
      display.printError(String(e));
      process.exit(1);
    }

    const rl = readline.createInterface({ input: process.stdin, output: process.stdout });

    const askLine = (): Promise<string> =>
      new Promise((resolve) => {
        display.printReplPrompt(provider, model, cwd);
        rl.question(`${wake}> `, resolve);
      });

    const loop = async () => {
      while (true) {
        let line: string;
        try {
          line = (await askLine()).trim();
        } catch {
          display.printInfo("\nGoodbye.");
          break;
        }
        if (!line) continue;
        if (["exit", "quit", "q", ":q"].includes(line.toLowerCase())) {
          display.printInfo("Goodbye.");
          break;
        }
        await runAgent({
          task: line,
          adapter,
          provider,
          model,
          cwd,
          maxIterations: 100,
          backup: false,
          log: true,
        });
        display.printRule();
      }
      rl.close();
    };

    rl.on("close", () => { display.printInfo("\nGoodbye."); process.exit(0); });
    await loop();
  });

// ── run ───────────────────────────────────────────────────────────────────────

program
  .command("run <task>")
  .description("Run TASK autonomously using the configured model")
  .option("-m, --model <model>", "Model ID override")
  .option("-p, --provider <provider>", "Provider override")
  .option("-d, --dir <path>", "Working directory (default: cwd)")
  .option("--no-backup", "Skip auto-backup before run")
  .option("--max-iter <n>", "Max tool-call iterations", "100")
  .option("--no-log", "Skip session log")
  .option("-y, --yes", "Skip confirmation prompt")
  .action(async (task: string, opts) => {
    display.printBanner();

    const cfg = loadConfig();
    const provider = opts.provider ?? cfg.default_provider;
    const model = opts.model ?? cfg.default_model ?? getDefaultModel(provider);
    const cwd = path.resolve(opts.dir ?? process.cwd());

    display.warnAutonomous(cwd, provider, model);

    if (!opts.yes) {
      const confirmed = await confirm("Proceed? [Y/n] ");
      if (!confirmed) { display.printInfo("Aborted."); process.exit(0); }
    }

    let adapter;
    try {
      adapter = await getAdapter(provider, model, cfg);
    } catch (e) {
      display.printError(String(e));
      process.exit(1);
    }

    await runAgent({
      task,
      adapter,
      provider,
      model,
      cwd,
      maxIterations: parseInt(opts.maxIter),
      backup: opts.backup !== false,
      log: opts.log !== false,
    });
  });

// ── config ────────────────────────────────────────────────────────────────────

const configCmd = program.command("config").description("Manage configuration and API keys");

configCmd
  .command("set-key <provider> <key>")
  .description("Store an API key for PROVIDER")
  .action((provider: string, key: string) => {
    const cfg = loadConfig();
    cfg.providers[provider] ??= {};
    cfg.providers[provider].api_key = key;
    saveConfig(cfg);
    display.printInfo(`API key saved for '${provider}'.`);
  });

configCmd
  .command("set-model <model>")
  .option("-p, --provider <provider>")
  .description("Set the default model")
  .action((model: string, opts) => {
    const cfg = loadConfig();
    cfg.default_model = model;
    if (opts.provider) cfg.default_provider = opts.provider;
    saveConfig(cfg);
    display.printInfo(`Default model set to '${model}'.`);
  });

configCmd
  .command("set-wake-word <word>")
  .description("Set the wake word used in REPL mode and shell-setup")
  .action((word: string) => {
    if (!/^[a-zA-Z_][a-zA-Z0-9_]*$/.test(word)) {
      display.printError(
        `'${word}' is not a valid shell identifier. Use letters, digits, and underscores only.`
      );
      process.exit(1);
    }
    const cfg = loadConfig();
    cfg.wake_word = word;
    saveConfig(cfg);
    display.printInfo(
      `Wake word set to '${word}'. Run 'redtonomous shell-setup' to get your shell function.`
    );
  });

configCmd
  .command("add-provider <name> <base_url>")
  .option("--key <key>", "API key", "none")
  .option("--default-model <model>", "Default model", "default")
  .description("Add a custom OpenAI-compatible provider")
  .action((name: string, baseUrl: string, opts) => {
    const cfg = loadConfig();
    cfg.providers[name] = { type: "openai-compat", base_url: baseUrl, api_key: opts.key, default_model: opts.defaultModel };
    saveConfig(cfg);
    display.printInfo(`Provider '${name}' added (base_url=${baseUrl}).`);
  });

configCmd
  .command("show")
  .description("Print current configuration (masks API keys)")
  .action(() => {
    const cfg = loadConfig();
    for (const pdata of Object.values(cfg.providers)) {
      if (pdata.api_key && pdata.api_key !== "none") {
        pdata.api_key = pdata.api_key.slice(0, 8) + "…";
      }
    }
    console.log(JSON.stringify(cfg, null, 2));
  });

// ── models ────────────────────────────────────────────────────────────────────

program.command("models").description("List all known models").action(() => {
  display.printModelsTable(KNOWN_MODELS);
});

// ── shell-setup ───────────────────────────────────────────────────────────────

program
  .command("shell-setup")
  .description("Print (or install) the shell function for your wake word")
  .option("--shell <shell>", "Target shell: bash | zsh | fish | pwsh (default: auto-detect)")
  .option("--wake-word <word>", "Override the configured wake word")
  .option("--write", "Append the function directly to your shell rc file")
  .action((opts) => {
    const cfg = loadConfig();
    const wake = opts.wakeWord ?? getWakeWord(cfg);

    if (!wake) {
      display.printError("No wake word configured. Run: redtonomous config set-wake-word <word>");
      process.exit(1);
    }

    // Auto-detect shell
    let shellName: string = opts.shell ?? "";
    if (!shellName) {
      const shellEnv = process.env.SHELL ?? "";
      if (shellEnv.includes("fish"))  shellName = "fish";
      else if (shellEnv.includes("zsh")) shellName = "zsh";
      else if (shellEnv.toLowerCase().includes("pwsh") || shellEnv.toLowerCase().includes("powershell")) shellName = "pwsh";
      else shellName = "bash";
    }

    const snippets: Record<string, string> = {
      bash: `# Redtonomous wake word — add to ~/.bashrc\n${wake}() {\n  redtonomous run "$@"\n}`,
      zsh:  `# Redtonomous wake word — add to ~/.zshrc\n${wake}() {\n  redtonomous run "$@"\n}`,
      fish: `# Redtonomous wake word — save as ~/.config/fish/functions/${wake}.fish\nfunction ${wake}\n  redtonomous run $argv\nend`,
      pwsh: `# Redtonomous wake word — add to $PROFILE\nfunction ${wake} { redtonomous run @args }`,
    };
    const rcFiles: Record<string, string> = {
      bash: "~/.bashrc",
      zsh:  "~/.zshrc",
      fish: `~/.config/fish/functions/${wake}.fish`,
      pwsh: "$PROFILE",
    };

    const snippet = snippets[shellName] ?? snippets["bash"];
    const rcFile  = rcFiles[shellName]  ?? "~/.bashrc";

    console.log(`\nWake word: \x1b[1;31m${wake}\x1b[0m  \x1b[2m(${shellName})\x1b[0m\n`);
    console.log(`\x1b[2mAdd this to \x1b[1m${rcFile}\x1b[0m\x1b[2m:\x1b[0m\n`);
    console.log(`\x1b[32m${snippet}\x1b[0m\n`);

    if (opts.write) {
      writeSnippet(shellName, wake, snippet, rcFile);
    } else {
      const sourceCmd = `source ${rcFile}`;
      display.printInfo(`Then run: ${sourceCmd} (or open a new terminal)`);
      display.printInfo(`After that: ${wake} build me a FastAPI app`);
    }
  });

function writeSnippet(shellName: string, wake: string, snippet: string, rcFile: string): void {
  let target: string;
  if (shellName === "fish") {
    const fishDir = path.join(os.homedir(), ".config", "fish", "functions");
    fs.mkdirSync(fishDir, { recursive: true });
    target = path.join(fishDir, `${wake}.fish`);
  } else {
    target = rcFile.replace("~", os.homedir());
  }

  const markerStart = `# >>> redtonomous wake word (${wake}) >>>`;
  const markerEnd   = `# <<< redtonomous wake word (${wake}) <<<`;
  const block = `\n${markerStart}\n${snippet}\n${markerEnd}\n`;

  if (fs.existsSync(target)) {
    let content = fs.readFileSync(target, "utf-8");
    if (content.includes(markerStart)) {
      content = content.replace(
        new RegExp(`${escapeRegex(markerStart)}[\\s\\S]*?${escapeRegex(markerEnd)}`),
        block.trim()
      );
      fs.writeFileSync(target, content, "utf-8");
      display.printInfo(`Updated wake word in ${target}`);
      return;
    }
    fs.copyFileSync(target, target + ".bak");
  }

  fs.appendFileSync(target, block, "utf-8");
  display.printInfo(`Written to ${target}`);
  if (shellName !== "fish") display.printInfo(`Run: source ${target}`);
}

function escapeRegex(s: string): string {
  return s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

// ── auth ──────────────────────────────────────────────────────────────────────

program.command("auth").description("OAuth login for Claude (coming soon)").action(() => {
  display.printInfo("OAuth login is on the roadmap. Use 'config set-key claude <key>' for now.");
});

// ── helpers ───────────────────────────────────────────────────────────────────

function confirm(prompt: string): Promise<boolean> {
  return new Promise((resolve) => {
    const rl = readline.createInterface({ input: process.stdin, output: process.stdout });
    rl.question(prompt, (ans) => { rl.close(); resolve(ans.trim().toLowerCase() !== "n"); });
  });
}

program.parse(process.argv);
