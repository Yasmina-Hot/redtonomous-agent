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

## Web UI — Quick Start

Two browser apps + a shared Python backend. One command starts everything:

```bash
cd web
chmod +x start.sh && ./start.sh
```

| App | URL | What it is |
|---|---|---|
| **Redtonomous Chat** | http://localhost:3000 | Web version of the CLI — live streaming, 4-tab canvas, model selector, session history |
| **Red Testing (RDX)** | http://localhost:3001 | Agent eval platform — test suites, race mode, pipeline builder |
| **API Backend** | http://localhost:8000 | FastAPI server powering both UIs |

### Manual start (if you prefer)

```bash
# Backend (requires the Python CLI installed first)
cd web/api && pip install -r requirements.txt && uvicorn main:app --port 8000 --reload

# Chat UI
cd web/chat && npm install --legacy-peer-deps && npm run dev    # → localhost:3000

# RDX
cd web/rdx  && npm install --legacy-peer-deps && npm run dev   # → localhost:3001
```

### First-time setup

1. Open http://localhost:3000
2. Click the gear icon → paste your `~/.redtonomous/config.json` (or type keys directly)
3. Pick a provider + model from the top dropdown
4. Type a task and hit **Run**

---

## CLI Quick Start

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
  -m, --model         Model ID (e.g. claude-opus-4-7)
  -p, --provider      Provider (claude, openai, gemini, groq, ollama, ...)
  -d, --dir           Working directory (default: current dir)
  --no-backup         Skip automatic backup
  --max-iter N        Max tool-call iterations (default: 100)
  --no-log            Skip session log
  -y, --yes           Skip confirmation prompt
  --resume ID         Resume a previous session by id (see ~/.redtonomous/logs/)
  --budget USD        Halt when accumulated cost exceeds USD (0 = no cap)
  --max-hours N       Wall-clock cap, refuses to run past this many hours
  --dry-run           Stub out write_file / execute_command / etc. — no side effects
  --plan-first        Ask the model for a numbered plan and confirm before running
  --diff              After the run, git-diff every file the agent touched
  --git-commit "msg"  On success, git add -A && git commit -m "msg" in cwd
  --git-branch "name" Create + check out this branch before the run
  --tools a,b         Allow-list of tool names available to the model
  --no-tools x,y      Deny-list of tool names
  --fallback p,q      Provider failover chain on rate-limit / 5xx

# Autonomy modes — wrappers around `run` with opinionated defaults
redtonomous moonlight <task>   # overnight: 8h cap, $50 budget, retry, checkpoints
redtonomous red <task>         # dangerous: bypass gate; requires
                               # REDTONOMOUS_I_KNOW_WHAT_IM_DOING=1
redtonomous goal "<criteria>"  # judge-evaluated loop, retries until achieved

# Skills & meta
redtonomous chat               # plain back-and-forth (no tools, no loop)
redtonomous init               # write a REDTONOMOUS.md memory file
redtonomous review             # send the current git diff for code review
redtonomous bug                # find bugs in the current git diff
redtonomous plans              # show the pricing catalog
redtonomous completion bash    # shell completion script
redtonomous undo               # restore the most recent backup directory

# More flags on `run` (Cursor / Aider / Claude Code-inspired)
  --repo-map                   # inject an Aider-style repo map
  --with-url <url>             # fetch URL(s), inject as context (repeatable)
  --image <path>               # attach screenshot(s) to first message
  --architect <p[:m]>          # different model plans, editor model executes
  --test "<cmd>"               # auto-test gate: rerun until tests pass
  --style concise|verbose|json # response style
  --sandbox readonly|workdir|full
  --worktree                   # run inside a fresh git worktree
  --notify                     # desktop notification on done

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
├── go/              # Go CLI (go install . → single binary)
└── web/
    ├── start.sh     # Start all three services
    ├── chat/        # Next.js Chat UI → localhost:3000
    ├── rdx/         # Next.js RDX testing platform → localhost:3001
    └── api/         # FastAPI backend → localhost:8000
