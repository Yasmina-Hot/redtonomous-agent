from pathlib import Path

from redtonomous.repl_commands import REPLState, dispatch_slash


def _state(tmp_path: Path) -> REPLState:
    return REPLState(provider="claude", model="claude-sonnet-4-6", cwd=str(tmp_path))


def test_help_is_inline_no_op(tmp_path: Path):
    out = dispatch_slash("/help", _state(tmp_path))
    assert out is None


def test_unknown_command_is_inline(tmp_path: Path):
    out = dispatch_slash("/nope", _state(tmp_path))
    assert out is None


def test_model_changes_state(tmp_path: Path):
    st = _state(tmp_path)
    assert dispatch_slash("/model claude-opus-4-7", st) is None
    assert st.model == "claude-opus-4-7"


def test_provider_changes_state_and_default_model(tmp_path: Path):
    st = _state(tmp_path)
    assert dispatch_slash("/provider gemini", st) is None
    assert st.provider == "gemini"
    assert st.model.startswith("gemini")


def test_dir_changes_cwd(tmp_path: Path):
    st = _state(tmp_path)
    new = tmp_path / "sub"
    new.mkdir()
    assert dispatch_slash(f"/dir {new}", st) is None
    assert Path(st.cwd) == new.resolve()


def test_dir_rejects_nonexistent(tmp_path: Path):
    st = _state(tmp_path)
    cwd_before = st.cwd
    dispatch_slash("/dir /does/not/exist", st)
    assert st.cwd == cwd_before


def test_init_writes_memory_file(tmp_path: Path):
    st = _state(tmp_path)
    assert dispatch_slash("/init", st) is None
    assert (tmp_path / "REDTONOMOUS.md").exists()


def test_custom_command_expands(tmp_path: Path, monkeypatch):
    """A markdown file under ~/.redtonomous/commands/<name>.md becomes
    /<name> and expands to its contents.
    """
    monkeypatch.setenv("HOME", str(tmp_path))
    # Re-import so COMMANDS_DIR picks up the patched HOME.
    import importlib

    import redtonomous.repl_commands as rc
    importlib.reload(rc)

    rc.COMMANDS_DIR.mkdir(parents=True, exist_ok=True)
    (rc.COMMANDS_DIR / "summarise.md").write_text("Summarise the file: {args}")

    st = rc.REPLState(provider="claude", model="claude-sonnet-4-6", cwd=str(tmp_path))
    out = rc.dispatch_slash("/summarise lib.py", st)
    assert out == "Summarise the file: lib.py"


def test_resume_with_missing_id_returns_none(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    st = _state(tmp_path)
    out = dispatch_slash("/resume not-a-real-session", st)
    assert out is None
