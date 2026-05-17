export interface ToolDef {
  name: string;
  description: string;
  parameters: {
    type: "object";
    properties: Record<string, unknown>;
    required: string[];
  };
}

export const TOOLS: ToolDef[] = [
  {
    name: "read_file",
    description: "Read the full contents of a file from disk.",
    parameters: {
      type: "object",
      properties: { path: { type: "string", description: "File path" } },
      required: ["path"],
    },
  },
  {
    name: "write_file",
    description: "Create or overwrite a file with the given content.",
    parameters: {
      type: "object",
      properties: {
        path: { type: "string" },
        content: { type: "string", description: "Full file content" },
      },
      required: ["path", "content"],
    },
  },
  {
    name: "append_file",
    description: "Append text to the end of an existing file.",
    parameters: {
      type: "object",
      properties: { path: { type: "string" }, content: { type: "string" } },
      required: ["path", "content"],
    },
  },
  {
    name: "list_directory",
    description: "List files and directories at a path.",
    parameters: {
      type: "object",
      properties: {
        path: { type: "string" },
        recursive: { type: "boolean", default: false },
      },
      required: ["path"],
    },
  },
  {
    name: "create_directory",
    description: "Create a directory and any missing parents.",
    parameters: {
      type: "object",
      properties: { path: { type: "string" } },
      required: ["path"],
    },
  },
  {
    name: "delete_file",
    description: "Delete a file or directory.",
    parameters: {
      type: "object",
      properties: { path: { type: "string" } },
      required: ["path"],
    },
  },
  {
    name: "move_file",
    description: "Move or rename a file or directory.",
    parameters: {
      type: "object",
      properties: { source: { type: "string" }, dest: { type: "string" } },
      required: ["source", "dest"],
    },
  },
  {
    name: "search_files",
    description: "Search for a text pattern in files under a directory.",
    parameters: {
      type: "object",
      properties: {
        pattern: { type: "string" },
        directory: { type: "string" },
        file_glob: { type: "string", default: "*" },
      },
      required: ["pattern", "directory"],
    },
  },
  {
    name: "execute_command",
    description: "Run a shell command and return stdout, stderr, and exit code.",
    parameters: {
      type: "object",
      properties: {
        command: { type: "string" },
        cwd: { type: "string" },
        timeout: { type: "number", default: 120 },
      },
      required: ["command"],
    },
  },
  {
    name: "fetch_url",
    description: "Make an HTTP request and return the response body.",
    parameters: {
      type: "object",
      properties: {
        url: { type: "string" },
        method: { type: "string", enum: ["GET", "POST", "PUT", "DELETE"], default: "GET" },
        body: { type: "string" },
        headers: { type: "object" },
      },
      required: ["url"],
    },
  },
];

export function toAnthropicTools(tools: ToolDef[]) {
  return tools.map((t) => ({
    name: t.name,
    description: t.description,
    input_schema: t.parameters,
  }));
}

export function toOpenAITools(tools: ToolDef[]) {
  return tools.map((t) => ({
    type: "function" as const,
    function: { name: t.name, description: t.description, parameters: t.parameters },
  }));
}

export function toGeminiDeclarations(tools: ToolDef[]) {
  return tools.map((t) => ({
    name: t.name,
    description: t.description,
    parameters: t.parameters,
  }));
}
