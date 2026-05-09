# Getting Started with Mesh MCP Server

Mesh is a multi-model coordination layer for Claude Code (and any other MCP
client). It hands tool calls off to one of three backends:

```
   Claude Code  →  Mesh  →  ┬─ gemini CLI   (subprocess)
                            ├─ codex  CLI   (subprocess)
                            └─ OpenRouter   (HTTPS fallback)
```

You need at least one of those three to be available.

---

## Prerequisites

- **Python 3.10+** (3.12 recommended)
- **Git**
- **[uv](https://docs.astral.sh/uv/getting-started/installation/)** (optional, for the uvx install path)
- **Windows users:** WSL2 is required for Claude Code

---

## Step 1 — Choose your backend(s)

You can run Mesh with any combination of these. They are auto-detected.

### Gemini CLI (recommended for Gemini access)

```bash
# Install (see https://github.com/google-gemini/gemini-cli for the latest)
npm install -g @google/gemini-cli
gemini login            # one-time auth
gemini --version        # sanity check
```

### Codex CLI (recommended for OpenAI/o3/GPT-5 access)

```bash
# Install (see https://github.com/openai/codex for the latest)
npm install -g @openai/codex
codex login             # one-time auth
codex --version
```

### OpenRouter (HTTPS fallback for everything else)

1. Sign up at [openrouter.ai](https://openrouter.ai/)
2. Create an API key
3. Set `OPENROUTER_API_KEY=...` in your `.env` (see Step 3)

OpenRouter gives you access to Anthropic Claude, Mistral, DeepSeek, etc.
It is the only HTTP-based provider Mesh supports.

---

## Step 2 — Install Mesh

### Option A: Clone + setup.sh (recommended)

```bash
git clone https://github.com/dgdev25/mesh.git
cd mesh
./setup.sh             # idempotent: venv, deps, .env, Claude Code registration
```

Re-run `./setup.sh --check` any time to verify the install.

### Option B: uvx one-shot

Add to your MCP client config (Claude Desktop, Claude Code, etc.):

```json
{
  "mcpServers": {
    "mesh": {
      "command": "sh",
      "args": [
        "-c",
        "for p in $(which uvx 2>/dev/null) $HOME/.local/bin/uvx /opt/homebrew/bin/uvx /usr/local/bin/uvx uvx; do [ -x \"$p\" ] && exec \"$p\" --from git+https://github.com/dgdev25/mesh.git mesh; done; echo 'uvx not found' >&2; exit 1"
      ],
      "env": {
        "PATH": "/usr/local/bin:/usr/bin:/bin:/opt/homebrew/bin:~/.local/bin",
        "OPENROUTER_API_KEY": "your_key_here"
      }
    }
  }
}
```

---

## Step 3 — Configure

Copy `.env.example` → `.env` and edit. Minimum viable configurations:

**Just CLIs, no API key:**
```dotenv
DEFAULT_MODEL=auto
# Mesh detects gemini/codex on PATH automatically
```

**Just OpenRouter:**
```dotenv
DEFAULT_MODEL=auto
OPENROUTER_API_KEY=sk-or-v1-...
```

**Everything:**
```dotenv
DEFAULT_MODEL=auto
OPENROUTER_API_KEY=sk-or-v1-...
# gemini and codex CLIs picked up from PATH
# CLI_TIMEOUT_SECONDS=30  # optional
```

See `docs/configuration.md` for the full reference.

---

## Step 4 — Wire it into your client

Most MCP clients accept a server config like:

```json
{
  "mcpServers": {
    "mesh": {
      "command": "/absolute/path/to/mesh/.mesh_venv/bin/python",
      "args": ["/absolute/path/to/mesh/server.py"]
    }
  }
}
```

`run-server.sh` prints the right block for your client (Claude Desktop,
Claude Code, Cursor, Windsurf, Trae, Gemini CLI, Qwen CLI) and offers to
write it for you.

---

## Step 5 — Verify

In Claude Code (or your MCP client), ask:

> "Use mesh listmodels to show what's available"

You should see the three backend sections, marked configured/not configured.
If everything reports ❌, check `logs/mcp_server.log` for startup errors.

---

## Troubleshooting

See `docs/troubleshooting.md`. The most common issues:

- `gemini`/`codex` not found on PATH — install the CLI or set
  `GEMINI_CLI_PATH` / `CODEX_CLI_PATH` in `.env`.
- `OPENROUTER_API_KEY` set but requests fail — verify the key at
  [openrouter.ai/keys](https://openrouter.ai/keys), check spending limits.
- MCP client cannot connect — confirm the absolute path in your client
  config matches `pwd` of the cloned repo.
