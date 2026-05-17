import chalk from "chalk";

export function printBanner(): void {
  console.log(chalk.red.bold(`
██████╗ ███████╗██████╗ ████████╗ ██████╗ ███╗   ██╗ ██████╗ ███╗   ███╗ ██████╗ ██╗   ██╗███████╗
██╔══██╗██╔════╝██╔══██╗╚══██╔══╝██╔═══██╗████╗  ██║██╔═══██╗████╗ ████║██╔═══██╗██║   ██║██╔════╝
██████╔╝█████╗  ██║  ██║   ██║   ██║   ██║██╔██╗ ██║██║   ██║██╔████╔██║██║   ██║██║   ██║███████╗
██╔══██╗██╔══╝  ██║  ██║   ██║   ██║   ██║██║╚██╗██║██║   ██║██║╚██╔╝██║██║   ██║██║   ██║╚════██║
██║  ██║███████╗██████╔╝   ██║   ╚██████╔╝██║ ╚████║╚██████╔╝██║ ╚═╝ ██║╚██████╔╝╚██████╔╝███████║
╚═╝  ╚═╝╚══════╝╚═════╝    ╚═╝    ╚═════╝ ╚═╝  ╚═══╝ ╚═════╝ ╚═╝     ╚═╝ ╚═════╝  ╚═════╝ ╚══════╝`));
  console.log(chalk.dim("Autonomous multi-model coding agent — BYOK, no permission prompts\n"));
}

export function warnAutonomous(cwd: string, provider: string, model: string): void {
  console.log(chalk.yellow.bold("╔══════════════════════════════════════╗"));
  console.log(chalk.yellow.bold("║   ⚡  AUTONOMOUS MODE ACTIVE          ║"));
  console.log(chalk.yellow.bold("╚══════════════════════════════════════╝"));
  console.log(chalk.yellow("All actions execute WITHOUT confirmation."));
  console.log(chalk.yellow(`Files will be created, modified, and deleted.`));
  console.log(`Shell commands will run in: ${chalk.bold(cwd)}`);
  console.log(chalk.dim(`Provider: ${provider}  |  Model: ${model}\n`));
}

export function printBackup(dst: string): void {
  console.log(chalk.dim(`📦 Backup created: ${dst}`));
}

export function printToolCall(name: string, args: Record<string, unknown>): void {
  const argsStr = Object.entries(args)
    .map(([k, v]) => `${chalk.cyan(k)}=${chalk.green(String(v).slice(0, 80))}`)
    .join("  ");
  console.log(`${chalk.blue.bold("▶ " + name)}  ${argsStr}`);
}

export function printToolResult(name: string, result: string, isError: boolean): void {
  const preview = result.slice(0, 200) + (result.length > 200 ? "…" : "");
  if (isError) {
    console.log(chalk.red(`✗ ${name}: ${preview}`));
  } else {
    console.log(chalk.dim(`✓ ${name}: ${preview}`));
  }
}

export function printThinking(text: string): void {
  console.log(chalk.italic.dim(`  ${text.slice(0, 120)}`));
}

export function printFinal(text: string): void {
  console.log(chalk.green.bold("\n✅ Done"));
  console.log(chalk.green("─".repeat(60)));
  console.log(text);
  console.log(chalk.green("─".repeat(60)));
}

export function printError(msg: string): void {
  console.error(chalk.red.bold("Error: ") + msg);
}

export function printInfo(msg: string): void {
  console.log(chalk.dim(msg));
}

export function printModelsTable(models: Array<{ provider: string; model: string; type: string }>): void {
  console.log(chalk.bold("\nAvailable Models\n"));
  console.log(chalk.bold("Provider".padEnd(14) + "Model".padEnd(45) + "Type"));
  console.log("─".repeat(80));
  for (const m of models) {
    console.log(chalk.cyan(m.provider.padEnd(14)) + m.model.padEnd(45) + chalk.dim(m.type));
  }
}

export function printRule(label = ""): void {
  const line = "─".repeat(60);
  console.log(label ? chalk.red.bold(line + " " + label + " " + line) : chalk.dim(line));
}
