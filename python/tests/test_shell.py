

from redtonomous.tools.shell import execute_command


def test_basic_command():
    out = execute_command("echo hi", timeout=10)
    assert "hi" in out
    assert "EXIT_CODE: 0" in out


def test_empty_command_is_rejected():
    assert execute_command("", timeout=5).startswith("ERROR:")
    assert execute_command("   ", timeout=5).startswith("ERROR:")


def test_timeout(monkeypatch):
    out = execute_command("sleep 5", timeout=1)
    assert "timed out" in out


def test_dangerous_pattern_gate(monkeypatch):
    monkeypatch.setenv("REDTONOMOUS_CONFIRM_DANGEROUS", "1")
    out = execute_command("rm -rf /tmp/should-not-run", timeout=5)
    assert out.startswith("ERROR:")
    assert "dangerous pattern" in out


def test_dangerous_pattern_disabled_by_default(monkeypatch, tmp_path):
    # Without the env var the gate is off — but we still don't actually run rm.
    monkeypatch.delenv("REDTONOMOUS_CONFIRM_DANGEROUS", raising=False)
    # Pick a benign command that *looks* dangerous if the regex was over-broad.
    out = execute_command("echo 'curl-pipe-bash example'", timeout=5)
    assert "EXIT_CODE: 0" in out


def test_timeout_clamped_to_max():
    out = execute_command("echo ok", timeout=10**9)
    assert "EXIT_CODE: 0" in out
