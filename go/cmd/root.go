package cmd

import (
	"bufio"
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"regexp"
	"strings"
	"unicode"

	"github.com/fatih/color"
	"github.com/spf13/cobra"
	agentpkg "github.com/yasmina-hot/redtonomous-agent/go/agent"
	"github.com/yasmina-hot/redtonomous-agent/go/config"
	"github.com/yasmina-hot/redtonomous-agent/go/models"
)

var rootCmd = &cobra.Command{
	Use:   "redtonomous",
	Short: "Autonomous multi-model coding agent CLI — BYOK, no permission prompts",
	Long: `Redtonomous — autonomous multi-model coding agent.

Run without a subcommand to enter interactive REPL mode.
Use 'redtonomous run <task>' for a one-shot task.`,
	RunE: func(cmd *cobra.Command, args []string) error {
		return runREPL(cmd)
	},
}

func Execute() {
	if err := rootCmd.Execute(); err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
}

func init() {
	// Root-level flags (used by REPL mode)
	rootCmd.Flags().StringP("model",    "m", "", "Model ID override")
	rootCmd.Flags().StringP("provider", "p", "", "Provider override")
	rootCmd.Flags().StringP("dir",      "d", "", "Working directory")

	// ── run ──────────────────────────────────────────────────────────────
	var (
		modelFlag    string
		providerFlag string
		dirFlag      string
		noBackup     bool
		maxIter      int
		noLog        bool
		yes          bool
	)
	runCmd := &cobra.Command{
		Use:   "run <task>",
		Short: "Run TASK autonomously (one-shot)",
		Args:  cobra.MinimumNArgs(1),
		RunE: func(cmd *cobra.Command, args []string) error {
			task := strings.Join(args, " ")
			cfg, provider, model, cwd := resolveRunParams(modelFlag, providerFlag, dirFlag)

			printBanner()
			printWarning(cwd, provider, model)

			if !yes {
				fmt.Print("Proceed? [Y/n] ")
				reader := bufio.NewReader(os.Stdin)
				ans, _ := reader.ReadString('\n')
				if strings.TrimSpace(strings.ToLower(ans)) == "n" {
					color.HiBlack("Aborted.")
					return nil
				}
			}

			adapter, err := getAdapter(provider, model, cfg)
			if err != nil {
				return err
			}

			return agentpkg.Run(agentpkg.RunOptions{
				Task:          task,
				Adapter:       adapter,
				Provider:      provider,
				Model:         model,
				Cwd:           cwd,
				MaxIterations: maxIter,
				Backup:        !noBackup,
				Log:           !noLog,
			})
		},
	}
	runCmd.Flags().StringVarP(&modelFlag, "model", "m", "", "Model ID override")
	runCmd.Flags().StringVarP(&providerFlag, "provider", "p", "", "Provider override")
	runCmd.Flags().StringVarP(&dirFlag, "dir", "d", "", "Working directory")
	runCmd.Flags().BoolVar(&noBackup, "no-backup", false, "Skip auto-backup")
	runCmd.Flags().IntVar(&maxIter, "max-iter", 100, "Max tool-call iterations")
	runCmd.Flags().BoolVar(&noLog, "no-log", false, "Skip session log")
	runCmd.Flags().BoolVarP(&yes, "yes", "y", false, "Skip confirmation prompt")
	rootCmd.AddCommand(runCmd)

	// ── config ────────────────────────────────────────────────────────────
	cfgCmd := &cobra.Command{Use: "config", Short: "Manage configuration and API keys"}

	cfgCmd.AddCommand(&cobra.Command{
		Use:   "set-key <provider> <key>",
		Short: "Store an API key for PROVIDER",
		Args:  cobra.ExactArgs(2),
		RunE: func(cmd *cobra.Command, args []string) error {
			cfg := config.Load()
			p := cfg.Providers[args[0]]
			p.APIKey = args[1]
			cfg.Providers[args[0]] = p
			if err := config.Save(cfg); err != nil {
				return err
			}
			color.HiBlack("API key saved for '%s'.", args[0])
			return nil
		},
	})

	cfgCmd.AddCommand(&cobra.Command{
		Use:   "set-model <model>",
		Short: "Set the default model",
		Args:  cobra.ExactArgs(1),
		RunE: func(cmd *cobra.Command, args []string) error {
			cfg := config.Load()
			cfg.DefaultModel = args[0]
			if err := config.Save(cfg); err != nil {
				return err
			}
			color.HiBlack("Default model set to '%s'.", args[0])
			return nil
		},
	})

	cfgCmd.AddCommand(&cobra.Command{
		Use:   "set-wake-word <word>",
		Short: "Set the wake word for REPL mode and shell-setup",
		Args:  cobra.ExactArgs(1),
		RunE: func(cmd *cobra.Command, args []string) error {
			word := args[0]
			if !isValidIdentifier(word) {
				return fmt.Errorf(
					"'%s' is not a valid shell identifier. Use letters, digits, and underscores only.",
					word,
				)
			}
			cfg := config.Load()
			cfg.WakeWord = word
			if err := config.Save(cfg); err != nil {
				return err
			}
			color.HiBlack("Wake word set to '%s'. Run: redtonomous shell-setup", word)
			return nil
		},
	})

	cfgCmd.AddCommand(&cobra.Command{
		Use:   "show",
		Short: "Print current configuration",
		RunE: func(cmd *cobra.Command, args []string) error {
			cfg := config.Load()
			for k, p := range cfg.Providers {
				if p.APIKey != "" && p.APIKey != "none" && len(p.APIKey) > 8 {
					p.APIKey = p.APIKey[:8] + "…"
					cfg.Providers[k] = p
				}
			}
			data, _ := json.MarshalIndent(cfg, "", "  ")
			fmt.Println(string(data))
			return nil
		},
	})

	addProviderCmd := &cobra.Command{
		Use:   "add-provider <name> <base_url>",
		Short: "Add a custom OpenAI-compatible provider",
		Args:  cobra.ExactArgs(2),
		RunE: func(cmd *cobra.Command, args []string) error {
			key, _ := cmd.Flags().GetString("key")
			defModel, _ := cmd.Flags().GetString("default-model")
			cfg := config.Load()
			cfg.Providers[args[0]] = config.ProviderConfig{
				Type: "openai-compat", BaseURL: args[1], APIKey: key, DefaultModel: defModel,
			}
			if err := config.Save(cfg); err != nil {
				return err
			}
			color.HiBlack("Provider '%s' added.", args[0])
			return nil
		},
	}
	addProviderCmd.Flags().String("key", "none", "API key")
	addProviderCmd.Flags().String("default-model", "default", "Default model")
	cfgCmd.AddCommand(addProviderCmd)

	rootCmd.AddCommand(cfgCmd)

	// ── models ────────────────────────────────────────────────────────────
	rootCmd.AddCommand(&cobra.Command{
		Use:   "models",
		Short: "List all known models",
		Run: func(cmd *cobra.Command, args []string) {
			fmt.Printf("\n%-14s %-45s %s\n", "Provider", "Model", "Type")
			fmt.Println(strings.Repeat("─", 80))
			for _, m := range models.KnownModels {
				fmt.Printf("%-14s %-45s %s\n",
					color.CyanString(m.Provider),
					m.Model,
					color.HiBlackString(m.Type),
				)
			}
		},
	})

	// ── shell-setup ───────────────────────────────────────────────────────
	shellSetupCmd := &cobra.Command{
		Use:   "shell-setup",
		Short: "Print (or install) the shell function for your wake word",
		RunE: func(cmd *cobra.Command, args []string) error {
			shellName, _ := cmd.Flags().GetString("shell")
			wakeOverride, _ := cmd.Flags().GetString("wake-word")
			write, _ := cmd.Flags().GetBool("write")

			cfg := config.Load()
			wake := wakeOverride
			if wake == "" {
				wake = config.GetWakeWord(cfg)
			}
			if wake == "" {
				return fmt.Errorf("no wake word configured. Run: redtonomous config set-wake-word <word>")
			}

			// Auto-detect shell
			if shellName == "" {
				shellEnv := os.Getenv("SHELL")
				switch {
				case strings.Contains(shellEnv, "fish"):
					shellName = "fish"
				case strings.Contains(shellEnv, "zsh"):
					shellName = "zsh"
				case strings.Contains(strings.ToLower(shellEnv), "pwsh"),
					strings.Contains(strings.ToLower(shellEnv), "powershell"):
					shellName = "pwsh"
				default:
					shellName = "bash"
				}
			}

			snippets := map[string]string{
				"bash": fmt.Sprintf("# Redtonomous wake word — add to ~/.bashrc\n%s() {\n  redtonomous run \"$@\"\n}", wake),
				"zsh":  fmt.Sprintf("# Redtonomous wake word — add to ~/.zshrc\n%s() {\n  redtonomous run \"$@\"\n}", wake),
				"fish": fmt.Sprintf("# Redtonomous wake word — save as ~/.config/fish/functions/%s.fish\nfunction %s\n  redtonomous run $argv\nend", wake, wake),
				"pwsh": fmt.Sprintf("# Redtonomous wake word — add to $PROFILE\nfunction %s { redtonomous run @args }", wake),
			}
			rcFiles := map[string]string{
				"bash": "~/.bashrc",
				"zsh":  "~/.zshrc",
				"fish": fmt.Sprintf("~/.config/fish/functions/%s.fish", wake),
				"pwsh": "$PROFILE",
			}

			snippet := snippets[shellName]
			rcFile := rcFiles[shellName]

			fmt.Printf("\nWake word: %s  (%s)\n\n", color.RedString(wake), shellName)
			fmt.Printf("Add this to %s:\n\n", color.New(color.Bold).Sprint(rcFile))
			color.Green("%s\n\n", snippet)

			if write {
				return writeShellSnippet(shellName, wake, snippet, rcFile)
			}
			color.HiBlack("Then run: source %s (or open a new terminal)", rcFile)
			color.HiBlack("After that: %s build me a FastAPI app", wake)
			return nil
		},
	}
	shellSetupCmd.Flags().String("shell", "", "Target shell: bash | zsh | fish | pwsh (default: auto-detect)")
	shellSetupCmd.Flags().String("wake-word", "", "Override the configured wake word")
	shellSetupCmd.Flags().Bool("write", false, "Append directly to your shell rc file")
	rootCmd.AddCommand(shellSetupCmd)

	// ── auth ──────────────────────────────────────────────────────────────
	rootCmd.AddCommand(&cobra.Command{
		Use:   "auth",
		Short: "OAuth login (coming soon)",
		Run: func(cmd *cobra.Command, args []string) {
			color.HiBlack("OAuth login is on the roadmap. Use 'config set-key claude <key>' for now.")
		},
	})
}

