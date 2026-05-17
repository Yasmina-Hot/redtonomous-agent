#!/usr/bin/env node
import { Command } from "commander";
import * as readline from "readline";
import path from "path";
import * as display from "./display.js";
import { loadConfig, saveConfig, getDefaultModel } from "./config.js";
import { getAdapter, KNOWN_MODELS } from "./models/registry.js";
import { runAgent } from "./agent.js";

const program = new Command();

program
  .name("redtonomous")
  .description("Autonomous multi-model coding agent CLI — BYOK, no permission prompts")
  .version("0.1.0");

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
