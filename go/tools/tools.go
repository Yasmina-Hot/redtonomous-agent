package tools

import (
	"fmt"
	"io"
	"io/fs"
	"net/http"
	"os"
	"os/exec"
	"path/filepath"
	"regexp"
	"strings"
	"time"
)

// ToolDef holds the canonical definition of a tool.
type ToolDef struct {
	Name        string
	Description string
	Parameters  map[string]interface{}
}

// AllTools is the canonical list of tools shared across all model adapters.
var AllTools = []ToolDef{
	{Name: "read_file", Description: "Read the full contents of a file.", Parameters: map[string]interface{}{
		"type": "object",
		"properties": map[string]interface{}{"path": map[string]interface{}{"type": "string"}},
		"required": []string{"path"},
	}},
	{Name: "write_file", Description: "Create or overwrite a file.", Parameters: map[string]interface{}{
		"type": "object",
		"properties": map[string]interface{}{
			"path":    map[string]interface{}{"type": "string"},
			"content": map[string]interface{}{"type": "string"},
		},
		"required": []string{"path", "content"},
	}},
	{Name: "append_file", Description: "Append text to a file.", Parameters: map[string]interface{}{
		"type": "object",
		"properties": map[string]interface{}{
			"path":    map[string]interface{}{"type": "string"},
			"content": map[string]interface{}{"type": "string"},
		},
		"required": []string{"path", "content"},
	}},
	{Name: "list_directory", Description: "List files and directories.", Parameters: map[string]interface{}{
		"type": "object",
		"properties": map[string]interface{}{
			"path":      map[string]interface{}{"type": "string"},
			"recursive": map[string]interface{}{"type": "boolean"},
		},
		"required": []string{"path"},
	}},
	{Name: "create_directory", Description: "Create a directory.", Parameters: map[string]interface{}{
		"type": "object",
		"properties": map[string]interface{}{"path": map[string]interface{}{"type": "string"}},
		"required": []string{"path"},
	}},
	{Name: "delete_file", Description: "Delete a file or directory.", Parameters: map[string]interface{}{
		"type": "object",
		"properties": map[string]interface{}{"path": map[string]interface{}{"type": "string"}},
		"required": []string{"path"},
	}},
	{Name: "move_file", Description: "Move or rename a file.", Parameters: map[string]interface{}{
		"type": "object",
		"properties": map[string]interface{}{
			"source": map[string]interface{}{"type": "string"},
			"dest":   map[string]interface{}{"type": "string"},
		},
		"required": []string{"source", "dest"},
	}},
	{Name: "search_files", Description: "Search for a text pattern in files.", Parameters: map[string]interface{}{
		"type": "object",
		"properties": map[string]interface{}{
			"pattern":   map[string]interface{}{"type": "string"},
			"directory": map[string]interface{}{"type": "string"},
			"file_glob": map[string]interface{}{"type": "string"},
		},
		"required": []string{"pattern", "directory"},
	}},
	{Name: "execute_command", Description: "Run a shell command.", Parameters: map[string]interface{}{
		"type": "object",
		"properties": map[string]interface{}{
			"command": map[string]interface{}{"type": "string"},
			"cwd":     map[string]interface{}{"type": "string"},
			"timeout": map[string]interface{}{"type": "integer"},
		},
		"required": []string{"command"},
	}},
	{Name: "fetch_url", Description: "Make an HTTP request.", Parameters: map[string]interface{}{
		"type": "object",
		"properties": map[string]interface{}{
			"url":    map[string]interface{}{"type": "string"},
			"method": map[string]interface{}{"type": "string"},
			"body":   map[string]interface{}{"type": "string"},
		},
		"required": []string{"url"},
	}},
}

func str(args map[string]interface{}, key string) string {
	if v, ok := args[key]; ok {
		if s, ok := v.(string); ok {
			return s
		}
	}
	return ""
}

func boolVal(args map[string]interface{}, key string) bool {
	if v, ok := args[key]; ok {
		if b, ok := v.(bool); ok {
			return b
		}
	}
	return false
}

func intVal(args map[string]interface{}, key string, def int) int {
	if v, ok := args[key]; ok {
		switch n := v.(type) {
		case float64:
			return int(n)
		case int:
			return n
		}
	}
	return def
}

