# Mesh MCP — CLI-First MCP Server

<div align="center">

  <em>Local CLI tools meet the MCP protocol</em><br />
  <sub>Routes AI requests through the Gemini and Codex CLIs, with OpenRouter as an HTTPS fallback</sub>

</div>

**No accumulated API keys. No cloud lock-in. Just CLIs.**

Mesh routes every AI request through local command-line tools (`gemini`, `codex`) when possible, falling back to OpenRouter only when nothing local can serve the model. Same MCP tools, same `ModelResponse` format, same workflows — just a leaner provider layer.

**Features:**
- 🚀 **Fast** — local CLI execution (100–500 ms typical)
- 🔒 **Private** — no external API calls when CLIs handle the request
- 📦 **Simple** — install one or both CLIs and point Mesh at them
- 🔄 **Resilient** — automatic fallback Gemini → Codex → OpenRouter
- 🧰 **Complete** — 18 Mesh tools work identically to the original layer

---

## Quick Start

**Prerequisites:** Python 3.10+, Git. At least one of:
- **[Gemini CLI](https://github.com/google-gemini/gemini-cli)** — `npm i -g @google/gemini-cli && gemini login`
- **[Codex CLI](https://github.com/openai/codex)** — `npm i -g @openai/codex && codex login`
- **[OpenRouter](https://openrouter.ai/)** API key (set as `OPENROUTER_API_KEY` in `.env`)

**Install:**
```bash
git clone https://github.com/dgdev25/mesh.git
cd mesh
./setup.sh             # idempotent: venv, deps, .env, Claude Code registration
```

**Use it:**
```
"Use mesh chat with gemini-2.5-pro to review this auth flow"
"Get consensus from gpt-5 and opus on whether to use Redis or Postgres"
"Use mesh debug with o3 to find the race condition"
```

---

## How It Works

```
MCP Client (Claude Code, Codex CLI, Gemini CLI)
    ↓
Mesh MCP Server
    ↓
Gemini CLI       (gemini-* models)
Codex CLI        (gpt-*, o3, o4 models)
OpenRouter HTTPS (everything else: opus, sonnet, deepseek, grok, …)
    ↓
Automatic fallback if a backend can't handle the request
```

All three backends produce identical `ModelResponse` objects, so tool code never has to care which one served the request.

---

## Configuration

```bash
# Optional CLI path overrides (defaults: search PATH for `gemini` and `codex`)
GEMINI_CLI_PATH=/usr/local/bin/gemini
CODEX_CLI_PATH=/usr/local/bin/codex
CLI_TIMEOUT_SECONDS=120

# OpenRouter fallback (required if neither CLI is installed)
OPENROUTER_API_KEY=sk-or-...
OPENROUTER_ALLOWED_MODELS=                    # empty = no restrictions

# Defaults
DEFAULT_MODEL=auto                            # 'auto' picks per task
DEFAULT_THINKING_MODE_THINKDEEP=high
DISABLED_TOOLS=analyze,refactor,testgen,secaudit,docgen,tracer
```

Full reference: **[docs/configuration.md](docs/configuration.md)**.

---

## Documentation

- 📖 **[Getting Started](docs/getting-started.md)** — installation, MCP client setup, verification
- ⚙️ **[Configuration](docs/configuration.md)** — every environment variable, with defaults
- 🛠️ **[Troubleshooting](docs/troubleshooting.md)** — common issues and fixes
- 🧠 **[Advanced Usage](docs/advanced-usage.md)** — power-user workflows
- 📊 **[Model Ranking](docs/model_ranking.md)** — how auto-mode picks models
- 🪟 **[WSL Setup](docs/wsl-setup.md)** — Windows users
- 🤝 **[Contributing](docs/contributions.md)** — code standards, PR process

---

## Core Tools

> Each tool ships with its own multi-step workflow and parameters that consume context window space even when idle. Non-essential tools are disabled by default — toggle via `DISABLED_TOOLS` in `.env`.

**Collaboration & Planning** *(enabled by default)*
- **[`clink`](docs/tools/clink.md)** — bridge to external CLIs (Gemini planner, Codex codereviewer, etc.)
- **[`chat`](docs/tools/chat.md)** — brainstorm, get second opinions, validate approaches
- **[`thinkdeep`](docs/tools/thinkdeep.md)** — extended reasoning, edge case analysis
- **[`planner`](docs/tools/planner.md)** — break down complex projects into actionable plans
- **[`consensus`](docs/tools/consensus.md)** — multi-model debate with stance steering

**Code Analysis & Quality** *(enabled by default)*
- **[`debug`](docs/tools/debug.md)** — systematic root-cause analysis
- **[`precommit`](docs/tools/precommit.md)** — validate changes before committing
- **[`codereview`](docs/tools/codereview.md)** — professional reviews with severity levels

**Development Tools** *(disabled by default)*
- **[`analyze`](docs/tools/analyze.md)** — architecture and dependency analysis
- **[`refactor`](docs/tools/refactor.md)** — refactoring with decomposition focus
- **[`testgen`](docs/tools/testgen.md)** — test generation with edge cases
- **[`secaudit`](docs/tools/secaudit.md)** — OWASP Top 10 (2025) security audits
- **[`docgen`](docs/tools/docgen.md)** — documentation generation with complexity analysis
- **[`tracer`](docs/tools/tracer.md)** — call-flow mapping

**Utilities**
- **[`apilookup`](docs/tools/apilookup.md)** — current API/SDK lookups in a sub-process
- **[`challenge`](docs/tools/challenge.md)** — prevent reflexive AI agreement
- **[`listmodels`](docs/tools/listmodels.md)** — show configured backends and available models
- **[`version`](docs/tools/version.md)** — server version and capabilities

---

## Example Workflows

**Multi-model code review** *(codereview takes one model per pass — chain via continuation):*
```
"Run codereview with gemini pro on the auth/ directory, then continue with o3
 for a second opinion, then use planner to outline a fix strategy"
```

**Collaborative debugging** *(thinking_mode only applies to thinking-capable models — name one):*
```
"Use debug with gemini pro and thinking_mode=max on this race condition,
 then validate the fix with precommit"
```

**Architecture planning** *(consensus takes multiple models with stances):*
```
"Use planner to break down our microservices migration, then run consensus
 with sonnet supporting the proposal and o3 opposing it"
```

See **[docs/advanced-usage.md](docs/advanced-usage.md)** for more.

---

## Testing

```bash
pytest tests/                                              # unit + integration (mocked)
MESH_RUN_CLI_TESTS=1 pytest tests/test_cli_integration.py  # real subprocess against gemini/codex
python -m simulator_tests --quick                          # end-to-end MCP scenarios
```

**Current status:** 595 unit tests passing.

---

## License

MIT — see [LICENSE](LICENSE).

## Acknowledgments

- [Model Context Protocol](https://modelcontextprotocol.com)
- [Claude Code](https://claude.ai/code)
- [Codex CLI](https://developers.openai.com/codex/cli)
- [Gemini CLI](https://github.com/google-gemini/gemini-cli)
- [OpenRouter](https://openrouter.ai/)

[![Star History Chart](https://api.star-history.com/svg?repos=dgdev25/mesh&type=Date)](https://www.star-history.com/#dgdev25/mesh&Date)
