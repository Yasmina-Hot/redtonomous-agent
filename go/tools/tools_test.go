package tools

import (
	"strings"
	"testing"
)

func TestExecuteCommandBasic(t *testing.T) {
	out := executeCommand("echo hi", "", 10)
	if !strings.Contains(out, "hi") || !strings.Contains(out, "EXIT_CODE: 0") {
		t.Fatalf("unexpected output: %q", out)
	}
}

func TestExecuteCommandEmpty(t *testing.T) {
	out := executeCommand("", "", 5)
	if !strings.HasPrefix(out, "ERROR:") {
		t.Fatalf("expected error for empty command, got %q", out)
	}
}

func TestExecuteCommandTimeout(t *testing.T) {
	out := executeCommand("sleep 5", "", 1)
	if !strings.Contains(out, "timed out") {
		t.Fatalf("expected timeout, got %q", out)
	}
}

func TestExecuteCommandDangerousGate(t *testing.T) {
	t.Setenv("REDTONOMOUS_CONFIRM_DANGEROUS", "1")
	out := executeCommand("rm -rf /tmp/this-should-not-run", "", 5)
	if !strings.HasPrefix(out, "ERROR:") || !strings.Contains(out, "dangerous pattern") {
		t.Fatalf("dangerous pattern not blocked: %q", out)
	}
}

func TestSearchFilesInvalidRegex(t *testing.T) {
	out := searchFiles("(", ".", "*")
	if !strings.HasPrefix(out, "ERROR:") {
		t.Fatalf("expected invalid-regex error, got %q", out)
	}
}
