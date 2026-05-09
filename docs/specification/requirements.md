# Mesh MCP Server — Requirements

## Overview

Mesh is a CLI-first variant of Mesh MCP Server that routes AI tool calls through local CLI tools (Gemini CLI, Codex CLI) instead of cloud API keys. It maintains 100% API compatibility with Mesh while replacing the provider implementation layer.

## Functional Requirements

### FR-001: CLI-Based Provider Execution
The server MUST execute AI requests through local CLI tools rather than SDKs.
- Gemini requests → `gemini` CLI command
- OpenAI/Codex requests → `codex` CLI command
- Full response collection before returning (no streaming)

### FR-002: Graceful Fallback to OpenRouter
If Gemini or Codex CLIs fail or are unavailable, the server MUST fall back to OpenRouter API.
- OpenRouter requires API key (optional, environment variable only)
- Fallback MUST be transparent to caller
- Attempt CLI first, then fallback, then final error

### FR-003: All 50+ Mesh Tools Compatible
Every tool from Mesh (chat, analyze, codereview, debug, testgen, etc.) MUST work identically.
- No tool-specific code changes required
- Provider interface abstraction handles all differences

### FR-004: Subprocess Error Handling
CLI tool failures MUST be caught and logged with clear error messages.
- Timeout handling (default 30s per request)
- Signal handling (SIGTERM, SIGKILL cleanup)
- Non-zero exit codes → fallback or error

### FR-005: Configuration Management
CLI tool paths and OpenRouter credentials MUST be environment-configurable.
- `GEMINI_CLI_PATH` → path to gemini binary (default: "gemini")
- `CODEX_CLI_PATH` → path to codex binary (default: "codex")
- `OPENROUTER_API_KEY` → optional fallback API key

## Non-Functional Requirements

### NFR-001: Performance
- CLI request latency: <5s per request (CLI overhead acceptable)
- Fallback decision time: <500ms
- No regression vs. Mesh response times (within 10%)

### NFR-002: Reliability
- All CLI invocations MUST include timeout protection
- All subprocess outputs MUST be validated before parsing
- Failed CLI calls MUST never crash the server (graceful fallback)

### NFR-003: Observability
- CLI command execution logged with args (no secrets in logs)
- Provider selection logged (CLI vs. fallback)
- Error details captured for debugging

### NFR-004: Security
- No secrets in subprocess arguments
- No eval/exec of subprocess output
- API keys only in environment variables (not config files)

## Success Criteria

✅ All 50+ Mesh tools execute and return correct responses  
✅ Gemini CLI failures → fallback to Codex/OpenRouter  
✅ Codex CLI failures → fallback to OpenRouter  
✅ OpenRouter failures → return clear error to caller  
✅ Integration tests pass (all tools tested)  
✅ Setup guide + architecture docs complete  
✅ Zero security vulnerabilities in subprocess handling
