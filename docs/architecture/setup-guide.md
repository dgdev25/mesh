# Mesh MCP Server — Setup Guide

## Installation & Configuration

### Prerequisites

- Python 3.10+
- `pip` package manager
- Local access to Gemini CLI (`gemini`) or Codex CLI (`codex`), or OpenRouter API key

### Step 1: Clone and Install

```bash
# Clone the Mesh repository
git clone <mesh-repo-url> /path/to/mesh
cd /path/to/mesh

# Install dependencies
pip install -r requirements.txt

# Install in development mode (optional)
pip install -e .
```

### Step 2: Configure CLI Tools

Mesh attempts to auto-detect `gemini` and `codex` CLIs in your PATH. If they are not found, specify their paths explicitly.

#### Option A: System PATH (Recommended)

Ensure both CLI tools are in your system PATH:

```bash
which gemini
which codex
```

If both commands resolve, Mesh will find them automatically.

#### Option B: Environment Variables

If CLIs are installed in custom locations, configure them via environment variables:

```bash
export GEMINI_CLI_PATH="/usr/local/bin/gemini"
export CODEX_CLI_PATH="/opt/bin/codex"
export CLI_TIMEOUT_SECONDS=30
```

Add to `~/.bashrc`, `~/.zshrc`, or your shell configuration for persistence.

#### Option C: `.env` File (Development)

Create a `.env` file in the project root:

```bash
GEMINI_CLI_PATH=gemini
CODEX_CLI_PATH=codex
CLI_TIMEOUT_SECONDS=30
OPENROUTER_API_KEY=sk-or-...  # Optional fallback
```

**Security Note:** Never commit `.env` files to version control. Add `.env` to `.gitignore`.

### Step 3: Verify Configuration

Run the environment validation check:

```bash
python -c "from utils.env import validate_provider_environment; validate_provider_environment()"
```

Expected output:
```
✓ Gemini CLI found at: gemini
✓ Codex CLI found at: codex
✓ OpenRouter fallback enabled (API key set)
```

If any CLI is not found, Mesh will warn but continue. Requests will automatically fallback to available providers.

### Step 4: Start the MCP Server

```bash
# From project root
python -m mcp_server

# Or with logging enabled
LOGLEVEL=DEBUG python -m mcp_server
```

The server listens on `stdout`/`stdin` by default for MCP protocol communication.

### Step 5: Connect a Client

Claude CLI:
```bash
claude mcp add mesh --path /path/to/mesh -- python -m mcp_server
```

Verify connection:
```bash
claude mcp list
```

---

## Environment Variables Reference

| Variable | Default | Purpose | Example |
|----------|---------|---------|---------|
| `GEMINI_CLI_PATH` | `gemini` | Path to Gemini CLI binary | `/usr/local/bin/gemini` |
| `CODEX_CLI_PATH` | `codex` | Path to Codex CLI binary | `/opt/openai/codex` |
| `CLI_TIMEOUT_SECONDS` | `30` | Subprocess timeout in seconds | `60` |
| `OPENROUTER_API_KEY` | (unset) | Optional OpenRouter fallback API key | `sk-or-v1-abc123...` |
| `LOGLEVEL` | `INFO` | Logging level | `DEBUG`, `INFO`, `WARNING`, `ERROR` |

---

## Local Testing

### Run All Tests

```bash
# Phase 1: CLI execution layer
pytest tests/test_providers_cli.py -v

# Phase 2: Error handling & fallback
pytest tests/test_fallback_logic.py -v

# Phase 3: Integration tests (all Mesh tools)
pytest tests/test_all_tools.py -v

# All tests
pytest tests/ -v --tb=short
```

### Quick Smoke Test

Verify a single tool works:

```python
import asyncio
from providers.gemini_cli import GeminiCliProvider

async def test():
    provider = GeminiCliProvider()
    response = await provider.complete(
        prompt="Hello, world",
        model="gemini-2.5-flash"
    )
    print(f"Success: {response.success}")
    print(f"Content: {response.content[:100]}")

asyncio.run(test())
```

### Simulate Provider Failures

Test fallback chain by temporarily renaming a CLI:

```bash
# Simulate Gemini unavailable
mv $(which gemini) $(which gemini).bak

# Run tests or client - should fallback to Codex automatically
pytest tests/test_all_tools.py

# Restore
mv $(which gemini).bak $(which gemini)
```

---

## Troubleshooting

### Issue: "CLI not found"

**Symptom:** Error message: `CliNotFoundError: gemini not found`

**Causes & Solutions:**

1. **CLI binary missing from PATH**
   - Install Gemini CLI: `curl ... | bash` (follow official docs)
   - Verify: `which gemini`
   - If not found, set `GEMINI_CLI_PATH` explicitly

2. **Binary in custom location**
   - Set `GEMINI_CLI_PATH=/path/to/gemini`
   - Verify path: `ls -la /path/to/gemini`

3. **Permissions issue**
   - Check executable permission: `ls -la $(which gemini)`
   - Fix: `chmod +x /path/to/gemini`

### Issue: "CLI timeout"

**Symptom:** Error message: `CliTimeoutError: gemini CLI exceeded 30s timeout`

**Causes & Solutions:**

