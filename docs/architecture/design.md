# Mesh Architecture

## System Overview

```
MCP Client (Claude)
    ↓
MCP Server (server.py)
    ↓
Tool Router (tools/*)
    ↓
Provider Registry
    ├── CliProvider (base class)
    │   ├── GeminiCliProvider
    │   ├── CodexCliProvider
    │   └── FallbackLogic
    └── OpenRouterProvider (fallback)
    ↓
Subprocess Execution / API Calls
```

## Provider Layer Architecture

### Layer 1: CliProvider (Abstract Base)

**Location:** `providers/cli_base.py`

**Responsibilities:**
- Execute subprocess commands with timeout protection
- Collect full stdout/stderr
- Parse JSON/text responses
- Handle SIGTERM/SIGKILL cleanup
- Convert raw CLI output to `ModelResponse`

**Key Methods:**
```python
class CliProvider(ModelProvider):
    def __init__(self, cli_path: str, timeout: int = 30)
    async def invoke_cli(self, args: List[str]) -> str  # Handles subprocess
    def parse_response(self, raw_output: str) -> ModelResponse
    def handle_timeout() -> ModelResponse  # Fallback trigger
```

### Layer 2: GeminiCliProvider & CodexCliProvider

**Location:** `providers/gemini_cli.py`, `providers/codex_cli.py`

**Responsibilities:**
- Format request arguments for CLI invocation
- Map tool parameters → CLI flags
- Parse CLI-specific response format
- Delegate to CliProvider base for execution

**Example (GeminiCliProvider):**
```python
class GeminiCliProvider(CliProvider):
    async def complete(self, prompt, **kwargs) -> ModelResponse:
        args = self._build_args(prompt, **kwargs)
        # ["gemini", "generate", "--prompt", "...", "--model", "gemini-2"]
        result = await self.invoke_cli(args)
        return self.parse_response(result)
```

### Layer 3: Fallback Logic

**Location:** `providers/registry.py` (ModelProviderRegistry enhancement)

**Behavior:**
```
try:
    response = gemini_cli_provider.invoke(request)
    if response.success:
        return response
except CliUnavailable | Timeout | NonZeroExit:
    try:
        response = codex_cli_provider.invoke(request)
        if response.success:
            return response
    except:
        if OPENROUTER_API_KEY:
            return openrouter_provider.invoke(request)
        else:
            raise final_error
```

## Module Dependency Graph

```
1. CLI Output Parser (lowest level)
   ↓ used by
2. CliProvider Base Class
   ↓ extended by
3. GeminiCliProvider ─┐
4. CodexCliProvider  ├→ 5. Error Handling & Retry Logic
                     │
                     ├→ 6. OpenRouter Fallback (optional)
                     │
                     └→ 7. Config/Env Management
                        ↓ used by
                        8. Integration Tests
                        ↓ validated by
                        9. Documentation
```

## Data Flow: Single Request

```
Tool (e.g., chat.py) calls:
  provider.complete(prompt="...", model="auto", temp=0.7)
    ↓
Registry selects provider based on model routing
    ↓
CliProvider.invoke(request):
  1. Build CLI args from request params
  2. Execute: subprocess.run(['gemini', 'generate', ...], timeout=30)
  3. Collect stdout → validate JSON
  4. Parse response → ModelResponse
  5. Return to tool
    ↓ on CLI error:
  FallbackLogic:
    6. Try next provider (CodexCliProvider)
    7. If all fail and OPENROUTER_API_KEY set:
       → invoke OpenRouterProvider (existing code reused)
    ↓ on final error:
  8. Return error ModelResponse to caller
```

## Configuration & Environment

**File:** `config.py` (update existing)

```python
# CLI paths (from env vars, with defaults)
GEMINI_CLI_PATH = os.getenv("GEMINI_CLI_PATH", "gemini")
CODEX_CLI_PATH = os.getenv("CODEX_CLI_PATH", "codex")

# Subprocess settings
CLI_TIMEOUT_SECONDS = int(os.getenv("CLI_TIMEOUT", "30"))
CLI_FALLBACK_ENABLED = True  # Always try fallback

# OpenRouter fallback (optional)
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", None)
```

## Testing Strategy

### Unit Tests (Module 8a)
- Test CliProvider subprocess execution
- Test response parsing for both CLI formats
- Test timeout handling
- Test fallback logic

### Integration Tests (Module 8b)
- Run all 50+ Mesh tools with Mesh providers
- Verify output matches expected format
- Test fallback path (simulate CLI failure)

### E2E Tests (Module 8c)
- Test full request flow: MCP → Tool → Provider → CLI → Response
- Verify all tools return valid responses

## Error Handling Strategy

```
Error Type          Handling
─────────────────────────────────────────────
CLI not found       → Try next provider
Timeout (30s)       → Fallback immediately
Non-zero exit       → Parse stderr, try fallback
Invalid JSON output → Log, try fallback
No providers work   → Return clear error to MCP client
```

## Security Considerations

- ✅ CLI args built from typed params (no string interpolation)
- ✅ Subprocess output validated before parsing
- ✅ No eval/exec of CLI output
- ✅ Secrets (API keys) only in environment variables
- ✅ stderr captured and logged (no secrets logged)
- ✅ Process cleanup on timeout/error
