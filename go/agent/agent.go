package agent

import (
	"encoding/json"
	"fmt"
	"io/fs"
	"os"
	"path/filepath"
	"time"

	"github.com/fatih/color"
	"github.com/yasmina-hot/redtonomous-agent/go/config"
	"github.com/yasmina-hot/redtonomous-agent/go/models"
	"github.com/yasmina-hot/redtonomous-agent/go/tools"
)

var systemPrompt = `You are Redtonomous — a fully autonomous software engineering agent.
You have unrestricted permission to read/write files, execute shell commands,
install packages, run builds, and fetch URLs within the working directory.

Rules:
1. Complete every task FULLY. Never stop halfway.
2. Make real changes. Do not just plan or describe.
3. Install missing dependencies with the shell tool if needed.
4. After writing code, run it to verify it works. Fix any errors before finishing.
5. Think through the full dependency and execution order before starting.
6. Never ask the user for confirmation. Just do it.
7. When done, summarize exactly what was built/changed.

Working directory: %s
Provider: %s | Model: %s`

type RunOptions struct {
	Task          string
	Adapter       models.Adapter
	Provider      string
	Model         string
	Cwd           string
	MaxIterations int
	Backup        bool
	Log           bool
}

type logEntry struct {
	Iter  int                    `json:"iter"`
	Tool  string                 `json:"tool"`
	Args  map[string]interface{} `json:"args"`
	Result string                `json:"result"`
	Error bool                   `json:"error"`
}

func Run(opts RunOptions) error {
	if opts.MaxIterations == 0 {
		opts.MaxIterations = 100
	}

	if opts.Backup {
		ts := time.Now().Format("20060102_150405")
		dst := fmt.Sprintf("%s_backup_%s", opts.Cwd, ts)
		if err := copyDir(opts.Cwd, dst); err != nil {
			color.Yellow("Backup skipped: %v", err)
		} else {
			color.HiBlack("📦 Backup created: %s", dst)
		}
	}

	system := fmt.Sprintf(systemPrompt, opts.Cwd, opts.Provider, opts.Model)
	messages := []models.Message{{Role: "user", Content: opts.Task}}

	var sessionLog []logEntry
	totalIn, totalOut := 0, 0

	color.Red("─────────────────────────────────── Redtonomous ───────────────────────────────────")
	color.HiBlack("Task: %s", opts.Task)
	color.HiBlack("Model: %s/%s  |  Dir: %s  |  Max iterations: %d", opts.Provider, opts.Model, opts.Cwd, opts.MaxIterations)
	color.Red("────────────────────────────────────────────────────────────────────────────────────")

	for iter := 0; iter < opts.MaxIterations; iter++ {
		resp, err := opts.Adapter.Chat(messages, tools.AllTools, system)
		if err != nil {
			return fmt.Errorf("model error: %w", err)
		}
		totalIn += resp.InputTokens
		totalOut += resp.OutputTokens

		if resp.Text != "" {
			preview := resp.Text
			if len(preview) > 120 {
				preview = preview[:120]
			}
			color.HiBlack("  %s", preview)
		}

		if resp.StopReason == "end_turn" || len(resp.ToolCalls) == 0 {
			text := resp.Text
			if text == "" {
				text = "(Task complete)"
			}
			color.Green("\n✅ Done\n────────────────────────────────────────────────────────────────\n%s\n────────────────────────────────────────────────────────────────", text)
			break
		}

		var results []models.ToolResult
		for _, tc := range resp.ToolCalls {
			argsStr := argsPreview(tc.Args)
			color.Blue("▶ %s  %s", tc.Name, argsStr)

			result, isError := tools.Execute(tc.Name, tc.Args)
			preview := result
			if len(preview) > 200 {
				preview = preview[:200] + "…"
			}
			if isError {
				color.Red("✗ %s: %s", tc.Name, preview)
			} else {
				color.HiBlack("✓ %s: %s", tc.Name, preview)
			}

			results = append(results, models.ToolResult{Content: result, IsError: isError})
			rPreview := result
			if len(rPreview) > 500 {
				rPreview = rPreview[:500]
			}
			sessionLog = append(sessionLog, logEntry{
				Iter: iter, Tool: tc.Name, Args: tc.Args, Result: rPreview, Error: isError,
			})
		}

		newMsgs := opts.Adapter.BuildToolResultMessages(resp.ToolCalls, results)
		messages = append(messages, newMsgs...)

		if iter == opts.MaxIterations-1 {
			color.Red("Error: reached max iterations (%d). Task may be incomplete.", opts.MaxIterations)
		}
	}

	color.HiBlack("Tokens used — input: %d  output: %d", totalIn, totalOut)

	if opts.Log && len(sessionLog) > 0 {
		logsDir := config.EnsureLogsDir()
		ts := time.Now().Format("20060102_150405")
		logFile := filepath.Join(logsDir, fmt.Sprintf("session_%s.json", ts))
		data, _ := json.MarshalIndent(map[string]interface{}{
			"task": opts.Task, "provider": opts.Provider, "model": opts.Model, "cwd": opts.Cwd, "log": sessionLog,
		}, "", "  ")
		_ = os.WriteFile(logFile, data, 0600)
		color.HiBlack("Session log: %s", logFile)
	}
	return nil
}

func argsPreview(args map[string]interface{}) string {
	parts := ""
	for k, v := range args {
		s := fmt.Sprintf("%v", v)
		if len(s) > 60 {
			s = s[:60]
		}
		parts += fmt.Sprintf("%s=%s  ", k, s)
	}
	return parts
}

func copyDir(src, dst string) error {
	return filepath.WalkDir(src, func(path string, d fs.DirEntry, err error) error {
		if err != nil {
			return err
		}
		rel, _ := filepath.Rel(src, path)
		target := filepath.Join(dst, rel)
		if d.IsDir() {
			return os.MkdirAll(target, 0755)
		}
		data, err := os.ReadFile(path)
		if err != nil {
			return err
		}
		return os.WriteFile(target, data, 0644)
	})
}