1. **CLI is slow**
   - Increase timeout: `export CLI_TIMEOUT_SECONDS=60`
   - Default is 30 seconds; set higher if network is slow

2. **CLI is hung**
   - CLI process will be killed after timeout
   - Check system resources: `top`, `df -h`
   - Restart CLI service if it exists

3. **Large request**
   - Very large prompts (>1MB) may exceed timeout
   - Break requests into smaller chunks
   - Or increase timeout as above

### Issue: "Invalid JSON output"

**Symptom:** Error message: `CliError: Invalid JSON in CLI output`

**Causes & Solutions:**

1. **CLI output contains non-JSON text**
   - Ensure CLI is configured to output JSON
   - Check CLI version: `gemini --version`
   - Verify CLI args: `gemini generate --help`

2. **CLI is outputting errors to stdout**
   - Check CLI configuration
   - Review CLI documentation for JSON output format
   - Test manually: `gemini generate --prompt "test" --model gemini-2.5-flash`

3. **Corrupted response**
   - Rare; try again
   - If persistent, check CLI stability

### Issue: "OpenRouter fallback not working"

**Symptom:** Mesh falls back to error instead of OpenRouter

**Causes & Solutions:**

1. **API key not set**
   - Set `OPENROUTER_API_KEY=sk-or-...`
   - Verify: `echo $OPENROUTER_API_KEY`

2. **API key invalid**
   - Generate new key from OpenRouter dashboard
   - Verify format: Must start with `sk-or-`

3. **API rate limit**
   - OpenRouter may be rate-limiting requests
   - Wait and retry
   - Check API quota on dashboard

### Issue: "All providers exhausted"

**Symptom:** Error message: `RuntimeError: All providers exhausted`

**Causes & Solutions:**

1. **All CLIs unavailable and no OpenRouter key**
   - Install at least one CLI (Gemini or Codex)
   - Or set `OPENROUTER_API_KEY` as fallback
   - Check which CLIs are available: `which gemini codex`

2. **All providers timing out**
   - Increase `CLI_TIMEOUT_SECONDS`
   - Check network connectivity
   - Verify CLI binaries are responsive (test manually)

3. **All providers returning invalid JSON**
   - Check CLI output format
   - Verify CLI versions match expected format
   - Contact CLI maintainers if output format changed

---

## Performance Tuning

### Reduce Latency

1. **Use local CLIs instead of API fallback**
   - API calls (~500ms-5s) are slower than local CLI (~100-500ms)
   - Ensure Gemini/Codex CLIs are installed locally

2. **Increase timeout for large requests**
   - Default 30s timeout is conservative
   - For typical requests: 30s is sufficient
   - For large prompts: increase to 60-120s

3. **Monitor timeout/fallback logs**
   - Enable `DEBUG` logging: `LOGLEVEL=DEBUG`
   - Identify slow providers
   - Consider increasing timeout or removing slow providers

### Batch Requests

- If using Mesh programmatically, batch similar requests
- Reduces per-request overhead
- Example: Generate 10 functions in one prompt instead of 10 prompts

---

## Docker Deployment

### Build Docker Image

```dockerfile
FROM python:3.10-slim

WORKDIR /mesh
COPY . .
RUN pip install -r requirements.txt

ENV GEMINI_CLI_PATH=gemini
ENV CODEX_CLI_PATH=codex
ENV CLI_TIMEOUT_SECONDS=30

CMD ["python", "-m", "mcp_server"]
```

### Run Container

```bash
docker build -t mesh .

# With CLI tools installed in container
docker run -e GEMINI_CLI_PATH=/usr/local/bin/gemini mesh

# With OpenRouter fallback
docker run -e OPENROUTER_API_KEY=sk-or-... mesh
```

---

## FAQ

**Q: Which CLI should I install?**  
A: Either Gemini CLI or Codex CLI (or both). Mesh will use the first available. If unsure, start with Gemini CLI for cost efficiency.

**Q: What if both CLIs are unavailable?**  
A: Mesh will fallback to OpenRouter API if `OPENROUTER_API_KEY` is set. If not, requests fail with error "All providers exhausted".

**Q: Can I use only OpenRouter (no CLIs)?**  
A: Yes. Don't install CLIs and set `OPENROUTER_API_KEY`. Mesh will skip CLI attempts and use OpenRouter directly. Performance will be slower (~500ms-5s per request) but still functional.

**Q: How do I rotate API keys?**  
A: Update `OPENROUTER_API_KEY` environment variable and restart Mesh server. No code changes needed.

**Q: Can I use Mesh with custom CLI tools?**  
A: Yes, if they follow the same argument/response format as Gemini/Codex CLIs. Point `GEMINI_CLI_PATH` or `CODEX_CLI_PATH` to your custom tool.

**Q: What's the expected latency?**  
A: Local CLIs: 100-500ms per request. OpenRouter fallback: 500-5000ms per request.

**Q: Does Mesh cache responses?**  
A: No. Each request goes to the provider. Implement caching at the client level if needed.

---

## Support

- **Documentation:** See `/docs/architecture/` directory
- **Issues:** Report via GitHub issues or contact maintainers
- **Configuration:** See [API Reference](./api-reference.md) for provider configuration details
