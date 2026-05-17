# Redtonomous Agent

> Autonomous multi-model coding agent CLI. BYOK. No permission prompts. Builds real things.

**⚠️ WARNING: Always keep a backup of your project before running. This tool executes shell commands, writes files, and installs packages without asking.**

---

## What is it?

Redtonomous is a CLI agent that takes a task, picks up a model of your choice, and executes it fully — file reads, writes, shell commands, web fetches — in a loop until done. No pauses. No "are you sure?". Just output.

Three language implementations, one config format, same behavior:

| Version | Install | Binary |
|---|---|---|
| **Python** | `pip install -e python/` | `redtonomous` |
| **TypeScript** | `cd typescript && npm install && npm run build && npm link` | `redtonomous` |
| **Go** | `cd go && go install .` | `redtonomous` |

---

## Quick Start

```bash
# 1. Set your API key
redtonomous config set-key claude sk-ant-...

# 2. Run a task
redtonomous run "build a REST API in FastAPI with JWT auth and a /users endpoint"

# 3. Use a different model
redtonomous run "refactor this codebase to use async/await" --provider openai --model gpt-4o

# 4. Use a local model
redtonomous config set-key ollama none
redtonomous run "write unit tests for all functions" --provider ollama --model llama3.2
```

---

## Supported Providers

### Native SDKs
| Provider | Set Key | Models |
|---|---|---|
| **Anthropic Claude** | `config set-key claude sk-ant-...` | claude-opus-4-7, claude-sonnet-4-6, claude-haiku-4-5 |
| **Google Gemini** | `config set-key gemini AIza...` | gemini-2.5-pro, gemini-2.0-flash |
| **Cohere** | `config set-key cohere ...` | command-r-plus, command-r |
| **Mistral** | `config set-key mistral ...` | mistral-large-latest, codestral |

### OpenAI-Compatible (one adapter, config-driven)
| Provider | Set Key | Notes |
|---|---|---|
| **OpenAI** | `config set-key openai sk-...` | gpt-4o, o1, o3-mini |
| **Groq** | `config set-key groq gsk_...` | llama-3.3-70b, fast inference |
| **OpenRouter** | `config set-key openrouter sk-or-...` | 200+ models |
| **DeepSeek** | `config set-key deepseek ...` | deepseek-chat, deepseek-coder |
| **xAI Grok** | `config set-key xai ...` | grok-3 |
| **Together.ai** | `config set-key together ...` | llama, qwen, etc. |
| **Perplexity** | `config set-key perplexity ...` | sonar-pro |
| **Ollama** | *(no key needed)* | any locally pulled model |
| **LM Studio** | *(no key needed)* | any loaded model |

### Add any OpenAI-compatible provider
```bash
redtonomous config add-provider my_api https://my-llm-server.com/v1 --key mykey --default-model my-model
redtonomous run "do the thing" --provider my_api --model my-model
```

---

## Commands

```
redtonomous run <task>
  -m, --model       Model ID (e.g. claude-opus-4-7)
  -p, --provider    Provider (claude, openai, gemini, groq, ollama, ...)
  -d, --dir         Working directory (default: current dir)
  --no-backup       Skip automatic backup
  --max-iter N      Max tool-call iterations (default: 100)
  --no-log          Skip session log
  -y, --yes         Skip confirmation prompt

redtonomous config set-key <provider> <key>
redtonomous config set-model <model>
redtonomous config add-provider <name> <base_url>
redtonomous config show

redtonomous models       # list all known models
redtonomous auth         # OAuth login (coming soon)
```

---

## Tools the Agent Uses

| Tool | Description |
|---|---|
| `read_file` | Read file content |
| `write_file` | Create or overwrite file |
| `append_file` | Append to file |
| `list_directory` | List files (optionally recursive) |
| `create_directory` | mkdir -p |
| `delete_file` | Delete file or directory |
| `move_file` | Move/rename |
| `search_files` | grep-style search across files |
| `execute_command` | Run shell commands |
| `fetch_url` | HTTP requests |

---

## Config File

Location: `~/.redtonomous/config.json`

```json
{
  "default_provider": "claude",
  "default_model": "claude-sonnet-4-6",
  "providers": {
    "claude":     { "api_key": "sk-ant-..." },
    "openai":     { "api_key": "sk-..." },
    "gemini":     { "api_key": "AIza..." },
    "groq":       { "api_key": "gsk_..." },
    "ollama":     { "base_url": "http://localhost:11434/v1", "api_key": "none" }
  }
}
```

Session logs are saved to `~/.redtonomous/logs/`.

---

## Project Structure

```
redtonomous-agent/
├── python/          # Python CLI (pip install -e .)
├── typescript/      # TypeScript CLI (npm install && npm run build)
└── go/              # Go CLI (go install . → single binary)
```

All three share the same config file, same tool set, and same agent behavior.

---

## License

MIT
