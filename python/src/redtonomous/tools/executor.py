from .filesystem import (
    read_file, write_file, append_file, list_directory,
    create_directory, delete_file, move_file, search_files,
)
from .shell import execute_command
from .web import fetch_url

_DISPATCH = {
    "read_file": lambda a: read_file(**a),
    "write_file": lambda a: write_file(**a),
    "append_file": lambda a: append_file(**a),
    "list_directory": lambda a: list_directory(**a),
    "create_directory": lambda a: create_directory(**a),
    "delete_file": lambda a: delete_file(**a),
    "move_file": lambda a: move_file(**a),
    "search_files": lambda a: search_files(**a),
    "execute_command": lambda a: execute_command(**a),
    "fetch_url": lambda a: fetch_url(**a),
}


def execute_tool(name: str, args: dict) -> tuple[str, bool]:
    """Returns (result_text, is_error)."""
    fn = _DISPATCH.get(name)
    if fn is None:
        return f"ERROR: unknown tool '{name}'", True
    try:
        result = fn(args)
        is_error = isinstance(result, str) and result.startswith("ERROR:")
        return str(result), is_error
    except Exception as e:
        return f"ERROR: {e}", True
