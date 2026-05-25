import fnmatch
import os
import re
import shutil
from pathlib import Path


def read_file(path: str) -> str:
    p = Path(path)
    if not p.exists():
        return f"ERROR: {path} does not exist"
    if not p.is_file():
        return f"ERROR: {path} is not a file"
    try:
        return p.read_text(errors="replace")
    except Exception as e:
        return f"ERROR: {e}"


def write_file(path: str, content: str) -> str:
    try:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content)
        return f"OK: wrote {len(content)} bytes to {path}"
    except Exception as e:
        return f"ERROR: {e}"


def append_file(path: str, content: str) -> str:
    try:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "a") as f:
            f.write(content)
        return f"OK: appended {len(content)} bytes to {path}"
    except Exception as e:
        return f"ERROR: {e}"


def list_directory(path: str, recursive: bool = False) -> str:
    p = Path(path)
    if not p.exists():
        return f"ERROR: {path} does not exist"
    if not p.is_dir():
        return f"ERROR: {path} is not a directory"
    if recursive:
        entries = []
        for root, dirs, files in os.walk(p):
            # skip hidden dirs
            dirs[:] = [d for d in dirs if not d.startswith(".")]
            rel = Path(root).relative_to(p)
            for f in files:
                entries.append(str(rel / f))
        return "\n".join(sorted(entries)) or "(empty)"
    entries = sorted(str(e.name) + ("/" if e.is_dir() else "") for e in p.iterdir())
    return "\n".join(entries) or "(empty)"


def create_directory(path: str) -> str:
    Path(path).mkdir(parents=True, exist_ok=True)
    return f"OK: created {path}"


def delete_file(path: str) -> str:
    p = Path(path)
    if not p.exists():
        return f"ERROR: {path} does not exist"
    if p.is_dir():
        shutil.rmtree(p)
        return f"OK: deleted directory {path}"
    p.unlink()
    return f"OK: deleted {path}"


def move_file(source: str, dest: str) -> str:
    s, d = Path(source), Path(dest)
    if not s.exists():
        return f"ERROR: {source} does not exist"
    d.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(s), str(d))
    return f"OK: moved {source} → {dest}"


def search_files(pattern: str, directory: str, file_glob: str = "*") -> str:
    results = []
    root = Path(directory)
    if not root.exists():
        return f"ERROR: {directory} does not exist"
    try:
        regex = re.compile(pattern)
    except re.error as e:
        return f"ERROR: invalid regex {pattern!r}: {e}"

    for dirpath, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if not d.startswith(".")]
        for fname in files:
            if not fnmatch.fnmatch(fname, file_glob):
                continue
            fpath = Path(dirpath) / fname
            try:
                for lineno, line in enumerate(fpath.read_text(errors="replace").splitlines(), 1):
                    if regex.search(line):
                        rel = fpath.relative_to(root)
                        results.append(f"{rel}:{lineno}: {line.strip()}")
            except Exception:
                continue
    if not results:
        return "No matches found"
    return "\n".join(results[:200])
