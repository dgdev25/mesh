# Mesh — Troubleshooting Guide

## Common Issues and Solutions

### "gemini/codex: command not found"

**Error Message:**
```
CliNotFoundError: gemini not found
```

**Root Cause:**
The CLI binary is not in your system PATH or hasn't been installed.

**Solutions:**

1. **Verify CLI is installed:**
   ```bash
   which gemini
   which codex
   ```
   If no output, the CLI is not installed.

2. **Install the missing CLI:**
   - Gemini CLI: https://cloud.google.com/docs/generative-ai/install-gemini-cli
   - Codex CLI: https://platform.openai.com/docs/guides/codex

3. **Add CLI to PATH (if installed in non-standard location):**
   ```bash
   export GEMINI_CLI_PATH="/path/to/gemini"
   export CODEX_CLI_PATH="/path/to/codex"
   ```

4. **Verify PATH is persistent:**
   Add exports to `~/.bashrc`, `~/.zshrc`, or `/etc/profile`:
   ```bash
   echo 'export GEMINI_CLI_PATH="/usr/local/bin/gemini"' >> ~/.bashrc
   source ~/.bashrc
   ```

---

### "CLI exceeded timeout"

**Error Message:**
```
CliTimeoutError: gemini CLI exceeded 30s timeout
```

**Root Cause:**
The CLI command took longer than the configured timeout to execute.

**Solutions:**

1. **Increase timeout (most common fix):**
   ```bash
   export CLI_TIMEOUT_SECONDS=60  # Default: 30 seconds
   ```
   Increase to 60-120 for large requests or slow networks.

2. **Check system resources:**
   ```bash
   top          # Check CPU/memory usage
   df -h        # Check disk space
   ping 8.8.8.8 # Check network connectivity
   ```
   If system is slow, wait for resources to free up or increase timeout.

3. **Test CLI manually:**
   ```bash
   time gemini generate --prompt "test" --model gemini-2.5-flash
   ```
   This shows how long the CLI actually takes. Set `CLI_TIMEOUT_SECONDS` higher than this value.

4. **Reduce request size:**
   - Break large prompts into smaller chunks
   - Reduce `max_tokens` parameter if possible

---

### "Invalid JSON in CLI output"

**Error Message:**
```
CliError: Invalid JSON in CLI output: Unexpected token at position 0
```

**Root Cause:**
The CLI is not outputting valid JSON, or the output format has changed.

**Solutions:**

1. **Verify CLI JSON output manually:**
   ```bash
   gemini generate --prompt "hello" --model gemini-2.5-flash
   ```
   Output should be valid JSON. If not, CLI is misconfigured.

2. **Check CLI version:**
   ```bash
   gemini --version
   codex --version
   ```
   Update to latest version if outdated:
   - `gem install gemini-cli --latest`
   - `pip install openai[cli] --upgrade`

3. **Check CLI format setting:**
   - Ensure CLI is configured for JSON output (not plain text)
   - Consult CLI documentation for format options

4. **Test CLI with simple prompt:**
   ```bash
   gemini generate --prompt "test" --model gemini-2.5-flash 2>&1 | head -20
   ```
   If output doesn't start with `{`, CLI is not in JSON mode.

---

### "All providers exhausted"

**Error Message:**
```
RuntimeError: All providers exhausted
```

**Root Cause:**
All available providers (Gemini CLI, Codex CLI, OpenRouter) have failed or are unavailable.

**Solutions:**

1. **Install at least one CLI tool:**
   ```bash
   which gemini  # Check if installed
   which codex   # Check if installed
   ```
   If neither found, install at least one.

2. **Set OpenRouter fallback (if CLIs not available):**
   ```bash
   export OPENROUTER_API_KEY="sk-or-v1-..."
   ```
   Generate key from https://openrouter.ai/keys

3. **Verify environment variables:**
   ```bash
   echo $GEMINI_CLI_PATH
   echo $CODEX_CLI_PATH
   echo $OPENROUTER_API_KEY
   ```
   Ensure at least one is set and valid.

