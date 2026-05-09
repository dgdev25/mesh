# Mesh Documentation Index

## Overview

Mesh is a CLI-first MCP server that routes AI requests through local command-line tools (Gemini CLI, Codex CLI) instead of cloud SDKs. It maintains complete API compatibility with Mesh while replacing the provider implementation.

**Status:** Architecture designed, ready for implementation  
**Modules:** 9  
**Estimated Dev Time:** 6–8 hours  
**Team Size:** 1–2 developers  

---

## Quick Navigation

### For Getting Started
- **[Specification & Requirements](specification/requirements.md)** — What Mesh does, success criteria
- **[Architecture Overview](architecture/design.md)** — System design, data flow, module dependencies

### For Implementation
- **[Implementation Guide](architecture/implementation-guide.md)** — Module-by-module breakdown, code examples
- **Setup Guide** — (TODO) Installation, environment configuration, local testing

### For Reference
- **API Reference** — (TODO) Provider interface, method signatures
- **Testing Strategy** — (TODO) Unit, integration, E2E test matrix

---

## Modules at a Glance

| # | Name | Purpose | Dependencies |
|---|------|---------|--------------|
| 1 | CLI Output Parser | Parse subprocess results (JSON/text) | — |
| 2 | CliProvider Base | Abstract subprocess execution, timeouts | 1 |
| 3 | GeminiCliProvider | Wrap `gemini` CLI command | 2 |
| 4 | CodexCliProvider | Wrap `codex` CLI command | 2 |
| 5 | Error Handling | Implement fallback chain logic | 3, 4 |
| 6 | OpenRouter Fallback | Optional API-based fallback | 5 |
| 7 | Config/Env | CLI paths, API keys, timeouts | 3, 4, 6 |
| 8 | Integration Tests | Verify all 50+ tools work | 3, 4, 6, 7 |
| 9 | Documentation | User-facing guides & API docs | 8 |

---

## Key Architectural Decisions

### Decision 1: Full Response Collection (No Streaming)
- Simpler subprocess handling
- Easier error recovery
- Acceptable latency for MCP use case

### Decision 2: Graceful Fallback Chain
- Gemini CLI → Codex CLI → OpenRouter API
- Transparent to callers
- Enables graceful degradation

### Decision 3: All 50+ Mesh Tools Included
- No tool-specific modifications required
- Provider abstraction handles all differences
- Complete feature parity with PAL

### Decision 4: Environment-Based Configuration
- CLI paths: `GEMINI_CLI_PATH`, `CODEX_CLI_PATH`
- API key: `OPENROUTER_API_KEY` (optional)
- Timeout: `CLI_TIMEOUT_SECONDS`

---

## Development Workflow

### Phase 1: Foundation (Modules 1–4)
Implement CLI execution layer and provider wrappers. Requires:
- Subprocess handling expertise
- JSON/text parsing
- CLI tool familiarity

### Phase 2: Integration (Modules 5–7)
Implement error handling and configuration. Requires:
- Error handling patterns
- Environment configuration management

### Phase 3: Validation (Modules 8–9)
Testing and documentation. Requires:
- Integration test authorship
- Technical documentation writing

---

## Success Criteria

✅ All 50+ Mesh tools execute and return correct responses  
✅ Graceful fallback from CLI → OpenRouter works  
✅ Integration tests pass (all tools tested)  
✅ Zero security vulnerabilities in subprocess handling  
✅ Documentation complete and reviewed  
✅ Setup guide allows users to run locally  

---

## Files Changed/Created

### New Files
- `providers/cli_base.py` — Abstract CLI provider
- `providers/gemini_cli.py` — Gemini CLI implementation
- `providers/codex_cli.py` — Codex CLI implementation
- `providers/shared/cli_output.py` — Output parsing
- `tests/test_providers_cli.py` — Provider unit tests
- `tests/test_all_tools.py` — Tool integration tests
- `docs/architecture/setup-guide.md` — (TODO)
- `docs/architecture/api-reference.md` — (TODO)

### Modified Files
- `config.py` — Add CLI paths and timeout config
- `utils/env.py` — Add env var helpers
- `providers/registry.py` — Add fallback logic
- `README.md` — Update with Mesh info

---

## Next Steps

1. **Review this documentation** — Ensure alignment on architecture
2. **Proceed to Step 3** — Skill search per module
3. **Proceed to Step 4** — Agent assignment per module
4. **Review final plan** — Confirm execution order and agent roles
5. **Begin implementation** — Execute modules in dependency order
