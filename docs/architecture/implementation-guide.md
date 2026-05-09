# Implementation Guide: Module-by-Module

## Module 1: CLI Output Parser

**File:** `providers/shared/cli_output.py`

**Purpose:** Standardize parsing of subprocess output (stdout, stderr, exit code)

**Deliverables:**
```python
class CliOutput:
    stdout: str
    stderr: str
    exit_code: int
    command: str
    duration_ms: float

class CliResponseParser:
    @staticmethod
    def parse_json(output: str) -> dict
    @staticmethod
    def parse_text(output: str) -> str
    @staticmethod
    def validate_output(output: CliOutput, expected_format: str) -> bool
```

**Tests:** Unit tests for JSON parsing, error cases, malformed input

---

## Module 2: CliProvider Base Class

**File:** `providers/cli_base.py`

**Purpose:** Abstract subprocess execution with error handling, timeouts, response collection

**Key Features:**
- Async subprocess invocation with timeout protection
- Signal handling (graceful shutdown)
- Full response collection (no streaming)
- Fallback trigger on errors

**Deliverables:**
```python
class CliProvider(ModelProvider):
    def __init__(self, cli_path: str, timeout_s: int = 30)
    async def _run_cli(self, args: List[str]) -> CliOutput
    async def invoke_with_fallback(self, request) -> ModelResponse
    def _should_fallback(self, error: Exception) -> bool
```

**Tests:** Subprocess execution, timeout simulation, signal handling

---

## Module 3: GeminiCliProvider

**File:** `providers/gemini_cli.py`

**Purpose:** Wrap `gemini` CLI command with proper argument formatting

**Key Methods:**
```python
class GeminiCliProvider(CliProvider):
    PROVIDER_TYPE = ProviderType.GEMINI
    
    def __init__(self, cli_path: str = "gemini")
    def _build_args(self, prompt: str, model: str, temp: float, ...) -> List[str]
    def _parse_response(self, output: CliOutput) -> ModelResponse
    async def complete(self, prompt: str, **kwargs) -> ModelResponse
```

**CLI Invocation Pattern:**
```bash
gemini generate \
  --prompt "your prompt here" \
  --model "gemini-2-flash" \
  --temperature 0.7 \
  --max-tokens 4096
```

**Tests:** Argument building, response parsing, model selection

---

## Module 4: CodexCliProvider

**File:** `providers/codex_cli.py`

**Purpose:** Wrap `codex` (OpenAI) CLI command

**Similar structure to GeminiCliProvider:**
```python
class CodexCliProvider(CliProvider):
    PROVIDER_TYPE = ProviderType.OPENAI
    
    def __init__(self, cli_path: str = "codex")
    def _build_args(self, prompt: str, model: str, temp: float, ...) -> List[str]
```

**CLI Invocation Pattern:**
```bash
codex chat-completion \
  --message "your prompt here" \
  --model "gpt-4-turbo" \
  --temperature 0.7
```

**Tests:** Argument building, response parsing, error handling

---

## Module 5: Error Handling & Retry Logic

**File:** `providers/cli_base.py` (extend) + `providers/registry.py` (update)

**Purpose:** Implement fallback chain and retry strategy

**Fallback Chain:**
1. Try Gemini CLI
2. On error, try Codex CLI
3. On error, try OpenRouter (if API key set)
4. On all failures, return error to caller

**Deliverables:**
```python
class CliProvider:
    async def invoke_with_fallback(self, request) -> ModelResponse:
        """Try all providers in order, return first success"""
        
    def _classify_error(self, error: Exception) -> ErrorType
        """CLI not found vs. Timeout vs. Invalid output"""
```

**Retry Strategy:**
- No retries on CLI not found (fallback instead)
- Max 1 retry on timeout (then fallback)
- No retries on invalid output (fallback instead)

**Tests:** Fallback scenarios, error classification, exception propagation

---

## Module 6: OpenRouter Fallback Provider

**File:** `providers/openrouter.py` (reuse/adapt existing)

**Purpose:** Fallback when CLIs unavailable

**Integration Points:**
- Called only if both CLI providers fail
- Requires OPENROUTER_API_KEY environment variable
- Returns same ModelResponse format as CLI providers

**Deliverables:**
- Ensure OpenRouterProvider extends ModelProvider correctly
- Add fallback logic to registry

**Tests:** API key validation, fallback invocation

---

## Module 7: Config/Env Management

**File:** `config.py` (update) + `utils/env.py` (update)

**Purpose:** CLI path detection and fallback configuration

**Environment Variables:**
```bash
GEMINI_CLI_PATH=gemini              # Path to gemini binary
CODEX_CLI_PATH=codex                # Path to codex binary
CLI_TIMEOUT_SECONDS=30              # Subprocess timeout
OPENROUTER_API_KEY=sk-...           # Optional fallback API key
```

**Deliverables:**
```python
# config.py
CLI_PATHS = {
    "gemini": os.getenv("GEMINI_CLI_PATH", "gemini"),
    "codex": os.getenv("CODEX_CLI_PATH", "codex"),
}

CLI_TIMEOUT_SECONDS = int(os.getenv("CLI_TIMEOUT_SECONDS", "30"))
OPENROUTER_ENABLED = bool(os.getenv("OPENROUTER_API_KEY"))
```

**Validation on startup:**
- Check if CLI paths resolve (log warnings if not)
- Verify OPENROUTER_API_KEY format if provided

**Tests:** Env var parsing, fallback logic, missing var handling

---

## Module 8: Integration Tests

**File:** `tests/test_providers_cli.py` + `tests/test_all_tools.py`

**Purpose:** Verify all 50+ tools work with new providers

**Test Coverage:**
- **Provider tests:** Subprocess execution, timeout, fallback
- **Tool tests:** Each of 50+ tools calls its provider and validates response
- **Fallback tests:** Simulate CLI failures, verify fallback works
- **Response format tests:** Verify ModelResponse structure unchanged

**Test Data:**
- Simple prompts with known expected structures
- Edge cases: empty input, long input, special chars

**Tests:** 100+ test cases (all tools × providers × scenarios)

---

## Module 9: Documentation

**File:** `docs/` directory

**Deliverables:**
- ✅ `specification/requirements.md` — Functional/non-functional requirements
- ✅ `architecture/design.md` — System architecture, data flow
- ✅ `architecture/implementation-guide.md` — This file
- `architecture/setup-guide.md` — Installation, configuration
- `architecture/api-reference.md` — CLI provider interface
- `README.md` update — Overview + quick start

---

## Execution Order & Parallelization

**Phase 1 (Serial):** Build foundation
1. Module 1: CLI Output Parser
2. Module 2: CliProvider Base Class
3. Module 3: GeminiCliProvider
4. Module 4: CodexCliProvider

**Phase 2 (Can Overlap):** Error handling & configuration
5. Module 5: Error Handling & Retry Logic
6. Module 6: OpenRouter Fallback
7. Module 7: Config/Env Management

**Phase 3:** Validation & Documentation
8. Module 8: Integration Tests (start after Phase 1 complete)
9. Module 9: Documentation (start after Module 8 complete)

---

## Quality Gates

✅ Before Module 3: cli_output.py has 100% test coverage  
✅ Before Module 5: All providers pass unit tests  
✅ Before Module 8: Config system loads without errors  
✅ Before Module 9: All integration tests pass  
✅ Final: Zero security warnings from code review
