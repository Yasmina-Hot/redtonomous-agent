import json
import os
from pathlib import Path
from typing import Any

CONFIG_DIR = Path.home() / ".redtonomous"
CONFIG_FILE = CONFIG_DIR / "config.json"
LOGS_DIR = CONFIG_DIR / "logs"

OPENAI_COMPAT_PROVIDERS = {
    "openai":      {"base_url": "https://api.openai.com/v1",          "default_model": "gpt-4o"},
    "groq":        {"base_url": "https://api.groq.com/openai/v1",     "default_model": "llama-3.3-70b-versatile"},
    "openrouter":  {"base_url": "https://openrouter.ai/api/v1",       "default_model": "openai/gpt-4o"},
    "deepseek":    {"base_url": "https://api.deepseek.com/v1",        "default_model": "deepseek-chat"},
    "xai":         {"base_url": "https://api.x.ai/v1",               "default_model": "grok-3"},
    "together":    {"base_url": "https://api.together.xyz/v1",        "default_model": "meta-llama/Llama-3-70b-chat-hf"},
    "perplexity":  {"base_url": "https://api.perplexity.ai",         "default_model": "sonar-pro"},
    "ollama":      {"base_url": "http://localhost:11434/v1",          "default_model": "llama3.2", "api_key": "none"},
    "lmstudio":    {"base_url": "http://localhost:1234/v1",           "default_model": "local-model", "api_key": "none"},
}

DEFAULT_CONFIG: dict[str, Any] = {
    "default_provider": "claude",
    "default_model": "claude-sonnet-4-6",
    "providers": {},
}


def load() -> dict[str, Any]:
    if not CONFIG_FILE.exists():
        return dict(DEFAULT_CONFIG)
    with open(CONFIG_FILE) as f:
        data = json.load(f)
    # merge defaults
    for k, v in DEFAULT_CONFIG.items():
        data.setdefault(k, v)
    return data


def save(cfg: dict[str, Any]) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE, "w") as f:
        json.dump(cfg, f, indent=2)


def ensure_logs_dir() -> Path:
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    return LOGS_DIR


def get_api_key(cfg: dict, provider: str) -> str | None:
    providers = cfg.get("providers", {})
    pdata = providers.get(provider, {})
    key = pdata.get("api_key") or os.environ.get(f"{provider.upper()}_API_KEY")
    if key == "none":
        return "none"
    return key


def get_provider_base_url(cfg: dict, provider: str) -> str | None:
    providers = cfg.get("providers", {})
    pdata = providers.get(provider, {})
    if "base_url" in pdata:
        return pdata["base_url"]
    if provider in OPENAI_COMPAT_PROVIDERS:
        return OPENAI_COMPAT_PROVIDERS[provider]["base_url"]
    return None


def get_default_model_for_provider(provider: str) -> str:
    defaults = {
        "claude":   "claude-sonnet-4-6",
        "gemini":   "gemini-2.0-flash",
        "cohere":   "command-r-plus",
        "mistral":  "mistral-large-latest",
    }
    if provider in defaults:
        return defaults[provider]
    if provider in OPENAI_COMPAT_PROVIDERS:
        return OPENAI_COMPAT_PROVIDERS[provider]["default_model"]
    return "default"


def is_openai_compat(provider: str) -> bool:
    return provider in OPENAI_COMPAT_PROVIDERS or provider == "openai"
