# Configuration Guide

Mesh uses a CLI-first architecture with three backends:

1. **Gemini CLI** (`gemini`) — direct subprocess calls
2. **Codex CLI** (`codex`) — direct subprocess calls
3. **OpenRouter** — HTTPS fallback for any other model

At least one must be available. All configuration lives in `.env` (copy from `.env.example` or run `./setup.sh`).

---

## Quick Start

```bash
# Install gemini and/or codex CLIs (or set OPENROUTER_API_KEY in .env)
./setup.sh
```

That's it. Restart Claude Code and Mesh is ready.

---

## Environment Variables

### OpenRouter (HTTP fallback)

```bash
# Required if neither CLI is installed. Optional otherwise.
OPENROUTER_API_KEY=sk-or-...

# Restrict which OpenRouter models are usable. Empty = no restriction.
# Comma-separated, case-insensitive.
# Examples:
#   OPENROUTER_ALLOWED_MODELS=opus,sonnet
#   OPENROUTER_ALLOWED_MODELS=google/gemini-2.5-pro,openai/o3
OPENROUTER_ALLOWED_MODELS=
```

### CLI binary paths (optional)

```bash
# By default, Mesh searches PATH for `gemini` and `codex`.
# Override here if you need a specific binary path.
GEMINI_CLI_PATH=/usr/local/bin/gemini
CODEX_CLI_PATH=/usr/local/bin/codex

# Subprocess timeout (seconds). Defaults: 120 for gemini, 180 for codex.
CLI_TIMEOUT_SECONDS=120
```

### Defaults

```bash
# 'auto' lets Mesh pick the best available model per task.
# Other examples: gemini-2.5-pro, gpt-5.3-codex, opus, sonnet
DEFAULT_MODEL=auto

# Default thinking depth for the thinkdeep tool.
# Only models that support extended thinking honour this.
# Options: minimal | low | medium | high | max
DEFAULT_THINKING_MODE_THINKDEEP=high
```

### Tool selection

```bash
# Comma-separated list of tools to disable. Essential tools (version,
# listmodels) cannot be disabled. By default, non-essential tools are
# disabled to minimize context window usage.
DISABLED_TOOLS=analyze,refactor,testgen,secaudit,docgen,tracer
```

### Conversation memory

```bash
CONVERSATION_TIMEOUT_HOURS=24
MAX_CONVERSATION_TURNS=40
```

### Logging

```bash
# DEBUG | INFO | WARNING | ERROR
LOG_LEVEL=INFO
LOG_MAX_SIZE=10MB
```

### Locale (optional)

```bash
# Force AI responses into a specific language. Empty = English default.
# Examples: fr-FR, en-US, zh-CN, ja-JP
LOCALE=
```

### Mesh internals

```bash
# Force .env values to override system environment variables.
# Useful when MCP clients pass conflicting env vars.
MESH_MCP_FORCE_ENV_OVERRIDE=false
```

---

## Provider Priority

Mesh routes each model request in this order:

```
gemini-* / pro / flash      → Gemini CLI
gpt-* / o3 / o4 / codex     → Codex CLI
google/* / openai/* / opus / sonnet / etc.  → OpenRouter
```

If a CLI is unavailable for a model it claims to handle, Mesh falls back to OpenRouter automatically. If OpenRouter is also unavailable, the call fails with a clear error.

---

## Verifying configuration

```bash
./setup.sh --check    # Read-only verification of all setup steps
```

Or from inside Claude Code:

```
use mesh listmodels
```

This prints which backends are configured, available models per backend, and any restrictions in effect.

---

## Common configurations

### CLIs only (no API key)

```bash
# .env
DEFAULT_MODEL=auto
LOG_LEVEL=INFO
```

Install `gemini` and `codex` CLIs separately. No OpenRouter key needed.

### OpenRouter only (no CLIs installed)

```bash
# .env
OPENROUTER_API_KEY=sk-or-...
DEFAULT_MODEL=auto
```

All requests go to OpenRouter.

### Hybrid (recommended)

```bash
# .env
OPENROUTER_API_KEY=sk-or-...
DEFAULT_MODEL=auto
```

Plus `gemini` and `codex` on PATH. Mesh uses CLIs when possible, OpenRouter for everything else.

---

## Related Documentation

- **[Getting Started](getting-started.md)** — installation walkthrough
- **[Advanced Usage](advanced-usage.md)** — power-user workflows
- **[Troubleshooting](troubleshooting.md)** — common issues