// runREPL starts the interactive REPL loop (bare invocation).
func runREPL(cmd *cobra.Command) error {
	modelFlag, _ := cmd.Flags().GetString("model")
	providerFlag, _ := cmd.Flags().GetString("provider")
	dirFlag, _ := cmd.Flags().GetString("dir")

	cfg, provider, model, cwd := resolveRunParams(modelFlag, providerFlag, dirFlag)
	wake := config.GetWakeWord(cfg)
	if wake == "" {
		wake = "red"
	}

	printBanner()
	printWarning(cwd, provider, model)
	color.HiBlack("Interactive mode — type a task and press Enter. 'exit' or Ctrl-C to quit. (wake word: %s)", wake)
	fmt.Println(strings.Repeat("─", 70))

	adapter, err := getAdapter(provider, model, cfg)
	if err != nil {
		return err
	}

	scanner := bufio.NewScanner(os.Stdin)
	shortCwd := filepath.Base(cwd)

	for {
		color.HiBlack("(%s/%s · %s)  ", provider, model, shortCwd)
		fmt.Printf("%s> ", color.RedString(wake))

		if !scanner.Scan() {
			color.HiBlack("\nGoodbye.")
			break
		}
		task := strings.TrimSpace(scanner.Text())
		if task == "" {
			continue
		}
		switch strings.ToLower(task) {
		case "exit", "quit", "q", ":q":
			color.HiBlack("Goodbye.")
			return nil
		}

		if err := agentpkg.Run(agentpkg.RunOptions{
			Task:          task,
			Adapter:       adapter,
			Provider:      provider,
			Model:         model,
			Cwd:           cwd,
			MaxIterations: 100,
			Backup:        false,
			Log:           true,
		}); err != nil {
			color.Red("Error: %v", err)
		}
		fmt.Println(strings.Repeat("─", 70))
	}
	return nil
}

