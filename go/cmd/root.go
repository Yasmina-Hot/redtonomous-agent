package cmd

import (
	"bufio"
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"strings"

	"github.com/fatih/color"
	"github.com/spf13/cobra"
	agentpkg "github.com/yasmina-hot/redtonomous-agent/go/agent"
	"github.com/yasmina-hot/redtonomous-agent/go/config"
	"github.com/yasmina-hot/redtonomous-agent/go/models"
)

var rootCmd = &cobra.Command{
	Use:   "redtonomous",
	Short: "Autonomous multi-model coding agent CLI — BYOK, no permission prompts",
}

func Execute() {
	if err := rootCmd.Execute(); err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
}

func init() {
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
		Short: "Run TASK autonomously",
		Args:  cobra.MinimumNArgs(1),
		RunE: func(cmd *cobra.Command, args []string) error {
			task := strings.Join(args, " ")
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
				var err error
				cwd, err = os.Getwd()
				if err != nil {
					return err
				}
			}
			cwd, _ = filepath.Abs(cwd)

			printBanner()
			printWarning(cwd, provider, model)

			if !yes {
				fmt.Print("Proceed? [Y/n] ")
				reader := bufio.NewReader(os.Stdin)
				ans, _ := reader.ReadString('\n')
				ans = strings.TrimSpace(strings.ToLower(ans))
				if ans == "n" {
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

	cfgCmd.AddCommand(&cobra.Command{
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
	})

	rootCmd.AddCommand(cfgCmd)

	// ── models ────────────────────────────────────────────────────────────
	rootCmd.AddCommand(&cobra.Command{
		Use:   "models",
		Short: "List all known models",
		Run: func(cmd *cobra.Command, args []string) {
			fmt.Printf("\n%-14s %-45s %s\n", "Provider", "Model", "Type")
			fmt.Println(strings.Repeat("─", 80))
			for _, m := range models.KnownModels {
				color.Cyan("%-14s", m.Provider)
				fmt.Printf(" %-45s ", m.Model)
				color.HiBlack("%s\n", m.Type)
			}
		},
	})

	// ── auth ──────────────────────────────────────────────────────────────
	rootCmd.AddCommand(&cobra.Command{
		Use:   "auth",
		Short: "OAuth login (coming soon)",
		Run: func(cmd *cobra.Command, args []string) {
			color.HiBlack("OAuth login is on the roadmap. Use 'config set-key claude <key>' for now.")
		},
	})
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
		// Native SDK adapters — not yet implemented in the Go version.
		// Use the Python or TypeScript version for these providers.
		return nil, fmt.Errorf(
			"provider '%s' requires its native SDK and is not yet implemented in the Go version.\n"+
				"Use the Python or TypeScript CLI instead:\n  cd python && pip install -e . && redtonomous run ...",
			provider,
		)

	default:
		// Treat everything else as OpenAI-compatible (openai, groq, ollama, lmstudio, openrouter, etc.)
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