// Execute dispatches a tool call and returns (result, isError).
func Execute(name string, args map[string]interface{}) (string, bool) {
	var result string
	switch name {
	case "read_file":
		result = readFile(str(args, "path"))
	case "write_file":
		result = writeFile(str(args, "path"), str(args, "content"))
	case "append_file":
		result = appendFile(str(args, "path"), str(args, "content"))
	case "list_directory":
		result = listDirectory(str(args, "path"), boolVal(args, "recursive"))
	case "create_directory":
		result = createDirectory(str(args, "path"))
	case "delete_file":
		result = deleteFile(str(args, "path"))
	case "move_file":
		result = moveFile(str(args, "source"), str(args, "dest"))
	case "search_files":
		glob := str(args, "file_glob")
		if glob == "" {
			glob = "*"
		}
		result = searchFiles(str(args, "pattern"), str(args, "directory"), glob)
	case "execute_command":
		result = executeCommand(str(args, "command"), str(args, "cwd"), intVal(args, "timeout", 120))
	case "fetch_url":
		result = fetchURL(str(args, "url"), str(args, "method"), str(args, "body"))
	default:
		return fmt.Sprintf("ERROR: unknown tool '%s'", name), true
	}
	return result, strings.HasPrefix(result, "ERROR:")
}

func readFile(path string) string {
	data, err := os.ReadFile(path)
	if err != nil {
		return fmt.Sprintf("ERROR: %v", err)
	}
	return string(data)
}

func writeFile(path, content string) string {
	if err := os.MkdirAll(filepath.Dir(path), 0755); err != nil {
		return fmt.Sprintf("ERROR: %v", err)
	}
	if err := os.WriteFile(path, []byte(content), 0644); err != nil {
		return fmt.Sprintf("ERROR: %v", err)
	}
	return fmt.Sprintf("OK: wrote %d bytes to %s", len(content), path)
}

func appendFile(path, content string) string {
	if err := os.MkdirAll(filepath.Dir(path), 0755); err != nil {
		return fmt.Sprintf("ERROR: %v", err)
	}
	f, err := os.OpenFile(path, os.O_APPEND|os.O_CREATE|os.O_WRONLY, 0644)
	if err != nil {
		return fmt.Sprintf("ERROR: %v", err)
	}
	defer f.Close()
	_, _ = f.WriteString(content)
	return fmt.Sprintf("OK: appended %d bytes to %s", len(content), path)
}

func listDirectory(path string, recursive bool) string {
	if recursive {
		var entries []string
		_ = filepath.WalkDir(path, func(p string, d fs.DirEntry, err error) error {
			if err != nil {
				return nil
			}
			if strings.HasPrefix(d.Name(), ".") && p != path {
				if d.IsDir() {
					return filepath.SkipDir
				}
				return nil
			}
			if !d.IsDir() {
				rel, _ := filepath.Rel(path, p)
				entries = append(entries, rel)
			}
			return nil
		})
		if len(entries) == 0 {
			return "(empty)"
		}
		return strings.Join(entries, "\n")
	}
	entries, err := os.ReadDir(path)
	if err != nil {
		return fmt.Sprintf("ERROR: %v", err)
	}
	var names []string
	for _, e := range entries {
		if e.IsDir() {
			names = append(names, e.Name()+"/")
		} else {
			names = append(names, e.Name())
		}
	}
	if len(names) == 0 {
		return "(empty)"
	}
	return strings.Join(names, "\n")
}

func createDirectory(path string) string {
	if err := os.MkdirAll(path, 0755); err != nil {
		return fmt.Sprintf("ERROR: %v", err)
	}
	return fmt.Sprintf("OK: created %s", path)
}

func deleteFile(path string) string {
	if err := os.RemoveAll(path); err != nil {
		return fmt.Sprintf("ERROR: %v", err)
	}
	return fmt.Sprintf("OK: deleted %s", path)
}

func moveFile(source, dest string) string {
	if err := os.MkdirAll(filepath.Dir(dest), 0755); err != nil {
		return fmt.Sprintf("ERROR: %v", err)
	}
	if err := os.Rename(source, dest); err != nil {
		return fmt.Sprintf("ERROR: %v", err)
	}
	return fmt.Sprintf("OK: moved %s → %s", source, dest)
}