// resolveRunParams returns cfg, provider, model, cwd from flags + config.
func resolveRunParams(modelFlag, providerFlag, dirFlag string) (config.AppConfig, string, string, string) {
	cfg := config.Load()
	provider := providerFlag
	if provider == "" {
		provider = cfg.DefaultProvider
	}
	model := modelFlag
	if model == "" {
		model = cfg.DefaultModel
		if model == "" {
			model = config.GetDefaultModel(provider)
		}
	}
	cwd := dirFlag
	if cwd == "" {
		cwd, _ = os.Getwd()
	}
	cwd, _ = filepath.Abs(cwd)
	return cfg, provider, model, cwd
}

func getAdapter(provider, model string, cfg config.AppConfig) (models.Adapter, error) {
	apiKey := config.GetAPIKey(cfg, provider)
	baseURL := config.GetBaseURL(cfg, provider)

	switch provider {
	case "claude":
		if apiKey == "" {
			return nil, fmt.Errorf("no API key for claude. Run: redtonomous config set-key claude <key>")
		}
		return models.NewClaudeAdapter(apiKey, model), nil

	case "gemini", "cohere", "mistral":
		return nil, fmt.Errorf(
			"provider '%s' requires its native SDK and is not yet implemented in the Go version.\n"+
				"Use the Python or TypeScript CLI instead:\n  cd python && pip install -e . && redtonomous run ...",
			provider,
		)

	default:
		isLocal := provider == "ollama" || provider == "lmstudio"
		if apiKey == "" && !isLocal {
			return nil, fmt.Errorf("no API key for %s. Run: redtonomous config set-key %s <key>", provider, provider)
		}
		if apiKey == "" {
			apiKey = "none"
		}
		if baseURL == "" && !isLocal {
			return nil, fmt.Errorf("unknown provider '%s'. Add it with: redtonomous config add-provider %s <base_url>", provider, provider)
		}
		return models.NewOpenAICompatAdapter(apiKey, model, baseURL), nil
	}
}

