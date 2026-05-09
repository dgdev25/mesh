# Troubleshooting Guide

## Quick Debugging Steps

If you're experiencing issues with the Mesh MCP Server, follow these steps:

### 1. Check MCP Connection

Open Claude Desktop and type `/mcp` to see if mesh is connected:
- ✅ If mesh appears in the list, the connection is working
- ❌ If not listed or shows an error, continue to step 2

### 2. Launch Claude with Debug Mode

Close Claude Desktop and restart with debug logging:

```bash
# macOS/Linux
claude --debug

# Windows (in WSL2)
claude.exe --debug
```

Look for error messages in the console output, especially:
- API key errors
- Python/environment issues
- File permission errors

### 3. Verify API Keys

Check that your API keys are properly set:

```bash
# Check your .env file
cat .env

# Ensure OPENROUTER_API_KEY is set, or that gemini/codex CLIs are on PATH:
# OPENROUTER_API_KEY=sk-or-v1-...
```

If you need to update your API keys, edit the `.env` file and then restart Claude for changes to take effect.

### 4. Check Server Logs

View the server logs for detailed error information:

```bash
# View recent logs
tail -n 100 logs/mcp_server.log

# Follow logs in real-time
tail -f logs/mcp_server.log

# Or use the -f flag when starting to automatically follow logs
tail -f logs/mcp_server.log

# Search for errors
grep "ERROR" logs/mcp_server.log
```

See [Logging Documentation](logging.md) for more details on accessing logs.

### 5. Common Issues

**"Connection failed" in Claude Desktop**
- Ensure the server path is correct in your Claude config
- Run `./setup.sh` to verify setup and see configuration
- Check that Python is installed: `python3 --version`

**"API key environment variable is required"**
- Add your API key to the `.env` file
- Restart Claude Desktop after updating `.env`

**File path errors**
- Always use absolute paths: `/Users/you/project/file.py`
- Never use relative paths: `./file.py`

**Python module not found**
- Run `./setup.sh` to reinstall dependencies
- Check virtual environment is activated: should see `.mesh_venv` in the Python path

### 6. Environment Issues

**Virtual Environment Problems**
```bash
# Reset environment completely
rm -rf .mesh_venv
./setup.sh
```

**Permission Issues**
```bash
# Ensure script is executable
chmod +x setup.sh
```

### 7. Still Having Issues?

If the problem persists after trying these steps:

1. **Reproduce the issue** - Note the exact steps that cause the problem
2. **Collect logs** - Save relevant error messages from Claude debug mode and server logs
3. **Open a GitHub issue** with:
   - Your operating system
   - Python version: `python3 --version`
   - Error messages from logs
   - Steps to reproduce
   - What you've already tried

## Windows Users

**Important**: Windows users must use WSL2. Install it with:

```powershell
wsl --install -d Ubuntu
```

Then follow the standard setup inside WSL2.