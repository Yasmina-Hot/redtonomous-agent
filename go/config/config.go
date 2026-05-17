package config

import (
	"encoding/json"
	"os"
	"path/filepath"
)

var (
	ConfigDir = filepath.Join(homeDir(), ".redtonomous")
	ConfigFile = filepath.Join(ConfigDir, "config.json")
	LogsDir   = filepath.Join(ConfigDir, "logs")
)

func homeDir() string {
	h, _ := os.UserHomeDir()
	return h
}

type ProviderConfig struct {
	APIKey       string `json:"api_key,omitempty"`
	BaseURL      string `json:"base_url,omitempty"`
	DefaultModel string `json:"default_model,omitempty"`
	Type         string `json:"type,omitempty"`
}

type AppConfig struct {
	DefaultProvider string                    `json:"default_provider"`
	DefaultModel    string                    `json:"default_model"`
	Providers       map[string]ProviderConfig `json:"providers"`
}

var OpenAICompatProviders = map[string]struct{ BaseURL, DefaultModel string }{
	"openai":     {"https://api.openai.com/v1", "gpt-4o"},
	"groq":       {"https://api.groq.com/openai/v1", "llama-3.3-70b-versatile"},
	"openrouter": {"https://openrouter.ai/api/v1", "openai/gpt-4o"},
	"deepseek":   {"https://api.deepseek.com/v1", "deepseek-chat"},
	"xai":        {"https://api.x.ai/v1", "grok-3"},
	"together":   {"https://api.together.xyz/v1", "meta-llama/Llama-3-70b-chat-hf"},
	"perplexity": {"https://api.perplexity.ai", "sonar-pro"},
	"ollama":     {"http://localhost:11434/v1", "llama3.2"},
	"lmstudio":   {"http://localhost:1234/v1", "local-model"},
}

func Load() AppConfig {
	cfg := AppConfig{
		DefaultProvider: "claude",
		DefaultModel:    "claude-sonnet-4-6",
		Providers:       map[string]ProviderConfig{},
	}
	data, err := os.ReadFile(ConfigFile)
	if err != nil {
		return cfg
	}
	_ = json.Unmarshal(data, &cfg)
	if cfg.Providers == nil {
		cfg.Providers = map[string]ProviderConfig{}
	}
	return cfg
}

func Save(cfg AppConfig) error {
	if err := os.MkdirAll(ConfigDir, 0700); err != nil {
		return err
	}
	data, err := json.MarshalIndent(cfg, "", "  ")
	if err != nil {
		return err
	}
	return os.WriteFile(ConfigFile, data, 0600)
}

func GetAPIKey(cfg AppConfig, provider string) string {
	if p, ok := cfg.Providers[provider]; ok && p.APIKey != "" {
		return p.APIKey
	}
	return os.Getenv(provider + "_API_KEY")
}

func GetBaseURL(cfg AppConfig, provider string) string {
	if p, ok := cfg.Providers[provider]; ok && p.BaseURL != "" {
		return p.BaseURL
	}
	if p, ok := OpenAICompatProviders[provider]; ok {
		return p.BaseURL
	}
	return ""
}

func GetDefaultModel(provider string) string {
	defaults := map[string]string{
		"claude":  "claude-sonnet-4-6",
		"gemini":  "gemini-2.0-flash",
		"cohere":  "command-r-plus",
		"mistral": "mistral-large-latest",
	}
	if m, ok := defaults[provider]; ok {
		return m
	}
	if p, ok := OpenAICompatProviders[provider]; ok {
		return p.DefaultModel
	}
	return "default"
}

func EnsureLogsDir() string {
	_ = os.MkdirAll(LogsDir, 0700)
	return LogsDir
}

func IsOpenAICompat(provider string) bool {
	if provider == "openai" {
		return true
	}
	_, ok := OpenAICompatProviders[provider]
	return ok
}
