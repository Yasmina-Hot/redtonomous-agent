import fs from "fs";
import path from "path";

export function readFile(args: { path: string }): string {
  if (!fs.existsSync(args.path)) return `ERROR: ${args.path} does not exist`;
  if (!fs.statSync(args.path).isFile()) return `ERROR: ${args.path} is not a file`;
  try {
    return fs.readFileSync(args.path, "utf-8");
  } catch (e) {
    return `ERROR: ${String(e)}`;
  }
}

export function writeFile(args: { path: string; content: string }): string {
  try {
    fs.mkdirSync(path.dirname(args.path), { recursive: true });
    fs.writeFileSync(args.path, args.content, "utf-8");
    return `OK: wrote ${args.content.length} bytes to ${args.path}`;
  } catch (e) {
    return `ERROR: ${String(e)}`;
  }
}

export function appendFile(args: { path: string; content: string }): string {
  try {
    fs.mkdirSync(path.dirname(args.path), { recursive: true });
    fs.appendFileSync(args.path, args.content, "utf-8");
    return `OK: appended ${args.content.length} bytes to ${args.path}`;
  } catch (e) {
    return `ERROR: ${String(e)}`;
  }
}

function walkDir(dir: string, base: string): string[] {
  const entries: string[] = [];
  try {
    for (const e of fs.readdirSync(dir)) {
      if (e.startsWith(".")) continue;
      const full = path.join(dir, e);
      const rel = path.relative(base, full);
      if (fs.statSync(full).isDirectory()) {
        entries.push(...walkDir(full, base));
      } else {
        entries.push(rel);
      }
    }
  } catch { /* skip unreadable dirs */ }
  return entries;
}

export function listDirectory(args: { path: string; recursive?: boolean }): string {
  if (!fs.existsSync(args.path)) return `ERROR: ${args.path} does not exist`;
  if (!fs.statSync(args.path).isDirectory()) return `ERROR: not a directory`;
  try {
    if (args.recursive) return walkDir(args.path, args.path).join("\n") || "(empty)";
    const entries = fs.readdirSync(args.path).map((e) => {
      return fs.statSync(path.join(args.path, e)).isDirectory() ? e + "/" : e;
    });
    return entries.join("\n") || "(empty)";
  } catch (e) {
    return `ERROR: ${String(e)}`;
  }
}

export function createDirectory(args: { path: string }): string {
  try {
    fs.mkdirSync(args.path, { recursive: true });
    return `OK: created ${args.path}`;
  } catch (e) {
    return `ERROR: ${String(e)}`;
  }
}

export function deleteFile(args: { path: string }): string {
  if (!fs.existsSync(args.path)) return `ERROR: ${args.path} does not exist`;
  try {
    if (fs.statSync(args.path).isDirectory()) {
      fs.rmSync(args.path, { recursive: true, force: true });
      return `OK: deleted directory ${args.path}`;
    }
    fs.unlinkSync(args.path);
    return `OK: deleted ${args.path}`;
  } catch (e) {
    return `ERROR: ${String(e)}`;
  }
}

export function moveFile(args: { source: string; dest: string }): string {
  if (!fs.existsSync(args.source)) return `ERROR: ${args.source} does not exist`;
  try {
    fs.mkdirSync(path.dirname(args.dest), { recursive: true });
    fs.renameSync(args.source, args.dest);
    return `OK: moved ${args.source} → ${args.dest}`;
  } catch (e) {
    return `ERROR: ${String(e)}`;
  }
}

export function searchFiles(args: { pattern: string; directory: string; file_glob?: string }): string {
  if (!fs.existsSync(args.directory)) return `ERROR: ${args.directory} does not exist`;
  const results: string[] = [];

  let regex: RegExp;
  try {
    regex = new RegExp(args.pattern);
  } catch {
    regex = new RegExp(args.pattern.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"));
  }

  const glob = args.file_glob ?? "*";
  const globRegex = new RegExp("^" + glob.replace(/\./g, "\\.").replace(/\*/g, ".*") + "$");

  function walk(dir: string) {
    let entries: string[];
    try { entries = fs.readdirSync(dir); } catch { return; }
    for (const e of entries) {
      if (e.startsWith(".")) continue;
      const full = path.join(dir, e);
      let stat;
      try { stat = fs.statSync(full); } catch { continue; }
      if (stat.isDirectory()) { walk(full); continue; }
      if (!globRegex.test(e)) continue;
      try {
        const lines = fs.readFileSync(full, "utf-8").split("\n");
        for (let i = 0; i < lines.length; i++) {
          if (regex.test(lines[i])) {
            results.push(`${path.relative(args.directory, full)}:${i + 1}: ${lines[i].trim()}`);
          }
        }
      } catch { /* skip unreadable files */ }
    }
  }
  walk(args.directory);
  if (!results.length) return "No matches found";
  return results.slice(0, 200).join("\n");
}