4. **Check which provider failed:**
   Enable debug logging to see which providers were tried:
   ```bash
   LOGLEVEL=DEBUG python -m mcp_server
   ```
   Look for: "Trying GeminiCliProvider...", "Fallback to CodexCliProvider...", etc.

---

### "OpenRouter API key invalid"

**Error Message:**
```
OpenRouterError: Invalid API key format
```

**Root Cause:**
The `OPENROUTER_API_KEY` is not set, malformed, or has expired.

**Solutions:**

1. **Verify API key format:**
   ```bash
   echo $OPENROUTER_API_KEY
   ```
   Should start with `sk-or-` or `sk-or-v1-`.

2. **Generate new API key:**
   - Go to https://openrouter.ai/keys
   - Create new key (old key may have expired)
   - Set environment variable:
     ```bash
     export OPENROUTER_API_KEY="sk-or-..."
     ```

3. **Verify key is in environment:**
   ```bash
   python -c "import os; print('Set' if os.getenv('OPENROUTER_API_KEY') else 'Not set')"
   ```

4. **Check API quota:**
   - Log in to OpenRouter dashboard
   - Verify remaining credits/usage
   - If quota exhausted, top up account

---

### "Connection refused / Network error"

**Error Message:**
```
ConnectionError: Connection refused
```

**Root Cause:**
Network connectivity issue when trying to reach OpenRouter API or CLI service.

**Solutions:**

1. **Check internet connectivity:**
   ```bash
   ping google.com
   curl -I https://openrouter.ai
   ```

2. **Check firewall/proxy:**
   ```bash
   curl -x [proxy-url] https://openrouter.ai
   ```
   If behind proxy, ensure system proxy is configured.

3. **Check OpenRouter status:**
   - Visit https://status.openrouter.ai
   - Check for service outages

4. **Switch to local CLI provider:**
   If OpenRouter is down, ensure local CLI (Gemini/Codex) is available as fallback.

---

### "CLI process hanging / Zombie process"

**Symptom:**
Process doesn't complete, CPU usage stays high, or "defunct" processes appear in `ps aux`.

**Root Cause:**
CLI process did not terminate cleanly or child process wasn't reaped.

**Solutions:**

1. **Force cleanup (immediate workaround):**
   ```bash
   pkill -f "gemini generate"
   pkill -f "codex chat-completion"
   ```

2. **Increase timeout to allow cleanup:**
   ```bash
   export CLI_TIMEOUT_SECONDS=60
   ```
   Mesh sends SIGTERM, waits 5 seconds, then sends SIGKILL. Longer timeout allows cleanup.

3. **Check for system resource leaks:**
   ```bash
   lsof -p [process-id]  # Check open files
   ```

4. **Restart Mesh server:**
   ```bash
   kill [mesh-pid]
   python -m mcp_server
   ```

---

### "Out of memory / Killed"

**Error Message:**
```
Killed
```

**Root Cause:**
Request was too large (huge prompt or max_tokens) and exhausted available memory.

**Solutions:**

1. **Reduce request size:**
   ```python
   request = {
       "prompt": prompt[:10000],  # Limit prompt size
       "max_tokens": 2048,         # Reduce output limit
   }
   ```

2. **Increase system memory:**
   ```bash
   free -h  # Check available memory
   ```

3. **Close other processes:**
   ```bash
   top  # Kill non-essential processes
   ```

4. **Split large requests:**
   ```python
   # Instead of one large request:
   responses = [
       await registry.invoke_with_fallback({...large_request_1...}),
       await registry.invoke_with_fallback({...large_request_2...}),
   ]
   ```

---

### "File permission denied"

**Error Message:**
```
PermissionError: [Errno 13] Permission denied
```

**Root Cause:**
CLI binary is not executable, or Mesh doesn't have read permissions.

**Solutions:**

1. **Make CLI executable:**
   ```bash
   chmod +x $(which gemini)
   chmod +x $(which codex)
   ```

2. **Verify permissions:**
   ```bash
   ls -la $(which gemini)
   # Should show: -rwxr-xr-x (755 or similar)
   ```