func writeShellSnippet(shellName, wake, snippet, rcFile string) error {
	home, _ := os.UserHomeDir()
	var target string
	if shellName == "fish" {
		fishDir := filepath.Join(home, ".config", "fish", "functions")
		if err := os.MkdirAll(fishDir, 0755); err != nil {
			return err
		}
		target = filepath.Join(fishDir, wake+".fish")
	} else {
		target = strings.Replace(rcFile, "~", home, 1)
	}

	markerStart := fmt.Sprintf("# >>> redtonomous wake word (%s) >>>", wake)
	markerEnd   := fmt.Sprintf("# <<< redtonomous wake word (%s) <<<", wake)
	block := fmt.Sprintf("\n%s\n%s\n%s\n", markerStart, snippet, markerEnd)

	if _, err := os.Stat(target); err == nil {
		content, _ := os.ReadFile(target)
		if strings.Contains(string(content), markerStart) {
			re := regexp.MustCompile(
				`(?s)` + regexp.QuoteMeta(markerStart) + `.*?` + regexp.QuoteMeta(markerEnd),
			)
			updated := re.ReplaceAllString(string(content), strings.TrimSpace(block))
			_ = os.WriteFile(target, []byte(updated), 0644)
			color.HiBlack("Updated wake word in %s", target)
			return nil
		}
		_ = os.WriteFile(target+".bak", content, 0644)
	}

	f, err := os.OpenFile(target, os.O_APPEND|os.O_CREATE|os.O_WRONLY, 0644)
	if err != nil {
		return err
	}
	defer f.Close()
	_, err = f.WriteString(block)
	if err != nil {
		return err
	}
	color.HiBlack("Written to %s", target)
	if shellName != "fish" {
		color.HiBlack("Run: source %s", target)
	}
	return nil
}

func isValidIdentifier(s string) bool {
	if s == "" {
		return false
	}
	for i, r := range s {
		if i == 0 && unicode.IsDigit(r) {
			return false
		}
		if !unicode.IsLetter(r) && !unicode.IsDigit(r) && r != '_' {
			return false
		}
	}
	return true
}

func printBanner() {
	color.Red(`
██████╗ ███████╗██████╗ ████████╗ ██████╗ ███╗   ██╗ ██████╗ ███╗   ███╗ ██████╗ ██╗   ██╗███████╗
██╔══██╗██╔════╝██╔══██╗╚══██╔══╝██╔═══██╗████╗  ██║██╔═══██╗████╗ ████║██╔═══██╗██║   ██║██╔════╝
██████╔╝█████╗  ██║  ██║   ██║   ██║   ██║██╔██╗ ██║██║   ██║██╔████╔██║██║   ██║██║   ██║███████╗
██╔══██╗██╔══╝  ██║  ██║   ██║   ██║   ██║██║╚██╗██║██║   ██║██║╚██╔╝██║██║   ██║██║   ██║╚════██║
██║  ██║███████╗██████╔╝   ██║   ╚██████╔╝██║ ╚████║╚██████╔╝██║ ╚═╝ ██║╚██████╔╝╚██████╔╝███████║
╚═╝  ╚═╝╚══════╝╚═════╝    ╚═╝    ╚═════╝ ╚═╝  ╚═══╝ ╚═════╝ ╚═╝     ╚═╝ ╚═════╝  ╚═════╝ ╚══════╝`)
	color.HiBlack("Autonomous multi-model coding agent — BYOK, no permission prompts (Go edition)\n")
}

func printWarning(cwd, provider, model string) {
	color.Yellow("╔══════════════════════════════════════╗")
	color.Yellow("║   ⚡  AUTONOMOUS MODE ACTIVE          ║")
	color.Yellow("╚══════════════════════════════════════╝")
	fmt.Printf("All actions execute WITHOUT confirmation.\nShell commands will run in: %s\n", color.New(color.Bold).Sprint(cwd))
	color.HiBlack("Provider: %s  |  Model: %s\n", provider, model)
}
