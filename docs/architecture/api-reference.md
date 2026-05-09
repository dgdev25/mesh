# Mesh — API Reference

## Overview

Mesh MCP Server exposes 20+ Mesh tools through the Model Context Protocol (MCP). Tools call the provider layer which routes requests through CLI tools (Gemini, Codex) or OpenRouter API.

---

## Provider Interface

All providers inherit from `ModelProvider` base class and implement the following interface:

### Abstract Base Class: `ModelProvider`

**Location:** `providers/shared.py`

```python
class ModelProvider:
    """Abstract provider for AI model requests."""
    
    @abstractmethod
    async def complete(
        self,
        prompt: str,
        model: str,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        **kwargs
    ) -> ModelResponse:
        """Generate content from prompt.
        
        Args:
            prompt: Input prompt text
            model: Model identifier (e.g., "gemini-2.5-flash", "gpt-4-turbo")
            temperature: Sampling temperature (0.0-2.0)
            max_tokens: Maximum output tokens
            **kwargs: Additional provider-specific parameters
            
        Returns:
            ModelResponse with content, success status, and metadata
            
        Raises:
            CliError: For CLI-based providers (not found, timeout, invalid output)
            APIError: For API-based providers (rate limit, auth, etc.)
        """
```

### Response Format: `ModelResponse`

```python
@dataclass
class ModelResponse:
    """Unified response format across all providers."""
    
    content: str          # Generated content (empty if error)
    success: bool         # True if generation succeeded
    error: Optional[str]  # Error message (None if success)
    tokens_used: int      # Total tokens (input + output)
    cost_usd: float       # Estimated cost
    duration_ms: float    # Request duration in milliseconds
```

---

## CLI Providers

### GeminiCliProvider

**Location:** `providers/gemini_cli.py`

Wraps the `gemini` CLI command for Gemini model access.

```python
class GeminiCliProvider(CliProvider):
    """Execute requests through Gemini CLI binary."""
    
    def __init__(self, cli_path: str = "gemini", timeout_s: int = 30):
        """Initialize provider.
        
        Args:
            cli_path: Path to gemini binary (default: "gemini" from PATH)
            timeout_s: Subprocess timeout in seconds (default: 30)
        """
    
    async def complete(
        self,
        prompt: str,
        model: str = "gemini-2.5-flash",
        temperature: float = 0.7,
        max_tokens: int = 4096,
        thinking_mode: str = "disabled",  # "disabled", "agentic"
        **kwargs
    ) -> ModelResponse:
        """Generate content via Gemini CLI.
        
        Args:
            prompt: Input prompt
            model: Gemini model (e.g., "gemini-2.5-flash", "gemini-pro")
            temperature: 0.0-2.0
            max_tokens: Output limit
            thinking_mode: Extended thinking mode (Gemini-specific)
            
        Returns:
            ModelResponse
            
        Raises:
            CliNotFoundError: If gemini binary not in PATH
            CliTimeoutError: If request exceeds timeout
            CliError: If CLI output is invalid
        """
```

**CLI Invocation Pattern:**
```bash
gemini generate \
  --prompt "your prompt here" \
  --model "gemini-2.5-flash" \
  --temperature 0.7 \
  --max-tokens 4096 \
  --thinking-mode disabled
```

**Supported Models:**
- `gemini-2.5-flash` (recommended for speed)
- `gemini-2.5-pro` (recommended for quality)
- `gemini-1.5-flash` (legacy)
- `gemini-1.5-pro` (legacy)

---

### CodexCliProvider

**Location:** `providers/codex_cli.py`

Wraps the `codex` CLI command for OpenAI model access.

```python
class CodexCliProvider(CliProvider):
    """Execute requests through Codex CLI binary."""
    
    def __init__(self, cli_path: str = "codex", timeout_s: int = 30):
        """Initialize provider.
        
        Args:
            cli_path: Path to codex binary (default: "codex" from PATH)
            timeout_s: Subprocess timeout in seconds (default: 30)
        """
    
    async def complete(
        self,
        prompt: str,
        model: str = "gpt-4-turbo",
        temperature: float = 0.7,
        max_tokens: int = 4096,
        top_p: float = 1.0,
        frequency_penalty: float = 0.0,
        presence_penalty: float = 0.0,
        **kwargs
    ) -> ModelResponse:
        """Generate content via Codex CLI.
        
        Args:
            prompt: Input prompt
            model: OpenAI model (e.g., "gpt-4-turbo", "gpt-4", "gpt-3.5-turbo")
            temperature: 0.0-2.0
            max_tokens: Output limit
            top_p: Nucleus sampling (0.0-1.0)
            frequency_penalty: Reduce repetition (-2.0 to 2.0)
            presence_penalty: Encourage new tokens (-2.0 to 2.0)
            
        Returns:
            ModelResponse
            
        Raises:
            CliNotFoundError: If codex binary not in PATH
            CliTimeoutError: If request exceeds timeout
            CliError: If CLI output is invalid
        """
```

