# Mesh Setup Guide

## Quick Start (One Command)

```bash
cd /media/lyle/datadisk/dev/mesh
./setup.sh
```

This will:
1. ✅ Validate Python 3.10+ is installed
2. ✅ Install Python dependencies (pip packages)
3. ✅ Detect or install Gemini CLI and Codex CLI
4. ✅ Create `.env` configuration file with paths and timeouts
5. ✅ Run all 150+ tests to verify installation
6. ✅ Start the Mesh MCP server

---

## What setup.sh Does

### Step 1: Environment Validation
- Checks Python 3.10+ is available
- Verifies pip is installed
- Reports any missing dependencies

### Step 2: Install Dependencies
- Installs all Python packages from `requirements.txt`
- Includes: pytest, pydantic, google-generativeai, openai, etc.

### Step 3: Configuration
- **Detects CLIs** in your PATH (Gemini, Codex)
- **Prompts to install** any missing CLIs
- **Configures timeout** (default: 30 seconds)
- **Optional OpenRouter API key** for fallback

Creates `.env` file with:
```bash
GEMINI_CLI_PATH=gemini
CODEX_CLI_PATH=codex
CLI_TIMEOUT_SECONDS=30
OPENROUTER_API_KEY=sk-or-...  # (optional)
LOGLEVEL=INFO
```

### Step 4: Validate Environment
- Verifies CLI tools are accessible
- Tests configuration is loadable
- Confirms at least one provider is available

### Step 5: Run Test Suite
- Phase 1: CLI execution layer tests (~45 tests)
- Phase 2: Error handling & fallback tests (~20 tests)
- Phase 3: Integration tests (82 tests)
- **Total: 150+ tests in <3 seconds**

### Step 6: Connect to Claude Code
- Checks if Claude CLI is installed
- Automatically registers Mesh with `claude mcp add`
- Uses dynamic path (no hardcoded paths)
- Shows verification command: `claude mcp list`

### Step 7: Start Server
- Loads `.env` configuration
- Launches Mesh MCP server on stdin/stdout
- Ready to accept MCP client connections

---

## Usage Options

### Option 1: Full Interactive Setup
```bash
./setup.sh
```
Runs all steps with prompts for configuration.

### Option 2: Skip Tests
```bash
./setup.sh --skip-tests
```
Useful if you want to set up quickly without waiting for tests.

### Option 3: Start Server Only
```bash
./setup.sh --start-only
```
If `.env` already exists, just start the server without re-running setup.

### Option 4: Show Help
```bash
./setup.sh --help
```
Display usage options and exit.

---

## Detailed Walk-Through

### Example: Full Setup with Prompts

```
$ ./setup.sh

╔════════════════════════════════════════════════════════════════════╗
║ Mesh MCP Server Setup                                             ║
╚════════════════════════════════════════════════════════════════════╝

CLI-first MCP server using Gemini CLI + Codex CLI with OpenRouter fallback

Directory: /path/to/mesh

╔════════════════════════════════════════════════════════════════════╗
║ Step 1: Environment Validation                                    ║
╚════════════════════════════════════════════════════════════════════╝

→ Checking Python version...
✓ Python 3.13.7 found
→ Checking pip...
✓ pip is available

╔════════════════════════════════════════════════════════════════════╗
║ Step 2: Install Dependencies                                      ║
╚════════════════════════════════════════════════════════════════════╝

→ Installing Python dependencies...
✓ Dependencies installed

╔════════════════════════════════════════════════════════════════════╗
║ Environment Configuration                                         ║
╚════════════════════════════════════════════════════════════════════╝

→ Checking for Gemini CLI...
✓ Gemini CLI found at: /usr/local/bin/gemini
→ Checking for Codex CLI...
✓ Codex CLI found at: /usr/local/bin/codex

→ Configure CLI timeout (default: 30 seconds)
? Enter timeout in seconds (or press Enter for default): [press Enter]

→ Configure OpenRouter fallback (optional)
? Set OpenRouter API key for fallback? (y/N): n

→ Creating .env file...
✓ Configuration saved to: /path/to/mesh/.env

[Tests run...]

╔════════════════════════════════════════════════════════════════════╗
║ Connect to Claude Code                                            ║
╚════════════════════════════════════════════════════════════════════╝

→ Registering Mesh with Claude Code...
✓ Mesh registered with Claude Code!
→ Verify connection:
  claude mcp list

You can now use Mesh tools in Claude Code:
  /chat "Your question"
  /codereview "Review this code"
  /testgen "Write tests"

╔════════════════════════════════════════════════════════════════════╗
║ Start Server?                                                     ║
╚════════════════════════════════════════════════════════════════════╝

? Start Mesh MCP Server now? (Y/n): y

→ Starting server...
[Server running on stdin/stdout...]
```

---

## Troubleshooting Setup

### "Python 3 not found"
Install Python 3.10 or later:
```bash
# macOS
brew install python@3.11

# Ubuntu/Debian
sudo apt-get install python3.11

# Or use system package manager
```

