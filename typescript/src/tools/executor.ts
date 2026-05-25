import {
  readFile, writeFile, appendFile, listDirectory,
  createDirectory, deleteFile, moveFile, searchFiles,
} from "./filesystem.js";
import { executeCommand } from "./shell.js";
import { fetchUrl } from "./web.js";

type ToolArgs = Record<string, unknown>;

export async function executeTool(name: string, args: ToolArgs): Promise<[string, boolean]> {
  try {
    let result: string;
    switch (name) {
      case "read_file":       result = readFile(args as any); break;
      case "write_file":      result = writeFile(args as any); break;
      case "append_file":     result = appendFile(args as any); break;
      case "list_directory":  result = listDirectory(args as any); break;
      case "create_directory":result = createDirectory(args as any); break;
      case "delete_file":     result = deleteFile(args as any); break;
      case "move_file":       result = moveFile(args as any); break;
      case "search_files":    result = searchFiles(args as any); break;
      case "execute_command": result = executeCommand(args as any); break;
      case "fetch_url":       result = await fetchUrl(args as any); break;
      default:                return [`ERROR: unknown tool '${name}'`, true];
    }
    const isError = result.startsWith("ERROR:");
    return [result, isError];
  } catch (e) {
    return [`ERROR: ${String(e)}`, true];
  }
}