**CLI Invocation Pattern:**
```bash
codex chat-completion \
  --message "your prompt here" \
  --model "gpt-4-turbo" \
  --temperature 0.7 \
  --max-tokens 4096 \
  --top-p 1.0
```

**Supported Models:**
- `gpt-4-turbo` (recommended for speed/quality)
- `gpt-4` (highest quality)
- `gpt-3.5-turbo` (fastest)

---

### CliProvider (Abstract Base)

**Location:** `providers/cli_base.py`

Base class for CLI-based providers. Handles subprocess execution, timeout management, and error classification.

```python
class CliProvider(ModelProvider):
    """Abstract CLI provider."""
    
    async def _run_cli(
        self,
        args: List[str]
    ) -> CliOutput:
        """Execute CLI command with timeout protection.
        
        Args:
            args: Command arguments (first element is CLI binary)
            
        Returns:
            CliOutput containing stdout, stderr, exit code, duration
            
        Raises:
            CliTimeoutError: If subprocess exceeds timeout_s
            CliNotFoundError: If CLI binary not found
            CliError: If subprocess returns error output
        """
    
    def classify_error(self, error: Exception) -> str:
        """Classify error type for fallback decisions.
        
        Returns:
            "not_found" | "timeout" | "invalid_output" | "unknown"
        """
    
    def should_fallback(self, error: Exception) -> bool:
        """Determine if error warrants fallback to next provider.
        
        All CliError types return True. Other errors return False.
        """
```

---

## API Provider

### OpenRouterProvider

**Location:** `providers/openrouter.py`

Fallback provider using OpenRouter API. Automatically used if CLI providers fail and `OPENROUTER_API_KEY` is set.

```python
class OpenRouterProvider(ModelProvider):
    """Execute requests through OpenRouter API."""
    
    def __init__(self, api_key: str):
        """Initialize with API key."""
    
    async def complete(
        self,
        prompt: str,
        model: str,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        **kwargs
    ) -> ModelResponse:
        """Generate content via OpenRouter API.
        
        Supports all OpenRouter-available models via unified API.
        """
```

**When Used:**
- Gemini CLI unavailable AND Codex CLI unavailable
- OR both CLIs timeout/fail
- AND `OPENROUTER_API_KEY` environment variable is set

---

## Provider Registry

**Location:** `providers/registry.py`

Central registry for provider selection and fallback chain management.

```python
class ModelProviderRegistry:
    """Manages provider lifecycle and fallback chain."""
    
    @staticmethod
    def get_provider_for_model(model_name: str) -> Optional[ModelProvider]:
        """Get provider for a specific model.
        
        Args:
            model_name: Model identifier (e.g., "gemini-2.5-flash")
            
        Returns:
            Provider instance or None if model not available
        """
    
    @staticmethod
    async def invoke_with_fallback(request: Dict) -> ModelResponse:
        """Execute request with fallback chain.
        
        Tries providers in order:
        1. Gemini CLI (if available)
        2. Codex CLI (if Gemini fails)
        3. OpenRouter API (if both CLIs fail and API key set)
        
        Args:
            request: Dict with prompt, model, temperature, max_tokens, etc.
            
        Returns:
            ModelResponse from first successful provider
            
        Raises:
            RuntimeError: If all providers exhausted
        """
    
    @staticmethod
    def get_available_model_names() -> List[str]:
        """Get list of all available models from enabled providers."""
```

---

## CLI Output & Error Handling

### CliOutput

**Location:** `providers/shared/cli_output.py`

Represents parsed CLI command output.

```python
@dataclass
class CliOutput:
    """CLI command execution result."""
    
    stdout: str          # Command output
    stderr: str          # Command error output
    exit_code: int       # Exit code (0 = success)
    command: str         # Command that was executed
    duration_ms: float   # Execution time
    
    @property
    def success(self) -> bool:
        """True if exit_code == 0."""
    
    @property
    def raw_output(self) -> str:
        """Return stdout if non-empty, else stderr."""
```

### Error Classes

```python
class CliError(Exception):
    """Base CLI error."""

class CliNotFoundError(CliError):
    """CLI binary not found in PATH."""

class CliTimeoutError(CliError):
    """CLI execution exceeded timeout."""
```

### CliResponseParser

**Location:** `providers/shared/cli_output.py`

Utilities for parsing and validating CLI output.