func searchFiles(pattern, directory, fileGlob string) string {
	re, err := regexp.Compile(pattern)
	if err != nil {
		return fmt.Sprintf("ERROR: invalid regex %q: %v", pattern, err)
	}
	var results []string
	_ = filepath.WalkDir(directory, func(p string, d fs.DirEntry, err error) error {
		if err != nil {
			return nil
		}
		if d.IsDir() {
			if strings.HasPrefix(d.Name(), ".") {
				return filepath.SkipDir
			}
			return nil
		}
		matched, _ := filepath.Match(fileGlob, d.Name())
		if !matched {
			return nil
		}
		data, err := os.ReadFile(p)
		if err != nil {
			return nil
		}
		rel, _ := filepath.Rel(directory, p)
		for i, line := range strings.Split(string(data), "\n") {
			if re.MatchString(line) {
				results = append(results, fmt.Sprintf("%s:%d: %s", rel, i+1, strings.TrimSpace(line)))
				if len(results) >= 200 {
					return io.EOF
				}
			}
		}
		return nil
	})
	if len(results) == 0 {
		return "No matches found"
	}
	return strings.Join(results, "\n")
}

var dangerousPatterns = []*regexp.Regexp{
	regexp.MustCompile(`\brm\s+-rf\s+/\S*`),
	regexp.MustCompile(`\bmkfs(\.\w+)?\b`),
	regexp.MustCompile(`\bdd\s+if=`),
	regexp.MustCompile(`:\(\)\s*\{`),
	regexp.MustCompile(`>\s*/dev/sd[a-z]`),
	regexp.MustCompile(`\bchmod\s+(-R\s+)?0?777\b`),
	regexp.MustCompile(`\bchown\s+(-R\s+)?root\b`),
	regexp.MustCompile(`\bcurl\b[^|]*\|\s*(sudo\s+)?(ba)?sh`),
	regexp.MustCompile(`\bwget\b[^|]*\|\s*(sudo\s+)?(ba)?sh`),
}

func isDangerous(command string) string {
	for _, pat := range dangerousPatterns {
		if pat.MatchString(command) {
			return pat.String()
		}
	}
	return ""
}

func executeCommand(command, cwd string, timeout int) string {
	if strings.TrimSpace(command) == "" {
		return "ERROR: command must be a non-empty string"
	}
	if timeout <= 0 {
		timeout = 120
	}
	if timeout > 600 {
		timeout = 600
	}
	if v := strings.ToLower(os.Getenv("REDTONOMOUS_CONFIRM_DANGEROUS")); v == "1" || v == "true" || v == "yes" {
		if pat := isDangerous(command); pat != "" {
			return fmt.Sprintf(
				"ERROR: command matched a dangerous pattern (/%s/) and REDTONOMOUS_CONFIRM_DANGEROUS is enabled. "+
					"Re-issue with a narrower scope or unset the env var to proceed.",
				pat,
			)
		}
	}
	if cwd == "" {
		cwd, _ = os.Getwd()
	}
	ctx := exec.Command("sh", "-c", command)
	ctx.Dir = cwd
	ctx.Env = append(os.Environ(), "TERM=dumb")

	done := make(chan error, 1)
	var stdout, stderr strings.Builder
	ctx.Stdout = &stdout
	ctx.Stderr = &stderr

	if err := ctx.Start(); err != nil {
		return fmt.Sprintf("ERROR: %v", err)
	}

	go func() {
		done <- ctx.Wait()
	}()

	select {
	case <-done:
	case <-time.After(time.Duration(timeout) * time.Second):
		_ = ctx.Process.Kill()
		<-done // reap the goroutine so we don't leak
		return fmt.Sprintf("ERROR: command timed out after %ds", timeout)
	}

	var parts []string
	if s := stdout.String(); s != "" {
		parts = append(parts, "STDOUT:\n"+strings.TrimRight(s, "\n"))
	}
	if s := stderr.String(); s != "" {
		parts = append(parts, "STDERR:\n"+strings.TrimRight(s, "\n"))
	}
	parts = append(parts, fmt.Sprintf("EXIT_CODE: %d", ctx.ProcessState.ExitCode()))
	return strings.Join(parts, "\n")
}

func fetchURL(url, method, body string) string {
	if method == "" {
		method = "GET"
	}
	client := &http.Client{Timeout: 30 * time.Second}
	var bodyReader io.Reader
	if body != "" {
		bodyReader = strings.NewReader(body)
	}
	req, err := http.NewRequest(method, url, bodyReader)
	if err != nil {
		return fmt.Sprintf("ERROR: %v", err)
	}
	req.Header.Set("User-Agent", "redtonomous/0.1")
	resp, err := client.Do(req)
	if err != nil {
		return fmt.Sprintf("ERROR: %v", err)
	}
	defer resp.Body.Close()
	data, _ := io.ReadAll(io.LimitReader(resp.Body, 8000))
	return fmt.Sprintf("STATUS: %d\nCONTENT-TYPE: %s\n\n%s", resp.StatusCode, resp.Header.Get("Content-Type"), string(data))
}