3. **Check directory permissions:**
   ```bash
   ls -la /usr/local/bin/  # Parent directory must be readable
   ```

---

### "Too many open files"

**Error Message:**
```
OSError: [Errno 24] Too many open files
```

**Root Cause:**
System file descriptor limit exceeded (usually from concurrent requests or unclosed connections).

**Solutions:**

1. **Check current limit:**
   ```bash
   ulimit -n  # Show current limit
   ```

2. **Increase limit:**
   ```bash
   ulimit -n 4096  # Temporary increase
   # For permanent: edit /etc/security/limits.conf
   ```

3. **Reduce concurrent requests:**
   If running many requests in parallel, reduce concurrency.

4. **Ensure proper cleanup:**
   In Mesh code, ensure all file handles are closed after use.

---

### Tests Failing

**Error Message:**
```
pytest tests/ -v
FAILED tests/test_all_tools.py::TestGeminiCliProviderIntegration::test_complete_simple_prompt
```

**Solutions:**

1. **Check environment is configured:**
   ```bash
   python -c "from utils.env import validate_provider_environment; validate_provider_environment()"
   ```

2. **Run specific test with verbose output:**
   ```bash
   pytest tests/test_all_tools.py::TestGeminiCliProviderIntegration::test_complete_simple_prompt -vv -s
   ```

3. **Check Python version:**
   ```bash
   python --version  # Must be 3.10+
   ```

4. **Check dependencies:**
   ```bash
   pip install -r requirements.txt
   pip list | grep pytest
   ```

5. **Clear cache:**
   ```bash
   rm -rf __pycache__ .pytest_cache
   pytest tests/
   ```

---

### Mesh Server Not Responding

**Symptom:**
Claude CLI connects but no responses from tools.

**Solutions:**

1. **Check server is running:**
   ```bash
   ps aux | grep mcp_server
   ```

2. **Check logs:**
   ```bash
   LOGLEVEL=DEBUG python -m mcp_server 2>&1 | tail -20
   ```

3. **Verify MCP connection:**
   ```bash
   claude mcp list
   # Should show: mesh (status: running)
   ```

4. **Restart server:**
   ```bash
   kill [server-pid]
   python -m mcp_server
   ```

5. **Check config:**
   Verify `GEMINI_CLI_PATH`, `CODEX_CLI_PATH`, `CLI_TIMEOUT_SECONDS` are set correctly.

---

## Debug Checklist

When troubleshooting, go through this checklist:

- [ ] Check Python version: `python --version` (must be 3.10+)
- [ ] Check dependencies: `pip list | grep -E 'pytest|pydantic'`
- [ ] Check CLI tools: `which gemini && which codex`
- [ ] Check environment variables: `env | grep -E 'GEMINI|CODEX|OPENROUTER'`
- [ ] Test CLI manually: `gemini generate --prompt "test"`
- [ ] Check network: `ping google.com` and `curl -I https://openrouter.ai`
- [ ] Check logs: `LOGLEVEL=DEBUG python -m mcp_server`
- [ ] Check system resources: `top`, `df -h`, `free -h`
- [ ] Verify file permissions: `ls -la $(which gemini)`
- [ ] Run tests: `pytest tests/ -v`

---

## Getting Help

If issues persist:

1. **Collect debug information:**
   ```bash
   echo "=== Environment ===" && env | grep -E 'GEMINI|CODEX|OPENROUTER|LOGLEVEL'
   echo "=== CLIs ===" && which gemini codex
   echo "=== Python ===" && python --version
   echo "=== Tests ===" && pytest tests/ -v --tb=short
   ```

2. **Enable debug logging:**
   ```bash
   LOGLEVEL=DEBUG python -m mcp_server 2>&1 > /tmp/mesh-debug.log
   # Reproduce issue
   tail -100 /tmp/mesh-debug.log
   ```

3. **Report issue with:**
   - Full error message
   - Debug logs from above
   - Steps to reproduce
   - Expected vs. actual behavior
   - System info: `uname -a`, Python version, OS
