from .base import ModelAdapter
from .. import config as cfg_module

KNOWN_MODELS = [
    # Claude
    {"provider": "claude",      "model": "claude-opus-4-7",           "type": "claude"},
    {"provider": "claude",      "model": "claude-sonnet-4-6",         "type": "claude"},
    {"provider": "claude",      "model": "claude-haiku-4-5",          "type": "claude"},
    # OpenAI
    {"provider": "openai",      "model": "gpt-4o",                    "type": "openai-compat"},
    {"provider": "openai",      "model": "gpt-4o-mini",               "type": "openai-compat"},
    {"provider": "openai",      "model": "o1",                        "type": "openai-compat"},
    {"provider": "openai",      "model": "o3-mini",                   "type": "openai-compat"},
    # Gemini
    {"provider": "gemini",      "model": "gemini-2.5-pro",            "type": "gemini"},
    {"provider": "gemini",      "model": "gemini-2.0-flash",          "type": "gemini"},
    # Groq
    {"provider": "groq",        "model": "llama-3.3-70b-versatile",   "type": "openai-compat"},
    {"provider": "groq",        "model": "mixtral-8x7b-32768",        "type": "openai-compat"},
    {"provider": "groq",        "model": "gemma2-9b-it",              "type": "openai-compat"},
    # Mistral
    {"provider": "mistral",     "model": "mistral-large-latest",      "type": "mistral"},
    {"provider": "mistral",     "model": "codestral-latest",          "type": "mistral"},
    # Cohere
    {"provider": "cohere",      "model": "command-r-plus",            "type": "cohere"},
    {"provider": "cohere",      "model": "command-r",                 "type": "cohere"},
    # OpenRouter
    {"provider": "openrouter",  "model": "openai/gpt-4o",             "type": "openai-compat"},
    {"provider": "openrouter",  "model": "anthropic/claude-3.5-sonnet","type": "openai-compat"},
    {"provider": "openrouter",  "model": "meta-llama/llama-3.3-70b",  "type": "openai-compat"},
    # DeepSeek
    {"provider": "deepseek",    "model": "deepseek-chat",             "type": "openai-compat"},
    {"provider": "deepseek",    "model": "deepseek-coder",            "type": "openai-compat"},
    # xAI
    {"provider": "xai",         "model": "grok-3",                    "type": "openai-compat"},
    {"provider": "xai",         "model": "grok-3-mini",               "type": "openai-compat"},
    # Together
    {"provider": "together",    "model": "meta-llama/Llama-3-70b-chat-hf", "type": "openai-compat"},
    # Perplexity
    {"provider": "perplexity",  "model": "sonar-pro",                 "type": "openai-compat"},
    # Ollama (local)
    {"provider": "ollama",      "model": "llama3.2",                  "type": "openai-compat (local)"},
    {"provider": "ollama",      "model": "codellama",                 "type": "openai-compat (local)"},
    {"provider": "ollama",      "model": "mistral",                   "type": "openai-compat (local)"},
    {"provider": "ollama",      "model": "deepseek-coder-v2",         "type": "openai-compat (local)"},
    # LM Studio (local)
    {"provider": "lmstudio",    "model": "local-model",               "type": "openai-compat (local)"},
]


def get_adapter(provider: str, model: str, app_cfg: dict) -> ModelAdapter:
    api_key = cfg_module.get_api_key(app_cfg, provider)
    base_url = cfg_module.get_provider_base_url(app_cfg, provider)

    if provider == "claude":
        from .claude import ClaudeAdapter
        if not api_key:
            raise ValueError("No API key for claude. Run: redtonomous config set-key claude <key>")
        return ClaudeAdapter(api_key=api_key, model=model)

    if provider == "gemini":
        from .gemini import GeminiAdapter
        if not api_key:
            raise ValueError("No API key for gemini. Run: redtonomous config set-key gemini <key>")
        return GeminiAdapter(api_key=api_key, model=model)

    if provider == "cohere":
        from .cohere import CohereAdapter
        if not api_key:
            raise ValueError("No API key for cohere. Run: redtonomous config set-key cohere <key>")
        return CohereAdapter(api_key=api_key, model=model)

    if provider == "mistral":
        from .mistral import MistralAdapter
        if not api_key:
            raise ValueError("No API key for mistral. Run: redtonomous config set-key mistral <key>")
        return MistralAdapter(api_key=api_key, model=model)

    # Everything else: OpenAI-compatible
    from .openai_compat import OpenAICompatAdapter
    if not api_key and provider not in ("ollama", "lmstudio"):
        raise ValueError(f"No API key for {provider}. Run: redtonomous config set-key {provider} <key>")
    return OpenAICompatAdapter(
        api_key=api_key or "none",
        model=model,
        base_url=base_url,
    )


def list_models() -> list[dict]:
    return KNOWN_MODELS