### "Pip not found"
```bash
python3 -m ensurepip --upgrade
```

### "Gemini CLI installation failed"
Install manually:
1. Visit: https://cloud.google.com/docs/generative-ai/install-gemini-cli
2. Follow platform-specific installation instructions
3. Re-run `setup.sh`

### "Codex CLI installation failed"
Install via pip directly:
```bash
python3 -m pip install --upgrade openai[cli]
```

### "Neither Gemini CLI nor Codex CLI found"
You can still use Mesh with OpenRouter API fallback:
1. Run `setup.sh` and set `OPENROUTER_API_KEY` when prompted
2. Or manually set in `.env`:
   ```bash
   OPENROUTER_API_KEY=sk-or-v1-your-key-here
   ```

### "Tests failed during setup"
Setup will ask if you want to continue despite test failures. This is safe — most failures are environment-related (missing CLIs) and will be handled by the fallback chain.

---

## Manual Setup (Alternative to setup.sh)

If you prefer manual setup:

```bash
# 1. Install Python dependencies
pip install -r requirements.txt

# 2. Create .env file
cat > .env << EOF
GEMINI_CLI_PATH=gemini
CODEX_CLI_PATH=codex
CLI_TIMEOUT_SECONDS=30
OPENROUTER_API_KEY=sk-or-...  # (optional)
LOGLEVEL=INFO
EOF

# 3. Run tests (optional)
pytest tests/ -v

# 4. Start server
python3 -m mcp_server
```

---

## After Setup

### Claude Code Integration

The setup script automatically registers Mesh with Claude Code during Step 6 (no user choice needed).

**If Claude was not installed during setup**, you can add it manually:
```bash
claude mcp add mesh --path /path/to/mesh -- python3 -m mcp_server
```

**Verify connection:**
```bash
claude mcp list
```

### Using Mesh

Once connected, all PAL tools work identically:
```bash
# In Claude Code, use any PAL tool normally:
/chat "Explain async/await in Python"
/codereview "Analyze my authentication module"
/testgen "Write tests for this function"
```

Mesh automatically routes requests through:
1. Gemini CLI (if available)
2. Codex CLI (if Gemini fails)
3. OpenRouter API (if both CLIs fail and API key set)

---

## Configuration Details

### .env File Structure

```bash
# Path to Gemini CLI binary (or just "gemini" to use PATH)
GEMINI_CLI_PATH=/usr/local/bin/gemini

# Path to Codex CLI binary (or just "codex" to use PATH)
CODEX_CLI_PATH=/usr/local/bin/codex

# Subprocess timeout in seconds (default: 30)
CLI_TIMEOUT_SECONDS=30

# OpenRouter API key for fallback (optional)
OPENROUTER_API_KEY=sk-or-v1-abc123...

# Logging level (DEBUG, INFO, WARNING, ERROR)
LOGLEVEL=INFO
```

### Environment Variables

You can override `.env` by setting environment variables:

```bash
export GEMINI_CLI_PATH="/custom/path/to/gemini"
export CLI_TIMEOUT_SECONDS=60
export OPENROUTER_API_KEY="sk-or-..."

./setup.sh --start-only
```

---

## Docker Deployment

To run Mesh in Docker:

```bash
# Build image
docker build -t mesh-mcp .

# Run with CLI tools
docker run -it \
  -e GEMINI_CLI_PATH=/usr/local/bin/gemini \
  -e CODEX_CLI_PATH=/usr/local/bin/codex \
  mesh-mcp

# Run with OpenRouter fallback only
docker run -it \
  -e OPENROUTER_API_KEY=sk-or-... \
  mesh-mcp
```

See [setup-guide.md](docs/architecture/setup-guide.md) for full Docker instructions.

---

## Getting Help

If setup fails:

1. **Check the error message** — setup.sh prints clear error descriptions
2. **Review [troubleshooting.md](docs/architecture/troubleshooting.md)** — 13 common issues with solutions
3. **Run in debug mode** — enable logging:
   ```bash
   LOGLEVEL=DEBUG ./setup.sh
   ```
4. **Check dependencies manually:**
   ```bash
   python3 -m pytest tests/test_providers_cli.py -v
   ```

---

## Quick Reference

| Task | Command |
|------|---------|
| Full setup with tests | `./setup.sh` |
| Setup without tests | `./setup.sh --skip-tests` |
| Just start server | `./setup.sh --start-only` |
| Run tests manually | `pytest tests/ -v` |
| Check environment | `python3 -c "from utils.env import validate_provider_environment; validate_provider_environment()"` |
| View configuration | `cat .env` |
| Update OpenRouter key | Edit `.env` and change `OPENROUTER_API_KEY` |

---

## Summary

The `setup.sh` script automates:
- ✅ Python and dependency validation
- ✅ CLI detection and installation
- ✅ Configuration file generation
- ✅ Environment validation
- ✅ Test suite execution
- ✅ Server startup

**One command to get Mesh running:**
```bash
./setup.sh
```
