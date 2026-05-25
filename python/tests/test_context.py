from pathlib import Path

from redtonomous.context import (
    assemble,
    build_repo_map,
    expand_file_refs,
    load_conventions,
    load_memory,
)


def test_load_memory_picks_first_existing(tmp_path: Path):
    (tmp_path / "CLAUDE.md").write_text("# claude notes")
    (tmp_path / "REDTONOMOUS.md").write_text("# red notes")
    # REDTONOMOUS.md wins because it's first in the search order.
    out = load_memory(str(tmp_path))
    assert "red notes" in out
    assert "REDTONOMOUS.md" in out


def test_load_memory_missing_returns_empty(tmp_path: Path):
    assert load_memory(str(tmp_path)) == ""


def test_load_conventions_finds_rules_file(tmp_path: Path):
    (tmp_path / ".cursorrules").write_text("Use 2 spaces.")
    out = load_conventions(str(tmp_path))
    assert "2 spaces" in out
    assert ".cursorrules" in out


def test_expand_file_refs_inlines_contents(tmp_path: Path):
    (tmp_path / "a.py").write_text("def hello(): return 1")
    task = "Take a look at @a.py and refactor it."
    _, block = expand_file_refs(task, str(tmp_path))
    assert "a.py" in block and "hello" in block


def test_expand_file_refs_skips_missing(tmp_path: Path):
    task = "Refactor @nope.py"
    _, block = expand_file_refs(task, str(tmp_path))
    assert block == ""


def test_expand_file_refs_blocks_path_traversal(tmp_path: Path):
    # Trying to reference a file outside cwd should be silently dropped, not
    # leak the contents of /etc/passwd.
    _, block = expand_file_refs("read @../../etc/passwd", str(tmp_path))
    assert "passwd" not in block.lower()


def test_build_repo_map_includes_obvious_files(tmp_path: Path):
    (tmp_path / "main.py").write_text("print('hi')\n")
    (tmp_path / "README.md").write_text("# Project\n")
    rmap = build_repo_map(str(tmp_path))
    assert "main.py" in rmap
    assert "README.md" in rmap


def test_assemble_combines_all_sources(tmp_path: Path):
    (tmp_path / "REDTONOMOUS.md").write_text("# memory")
    (tmp_path / ".cursorrules").write_text("rule")
    (tmp_path / "lib.py").write_text("def f(): pass")
    extra, task_out = assemble(
        cwd=str(tmp_path),
        task="Refactor @lib.py please",
        include_memory=True,
        include_conventions=True,
        include_repo_map=False,
    )
    assert "REDTONOMOUS.md" in extra
    assert ".cursorrules" in extra
    assert "lib.py" in extra  # via the @ref block
    assert task_out == "Refactor @lib.py please"  # task is unchanged
