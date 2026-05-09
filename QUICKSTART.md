# Mesh — Quick Start (5 minutes)

## One Command Setup

```bash
cd /media/lyle/datadisk/dev/mesh
./setup.sh
```

The script will:
1. Check Python 3.10+ ✓
2. Install dependencies ✓
3. Find or install Gemini CLI and Codex CLI ✓
4. Create `.env` configuration ✓
5. Run 150+ tests ✓
6. Automatically register Mesh with Claude Code ✓
7. Start the Mesh server ✓

**That's it.** Fully automated. No manual steps. Claude integration is automatic.

---

## What Happens During Setup

```
Check Python 3.10+
    ↓
Install dependencies (pytest, pydantic, etc.)
    ↓
Detect Gemini CLI / Codex CLI
    ↓
Create .env with paths and timeouts
    ↓
Validate environment is working
    ↓
Run test suite (150+ tests)
    ↓
Start Mesh MCP server
```

---

## Interactive Prompts (All Optional)

The script asks for optional configuration:

| Prompt | Action |
|--------|--------|
| "Install Gemini CLI now?" | `y` (or `n` if already installed) |
| "Install Codex CLI now?" | `y` (or `n` if already installed) |
| "Enter timeout in seconds" | Press Enter for 30s default |
| "Set OpenRouter API key?" | `n` unless you want API fallback |
| "Start Mesh server now?" | `y` to start, or `n` to start later |

Claude Code registration happens automatically with no user prompt.

---

## If Setup Fails

### Python not found
```bash
# Install Python 3.10+
brew install python@3.11  # macOS
# or apt-get install python3.11  (Linux)
```

### CLI installation fails
```bash
# Install manually, then re-run setup
# Gemini: https://cloud.google.com/docs/generative-ai/install-gemini-cli
# Codex: pip install --upgrade openai[cli]
./setup.sh
```

### Tests fail
Setup will ask if you want to continue. It's safe — tests fail if CLIs aren't installed, but the fallback chain will still work.

---

## After Setup: Use Mesh

### Mesh is already connected to Claude Code
The setup script automatically registers Mesh when you choose to during setup.

Verify the connection:
```bash
claude mcp list
```

### Use any Mesh tool
```bash
# In Claude Code:
/chat "Explain this code"
/codereview "Check for bugs"
/testgen "Write tests"
```

Request routes automatically:
```
Claude request
    ↓
Mesh MCP Server
    ↓
Try Gemini CLI (100-500ms)
    ├─ Success? → Return
    └─ Fail? ↓
Try Codex CLI (100-500ms)
    ├─ Success? → Return
    └─ Fail? ↓
Try OpenRouter API (500-5000ms)
    ├─ Success? → Return
    └─ Fail? → Error
```

---

## Optional: Add OpenRouter Fallback

If you want API fallback when CLIs unavailable:

1. Get API key: https://openrouter.ai/keys
2. Edit `.env`:
   ```bash
   nano .env
   # Add: OPENROUTER_API_KEY=sk-or-v1-your-key
   ```
3. Restart server:
   ```bash
   ./setup.sh --start-only
   ```

---

## Restart Server Later

Once setup is complete:

```bash
cd /media/lyle/datadisk/dev/mesh
./setup.sh --start-only
```

This skips setup and just starts the server.

---

## View Configuration

```bash
cat .env
```

Shows:
- CLI paths (Gemini, Codex)
- Timeout (30 seconds)
- OpenRouter API key (if set)
- Logging level

---

## Troubleshoot

### See what's happening
```bash
LOGLEVEL=DEBUG ./setup.sh
```

### Check individual parts
```bash
# Test Python dependencies
pytest tests/test_providers_cli.py -v

# Test environment
python3 -c "from utils.env import validate_provider_environment; validate_provider_environment()"

# Check CLIs
which gemini codex
```

### Full documentation
- [Setup Guide](docs/architecture/setup-guide.md) — Detailed instructions
- [Troubleshooting](docs/architecture/troubleshooting.md) — Common issues
- [API Reference](docs/architecture/api-reference.md) — Developer docs

---

## Summary

| Step | Command | Time |
|------|---------|------|
| 1. Navigate to Mesh | `cd /media/lyle/datadisk/dev/mesh` | <1s |
| 2. Run setup | `./setup.sh` | 2-3m |
| 3. (Optional) Connect Claude | `claude mcp add mesh ...` | <1s |
| 4. Done! | Use any Mesh tool normally | ✓ |

**Total time: ~5 minutes**

---

## What Gets Created

After setup, you'll have:

```
/media/lyle/datadisk/dev/mesh/
├── .env                    # Your configuration
├── setup.sh               # This setup script (can re-run anytime)
├── providers/             # CLI provider implementations
├── tests/                 # Test suite (150+ tests)
├── config.py              # Configuration management
├── utils/env.py           # Environment validation
├── docs/                  # Full documentation
└── README.md              # Overview
```

The `.env` file is your configuration. Edit it anytime to:
- Change CLI paths
- Adjust timeout
- Add/remove OpenRouter API key

---

**Ready to go!** 🚀
