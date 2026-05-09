# Mesh Implementation Plan — Final

## Phase Overview

**Total Modules:** 9  
**Total Agents:** 3  
**Phases:** 3 (sequential) + Testing + Docs  
**Estimated Time:** 6–8 hours

---

## Complete Execution Plan

| Phase | Modules | Agents | Skill(s) | Duration |
|-------|---------|--------|----------|----------|
| **Phase 1** | 1–4 (Foundation) | `backend-dev-a` | `python`, `web-apis` | 2.5 hrs |
| **Phase 2** | 5–7 (Integration) | `backend-dev-b` | `python`, `security-patterns` | 1.5 hrs |
| **Phase 3** | 8 (Tests) | `tester` | `javascript-testing-patterns` | 1.5 hrs |
| **Final** | 9 (Docs) | Manual | — | 0.5 hrs |

---

## Module → Agent Mapping

### Phase 1: Foundation (backend-dev-a)
Build the core CLI execution layer

**Modules 1–4:**
1. CLI Output Parser (`providers/shared/cli_output.py`)
2. CliProvider Base Class (`providers/cli_base.py`)
3. GeminiCliProvider (`providers/gemini_cli.py`)
4. CodexCliProvider (`providers/codex_cli.py`)

**Deliverables:**
- ✅ Async subprocess execution with timeout protection
- ✅ JSON/text output parsing with error handling
- ✅ GeminiCliProvider with proper arg formatting
- ✅ CodexCliProvider with proper arg formatting
- ✅ Unit tests for output parsing and providers
- ✅ Local verification (run gemini/codex CLIs manually)

**Dependencies:** None (can start immediately)  
**Success Metric:** All provider unit tests pass

---

### Phase 2: Integration (backend-dev-b)
Implement error handling, fallback, and configuration

**Modules 5–7:**
5. Error Handling & Retry Logic
6. OpenRouter Fallback Provider
7. Config/Env Management

**Deliverables:**
- ✅ Fallback chain logic in registry
- ✅ OpenRouter integration (reuse existing provider)
- ✅ Environment variable config (CLI paths, timeouts, API keys)
- ✅ Env-var validation on startup
- ✅ Logging for provider selection (which backend was used)

**Dependencies:** Must complete Phase 1 first  
**Success Metric:** Config loads without errors, fallback chain works

---

### Phase 3: Testing (tester)
Comprehensive integration testing

**Module 8: Integration Tests**

**Deliverables:**
- ✅ Unit tests: Provider subprocess execution, timeout, fallback
- ✅ Tool tests: All 50+ PAL tools called via Mesh providers
- ✅ Fallback tests: Simulate CLI failures, verify fallback works
- ✅ Response validation: Ensure ModelResponse format unchanged
- ✅ Edge case tests: Empty input, long prompts, special chars

**Dependencies:** Must complete Phase 1 + 2 first  
**Success Metric:** All integration tests pass, 100%+ tool coverage

---

### Phase 4: Documentation (Manual)
Final documentation and setup guides

**Module 9: Documentation**

**Deliverables:**
- ✅ Setup guide: Installation, environment config, local testing
- ✅ API reference: Provider interfaces, method signatures
- ✅ Troubleshooting: Common errors and fixes
- ✅ Update README with Mesh info

**Dependencies:** All modules complete  
**Success Metric:** Guide is tested (user can follow it cold)

---

## Dependency Chain

```
Phase 1: Foundation
├── Module 1: CLI Output Parser
├── Module 2: CliProvider Base ← depends on 1
├── Module 3: GeminiCliProvider ← depends on 2
└── Module 4: CodexCliProvider ← depends on 2
    ↓
Phase 2: Integration (starts after Phase 1 complete)
├── Module 5: Error Handling ← depends on 3, 4
├── Module 6: OpenRouter Fallback ← depends on 5
└── Module 7: Config/Env ← depends on 3, 4, 6
    ↓
Phase 3: Testing (starts after Phase 2 complete)
└── Module 8: Integration Tests ← depends on 3, 4, 6, 7
    ↓
Phase 4: Documentation (starts after Phase 3 complete)
└── Module 9: Documentation ← depends on 8
```

---

## Parallel Execution Within Phases

### Phase 1 (2.5 hrs)
- **backend-dev-a alone:** Build modules 1–4 sequentially
  - CLI Output Parser (30 min)
  - CliProvider Base (45 min)
  - GeminiCliProvider (30 min)
  - CodexCliProvider (30 min)

### Phase 2 (1.5 hrs)
- **backend-dev-b alone:** Build modules 5–7 sequentially
  - Error Handling & Retry (30 min)
  - OpenRouter Fallback (20 min)
  - Config/Env (20 min)

### Phase 3 (1.5 hrs)
- **tester alone:** Write all integration tests
  - Provider unit tests (20 min)
  - Tool integration tests (50 min)
  - Fallback tests (20 min)

### Phase 4 (0.5 hrs)
- **Manual:** Write setup guide + API reference

---

## Quality Gates

✅ **Before Phase 2:** All Phase 1 code reviewed, tests passing  
✅ **Before Phase 3:** All Phase 2 code reviewed, config validated  
✅ **Before Phase 4:** All Phase 3 tests passing (100%+ coverage)  
✅ **Final:** Zero security warnings, code simplified

---

## Risk Mitigation

| Risk | Mitigation |
|------|-----------|
| CLI not installed on test machine | Environment setup doc includes fallback to OpenRouter |
| Subprocess timeout handling | Test timeouts explicitly, set conservative default (30s) |
| Fallback logic cascades incorrectly | Unit test each fallback transition |
| Config loading fails silently | Validate all env vars at startup, log warnings |
| Tool incompatibilities | Run all 50+ tools with new providers before shipping |

---

## Success Criteria (Final)

✅ All 50+ PAL tools execute identically via Mesh  
✅ Gemini CLI → (fail) → Codex CLI → (fail) → OpenRouter works  
✅ Integration test suite passes with 100%+ tool coverage  
✅ Setup guide allows user to run Mesh locally  
✅ Zero subprocess security issues (no command injection, etc.)  
✅ API compatibility verified: Mesh drop-in replacement for PAL  

---

## Files Summary

**New Files Created:**
- `providers/shared/cli_output.py`
- `providers/cli_base.py`
- `providers/gemini_cli.py`
- `providers/codex_cli.py`
- `tests/test_providers_cli.py`
- `tests/test_all_tools.py`
- `docs/architecture/setup-guide.md`
- `docs/architecture/api-reference.md`

**Files Modified:**
- `config.py`
- `utils/env.py`
- `providers/registry.py`
- `README.md`

---

## Next: Approval

Ready to proceed with implementation?  
**Option A:** Yes, begin Phase 1 immediately  
**Option B:** Review plan changes first  
**Option C:** Need clarification on specific modules