```python
class CliResponseParser:
    """Parse and validate CLI output."""
    
    @staticmethod
    def parse_json(output: str) -> dict:
        """Parse JSON from output string.
        
        Raises:
            CliError: If invalid JSON
        """
    
    @staticmethod
    def parse_text(output: str) -> str:
        """Parse plain text from output."""
    
    @staticmethod
    def validate_output(
        output: CliOutput,
        expected_format: str
    ) -> bool:
        """Validate output matches expected format.
        
        Args:
            expected_format: "json" or "text"
            
        Returns:
            True if valid
            
        Raises:
            CliError: If invalid
        """
    
    @staticmethod
    def extract_json_field(
        output: CliOutput,
        field_name: str,
        default: Any = None
    ) -> Any:
        """Extract a field from JSON output.
        
        Args:
            field_name: JSON key to extract
            default: Default value if missing
            
        Returns:
            Field value or default
            
        Raises:
            CliError: If field missing and no default
        """
```

---

## Configuration

### config.py

```python
# CLI tool paths (configurable via environment variables)
CLI_PATHS: Dict[str, str] = {
    "gemini": os.getenv("GEMINI_CLI_PATH", "gemini"),
    "codex": os.getenv("CODEX_CLI_PATH", "codex"),
}

# Subprocess timeout in seconds
CLI_TIMEOUT_SECONDS: int = int(os.getenv("CLI_TIMEOUT_SECONDS", "30"))

# Optional OpenRouter fallback
OPENROUTER_API_KEY: Optional[str] = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_ENABLED: bool = bool(OPENROUTER_API_KEY)
```

### utils/env.py

```python
def validate_cli_environment() -> Dict[str, bool]:
    """Check if CLI tools are available.
    
    Returns:
        Dict mapping tool names to availability status
        
    Example:
        {
            "gemini": True,
            "codex": False,  # Not found
        }
    """

def validate_provider_environment() -> None:
    """Validate all provider configuration.
    
    Logs status of:
    - CLI tool availability
    - OpenRouter API key format
    - Timeout settings
    
    Raises:
        No exceptions; logs warnings for unavailable providers
    """
```

---

## Tool Examples

### Using Chat Tool

```python
from providers.registry import ModelProviderRegistry

async def example():
    request = {
        "prompt": "Explain async/await in Python",
        "model": "gemini-2.5-flash",
        "temperature": 0.7,
        "max_tokens": 2048,
    }
    
    response = await ModelProviderRegistry.invoke_with_fallback(request)
    
    if response.success:
        print(response.content)
    else:
        print(f"Error: {response.error}")
```

### Using with Fallback

When Gemini CLI is not available, the registry automatically tries Codex, then OpenRouter:

```python
# Provider selection is automatic
# No code changes needed - just call invoke_with_fallback()
response = await ModelProviderRegistry.invoke_with_fallback(request)

# Logs will show which provider was used:
# INFO: Using GeminiCliProvider for model gemini-2.5-flash
# or
# INFO: Fallback to CodexCliProvider (Gemini failed: CliNotFoundError)
# or
# INFO: Fallback to OpenRouterProvider (Codex failed: CliTimeoutError)
```

---

## Logging

Enable debug logging to see provider selection and fallback details:

```bash
LOGLEVEL=DEBUG python -m mcp_server
```

**Example logs:**
```
INFO: Invoking request with model: gemini-2.5-flash
DEBUG: Trying GeminiCliProvider...
DEBUG: Running CLI: /usr/local/bin/gemini generate --prompt "..." --model gemini-2.5-flash
DEBUG: CLI completed in 245ms, exit code: 0
INFO: GeminiCliProvider succeeded
```

**Fallback logs:**
```
INFO: Invoking request with model: gemini-2.5-flash
DEBUG: Trying GeminiCliProvider...
DEBUG: CLI error: CliNotFoundError: gemini not found
INFO: Fallback to CodexCliProvider
DEBUG: Trying CodexCliProvider...
DEBUG: Running CLI: /usr/bin/codex chat-completion --message "..." --model gpt-4-turbo
DEBUG: CLI completed in 523ms, exit code: 0
INFO: CodexCliProvider succeeded
```

---

## Performance Characteristics

| Provider | Latency | Cost | Notes |
|----------|---------|------|-------|
| GeminiCliProvider | 100-300ms | Low | Local execution |
| CodexCliProvider | 100-500ms | Medium | Local execution |
| OpenRouterProvider | 500-5000ms | Medium-High | API-based, network overhead |

---

## Error Handling

All providers return `ModelResponse` with consistent error format:

```python
# On error, response contains:
response.success = False
response.error = "Human-readable error message"
response.content = ""  # Empty
response.tokens_used = 0

# Callers should check:
if response.success:
    process(response.content)
else:
    log_error(response.error)
```

Never raise exceptions to callers. All errors are captured in `ModelResponse.error`.

---

## Compatibility

Mesh maintains 100% API compatibility with PAL:
- All tool signatures unchanged
- All response formats unchanged
- All model parameters supported
- Transparent provider switching (no code changes needed)

For tool-specific documentation, see individual tool files in `tools/` directory.