```

The three CLIs share the same config file (`~/.redtonomous/config.json`), tool set, and agent behavior. The web backend imports directly from the Python implementation.

---

## Plans & Pricing

Local CLI usage with your own API keys is always free. The cloud relay tier and hosted UI offer optional managed plans:

| Plan    | Price | What's in it |
|---------|-------|--------------|
| free    | $0    | BYO keys, 50 cloud sessions/mo, all 3 CLIs, local web UI |
| min     | $4    | 100 cloud sessions, priority queue, email support |
| starter | $9    | 250 cloud sessions, hosted Chat UI, sync sessions across devices |
| pro     | $19   | Unlimited sessions, moonlight mode, prompt caching included |
| dev     | $39   | Team workspaces, audit logs (90d), custom MCP, Slack/Discord notifications |
| max     | $99   | Dedicated compute, priority routing, early-access features |
| red     | $499  | `/red` mode unlimited, self-host option, 24/7 SLA |

`redtonomous plans` prints the catalog from the CLI. `GET /plans` exposes it over the FastAPI backend. The chat UI has a $ icon in the header that opens the pricing page.

---

## REPL slash commands

Type `redtonomous` with no subcommand to enter the REPL. Inside:

| Command | What it does |
|---------|--------------|
| `/help`         | List all commands (including custom ones) |
| `/clear`        | Clear the screen |
| `/compact`      | (REPL state is already fresh each turn — informational) |
| `/resume <id>`  | Resume a previous session |
| `/init`         | Generate a `REDTONOMOUS.md` memory file |
| `/model <id>`   | Switch the active model |
| `/provider <p>` | Switch the active provider |
| `/dir <path>`   | Change the working directory |
| `/cost`         | Print pricing for the active model |
| `/plans`        | Print the subscription catalog |
| `/exit`         | Quit |

Custom slash commands: drop a markdown file at `~/.redtonomous/commands/<name>.md` and it becomes `/<name>`. The body is expanded as the next task. Use `{args}` inside the template for trailing arguments.

---

## Project memory + conventions (inspired by Aider / Cursor / Claude Code)

If any of these files exist in your `cwd`, they're auto-included:

- `REDTONOMOUS.md` / `CLAUDE.md` / `AGENTS.md` — project memory (prepended to system prompt)
- `.redtonomousrules` / `.cursorrules` / `.aiderrules` — conventions
- `@path/to/file` or `@dir/` inside a task — Cursor-style inline file references that get inlined as context

`redtonomous run --repo-map "<task>"` adds an Aider-style repo map (file tree + first lines of important files) to the system prompt.

---

## Security & Environment Variables

The FastAPI backend reads these at startup:

| Variable | Effect |
|---|---|
| `REDTONOMOUS_API_TOKEN` | When set, every endpoint except `/health` requires `Authorization: Bearer <token>` (or `?token=` for WebSockets). Unset = open dev mode (logs a warning). |
| `REDTONOMOUS_FILES_ROOT` | Sandbox root for `/files` and `/file`. Defaults to the process working directory. Path traversal is rejected. |
| `REDTONOMOUS_CORS_ORIGINS` | Comma-separated extra origins to allow (the four `localhost:300x` ones are always allowed). |
| `REDTONOMOUS_LOG_LEVEL` | `DEBUG` / `INFO` / `WARNING`. Default `INFO`. |

The CLI shell tool honors:

| Variable | Effect |
|---|---|
| `REDTONOMOUS_CONFIRM_DANGEROUS` | When `1`/`true`/`yes`, commands matching destructive patterns (`rm -rf /`, `mkfs`, `curl | sh`, …) are refused so the model has to re-issue with narrower scope. |
| `REDTONOMOUS_CLAUDE_PROMPT_CACHE` | Default `1`. Set to `0` to disable ephemeral prompt caching on the Claude adapter. |

The Next.js apps read:

| Variable | Effect |
|---|---|
| `NEXT_PUBLIC_API_URL` | Backend URL (default `http://localhost:8000`). |
| `NEXT_PUBLIC_API_TOKEN` | Bearer token sent with every fetch + WS query. Required when the backend has `REDTONOMOUS_API_TOKEN` set. |

---

## Deploying the Web UI

Both `web/chat` and `web/rdx` are standard Next.js apps — import them to Vercel as separate projects, setting the root directory to `web/chat` or `web/rdx` respectively.

The FastAPI backend (`web/api`) can be deployed to any Python host (Railway, Render, Fly.io). After deploying, set the `NEXT_PUBLIC_API_URL` environment variable in each Vercel project to point to your backend URL.

GitHub Actions workflows in `.github/workflows/` handle auto-deploy when `VERCEL_TOKEN` is set as a repo secret.

---

## License

MIT
