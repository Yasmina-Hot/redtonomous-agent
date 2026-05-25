"""Canonical tool definitions — provider-agnostic JSON Schema format."""

TOOLS: list[dict] = [
    {
        "name": "read_file",
        "description": "Read the full contents of a file from disk.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Absolute or relative file path"},
            },
            "required": ["path"],
        },
    },
    {
        "name": "write_file",
        "description": "Create or overwrite a file with the given content.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "File path to write"},
                "content": {"type": "string", "description": "Full file content"},
            },
            "required": ["path", "content"],
        },
    },
    {
        "name": "append_file",
        "description": "Append text to the end of an existing file (creates if missing).",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "content": {"type": "string"},
            },
            "required": ["path", "content"],
        },
    },
    {
        "name": "list_directory",
        "description": "List files and directories at a path.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Directory path"},
                "recursive": {"type": "boolean", "description": "Recurse into subdirectories", "default": False},
            },
            "required": ["path"],
        },
    },
    {
        "name": "create_directory",
        "description": "Create a directory (and any missing parents).",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
            },
            "required": ["path"],
        },
    },
    {
        "name": "delete_file",
        "description": "Delete a file or empty directory.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
            },
            "required": ["path"],
        },
    },
    {
        "name": "move_file",
        "description": "Move or rename a file or directory.",
        "parameters": {
            "type": "object",
            "properties": {
                "source": {"type": "string"},
                "dest": {"type": "string"},
            },
            "required": ["source", "dest"],
        },
    },
    {
        "name": "search_files",
        "description": "Search for a text pattern in files under a directory.",
        "parameters": {
            "type": "object",
            "properties": {
                "pattern": {"type": "string", "description": "Text or regex to search for"},
                "directory": {"type": "string", "description": "Root directory to search"},
                "file_glob": {"type": "string", "description": "Glob filter e.g. '*.py'", "default": "*"},
            },
            "required": ["pattern", "directory"],
        },
    },
    {
        "name": "execute_command",
        "description": "Run a shell command and return stdout, stderr, and exit code.",
        "parameters": {
            "type": "object",
            "properties": {
                "command": {"type": "string", "description": "Shell command to execute"},
                "cwd": {"type": "string", "description": "Working directory (optional)"},
                "timeout": {"type": "integer", "description": "Timeout in seconds (default 120)", "default": 120},
            },
            "required": ["command"],
        },
    },
    {
        "name": "fetch_url",
        "description": "Make an HTTP request and return the response body.",
        "parameters": {
            "type": "object",
            "properties": {
                "url": {"type": "string"},
                "method": {"type": "string", "enum": ["GET", "POST", "PUT", "DELETE"], "default": "GET"},
                "body": {"type": "string", "description": "Request body for POST/PUT"},
                "headers": {"type": "object", "description": "Extra HTTP headers"},
            },
            "required": ["url"],
        },
    },
]


def to_anthropic_tools(tools: list[dict]) -> list[dict]:
    return [
        {
            "name": t["name"],
            "description": t["description"],
            "input_schema": t["parameters"],
        }
        for t in tools
    ]


def to_openai_tools(tools: list[dict]) -> list[dict]:
    return [
        {
            "type": "function",
            "function": {
                "name": t["name"],
                "description": t["description"],
                "parameters": t["parameters"],
            },
        }
        for t in tools
    ]


def to_gemini_declarations(tools: list[dict]) -> list[dict]:
    """Return raw dicts for Gemini FunctionDeclaration construction."""
    return [
        {
            "name": t["name"],
            "description": t["description"],
            "parameters": t["parameters"],
        }
        for t in tools
    ]
