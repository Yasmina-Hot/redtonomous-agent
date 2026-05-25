"""Context enrichment — memory file, conventions, @file refs, repo map, URLs.

These functions all *augment* the user's task with extra context the model
should know about before it starts. They're intentionally cheap: every loader
caps at a few KB so an enormous repo doesn't blow the prompt budget.
"""
from __future__ import annotations

import os
import re
from pathlib import Path

# Files in cwd that an agent should treat as project memory / conventions.
MEMORY_FILES = ("REDTONOMOUS.md", "CLAUDE.md", "AGENTS.md")
CONVENTIONS_FILES = (".redtonomousrules", ".cursorrules", ".aiderrules")

# Cap each loader so a single context block can't dominate the prompt.
_MAX_MEMORY_BYTES = 16 * 1024
_MAX_CONVENTIONS_BYTES = 8 * 1024
_MAX_FILE_REF_BYTES = 32 * 1024
_MAX_REPO_MAP_FILES = 80
_MAX_URL_BYTES = 16 * 1024


def load_memory(cwd: str) -> str:
    """Return the first existing memory file's contents (truncated)."""
    for name in MEMORY_FILES:
        path = Path(cwd) / name
        if path.is_file():
            try:
                text = path.read_text(errors="replace")[:_MAX_MEMORY_BYTES]
            except OSError:
                continue
            return f"--- {name} ---\n{text}"
    return ""


def load_conventions(cwd: str) -> str:
    for name in CONVENTIONS_FILES:
        path = Path(cwd) / name
        if path.is_file():
            try:
                text = path.read_text(errors="replace")[:_MAX_CONVENTIONS_BYTES]
            except OSError:
                continue
            return f"--- {name} ---\n{text}"
    return ""


_REF_RE = re.compile(r"(?:^|[\s(])@([\w./-]+)")


def expand_file_refs(task: str, cwd: str) -> tuple[str, str]:
    """Find ``@path/to/file`` mentions in ``task`` and load their contents.

    Returns ``(task_unchanged, references_block)`` so the caller can choose
    whether to prepend or append.  Files that don't exist are silently
    skipped — we don't want to crash on a typo.
    """
    seen: dict[str, str] = {}
    for match in _REF_RE.finditer(task):
        ref = match.group(1)
        if ref in seen:
            continue
        candidate = (Path(cwd) / ref).resolve()
        try:
            candidate.relative_to(Path(cwd).resolve())
        except ValueError:
            continue
        if candidate.is_file():
            try:
                seen[ref] = candidate.read_text(errors="replace")
            except OSError:
                continue
        elif candidate.is_dir():
            entries = []
            for entry in sorted(candidate.iterdir()):
                entries.append(entry.name + ("/" if entry.is_dir() else ""))
                if len(entries) >= 50:
                    break
            seen[ref] = "(directory listing)\n" + "\n".join(entries)
    if not seen:
        return task, ""
    total = 0
    parts: list[str] = []
    for ref, body in seen.items():
        chunk = f"\n--- @{ref} ---\n{body}\n"
        if total + len(chunk) > _MAX_FILE_REF_BYTES:
            chunk = chunk[: _MAX_FILE_REF_BYTES - total] + "\n...(truncated)\n"
        parts.append(chunk)
        total += len(chunk)
        if total >= _MAX_FILE_REF_BYTES:
            break
    return task, "Referenced files:" + "".join(parts)


# Top-of-file lines to extract for the repo map. Generous-but-bounded.
_REPO_MAP_HEAD_LINES = 12

# Files we never include in the repo map.
_REPO_MAP_SKIP_DIRS = {".git", "node_modules", ".next", "dist", "build", "venv", ".venv", "__pycache__", ".pytest_cache", ".mypy_cache"}
_REPO_MAP_SKIP_SUFFIXES = (".pyc", ".pyo", ".class", ".jpg", ".png", ".gif", ".pdf", ".zip", ".tar", ".gz", ".lock", ".lockb")


def build_repo_map(cwd: str) -> str:
    """Aider-style: list the most "interesting" files plus their first lines.

    Interest = code-extension files at low directory depth. Hard cap at
    ``_MAX_REPO_MAP_FILES`` entries so a huge monorepo doesn't blow up the
    prompt.
    """
    root = Path(cwd).resolve()
    if not root.is_dir():
        return ""

    candidates: list[Path] = []
    for dirpath, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in _REPO_MAP_SKIP_DIRS and not d.startswith(".")]
        depth = len(Path(dirpath).relative_to(root).parts)
        for fname in files:
            if fname.endswith(_REPO_MAP_SKIP_SUFFIXES):
                continue
            candidates.append(Path(dirpath) / fname)
        # Cheap budget cap: stop walking once we've got enough breadth.
        if len(candidates) > _MAX_REPO_MAP_FILES * 4 and depth >= 2:
            break

    # Sort by depth then by name so top-level / short paths come first.
    def _rank(p: Path) -> tuple[int, str]:
        rel = p.relative_to(root)
        return (len(rel.parts), str(rel))

    candidates.sort(key=_rank)
    chosen = candidates[:_MAX_REPO_MAP_FILES]
    if not chosen:
        return ""

    lines: list[str] = ["Repo map (top files + first lines):"]
    for p in chosen:
        rel = p.relative_to(root)
        head = ""
        try:
            text = p.read_text(errors="replace")
            head_lines = text.splitlines()[:_REPO_MAP_HEAD_LINES]
            head = "\n".join(f"    {ln}" for ln in head_lines if ln.strip())
        except OSError:
            head = ""
        lines.append(f"  {rel}")
        if head:
            lines.append(head)
    return "\n".join(lines)


def fetch_url_context(url: str) -> str:
    """Pull a URL and return a context block (capped at ~16 KB)."""
    from .tools.web import fetch_url

    body = fetch_url(url=url, method="GET")
    return f"--- {url} ---\n{body[:_MAX_URL_BYTES]}"


def assemble(
    *,
    cwd: str,
    task: str,
    include_memory: bool = True,
    include_conventions: bool = True,
    include_repo_map: bool = False,
    extra_urls: list[str] | None = None,
) -> tuple[str, str]:
    """Compose the context blocks and the expanded task.

    Returns ``(extra_system_block, expanded_task_or_user_block)``. Callers
    typically append ``extra_system_block`` to the system prompt and use the
    second return value as the *first user message* — which preserves the
    structure existing model adapters expect.
    """
    blocks: list[str] = []
    if include_memory:
        mem = load_memory(cwd)
        if mem:
            blocks.append(mem)
    if include_conventions:
        conv = load_conventions(cwd)
        if conv:
            blocks.append(conv)
    if include_repo_map:
        rmap = build_repo_map(cwd)
        if rmap:
            blocks.append(rmap)
    for url in extra_urls or []:
        try:
            blocks.append(fetch_url_context(url))
        except Exception:  # noqa: BLE001  — best-effort
            continue

    # Expand @file references inline.
    task_out, refs_block = expand_file_refs(task, cwd)
    if refs_block:
        blocks.append(refs_block)

    extra_system = "\n\n".join(blocks) if blocks else ""
    return extra_system, task_out
