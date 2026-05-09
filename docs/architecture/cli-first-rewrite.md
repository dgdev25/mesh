# CLI-First Rewrite Plan

**Status:** Proposed — awaiting approval
**Scope:** In-place refactor of `mesh` MCP server
**Goal:** Reduce provider surface to **CLI subprocess first, OpenRouter HTTP fallback only**

---

## 1. Target Architecture

```
┌──────────────────────────────────────────────┐
│ MCP tools (chat, debug, codereview, ...)     │
└────────────────────┬─────────────────────────┘
                     │
              ModelProviderRegistry
                     │
       ┌─────────────┼──────────────┐
       ▼             ▼              ▼
   GeminiCLI      CodexCLI      OpenRouter
   (subprocess)   (subprocess)  (HTTPS API)
       │             │              │
   `gemini` bin   `codex` bin   openrouter.ai
```

**Selection rule (already implemented in `registry.invoke_with_fallback`):**
1. `gemini` CLI on PATH → use it
2. `codex` CLI on PATH → use it
3. `OPENROUTER_API_KEY` set → use OpenRouter
4. Otherwise → hard error

No direct vendor APIs. No DIAL. No Azure. No custom/Ollama. One auth surface (`OPENROUTER_API_KEY`).

---

## 2. Files to Delete

### Provider modules (~1,597 lines)
| File | Lines | Reason |
|---|---|---|
| `providers/gemini.py` | 522 | Direct Gemini API — replaced by `gemini_cli` |
| `providers/openai.py` | 167 | Direct OpenAI API — replaced by `codex_cli` |
| `providers/azure_openai.py` | 342 | Azure-hosted OpenAI — out of scope |
| `providers/xai.py` | 86 | X.AI direct — covered via OpenRouter if needed |
| `providers/dial.py` | 303 | DIAL unified API — covered via OpenRouter |
| `providers/custom.py` | 177 | Self-hosted/Ollama — out of scope |

### Config files (5 files, ~47 KB)
- `conf/gemini_models.json`
- `conf/openai_models.json`
- `conf/azure_models.json`
- `conf/xai_models.json`
- `conf/dial_models.json`
- `conf/custom_models.json`

**Keep:** `conf/openrouter_models.json` (OpenRouter catalogue — still needed)

### Tests to delete (provider-specific, ~75 KB)
- `tests/test_azure_openai_provider.py`
- `tests/test_xai_provider.py`
- `tests/test_dial_provider.py`
- `tests/test_custom_provider.py`
- `tests/test_custom_openai_temperature_fix.py`
- `tests/test_auto_mode_custom_provider_only.py`
- `tests/test_gemini_token_usage.py`
- `tests/test_openai_provider.py` ← only if it tests the *direct* OpenAI provider, not the OpenAI-compatible base
- `tests/openai_cassettes/`, `tests/gemini_cassettes/` ← VCR fixtures for direct APIs

**Keep & adapt:**
- `tests/test_openrouter_provider.py`
- `tests/test_providers_cli.py` (covers CLI providers — already added)
- `tests/test_provider_routing_bugs.py` (rewrite to reflect new chain)
- `tests/test_provider_retry_logic.py`
- `tests/test_providers.py` (registry behaviour — slim to new providers)

---

## 3. Files to Modify

### `providers/registry.py`
- Remove `GOOGLE`, `AZURE`, `XAI`, `DIAL`, `CUSTOM` from `PROVIDER_PRIORITY_ORDER` (keep `OPENAI` and `OPENROUTER` for the CLI factories that still register under those types — see note below).
- Strip `configure_providers()` branches for direct Gemini/OpenAI/Azure/XAI/DIAL/Custom (lines 519–571).
- Strip `_get_api_key_for_provider()` mappings for dropped types.
- Keep `invoke_with_fallback()` — already correct.
- Drop the `gemini-2.5-flash` ultimate fallback string in `get_preferred_fallback_model()` — no Gemini direct anymore. Replace with a sensible OpenRouter default (e.g. `openai/gpt-5.1` or whatever your OpenRouter catalogue marks default).

**Note on `ProviderType` enum:** `gemini_cli` registers under `ProviderType.GOOGLE` and `codex_cli` registers under `ProviderType.OPENAI`. We can either (a) keep the enum names as-is (cheap, slightly misleading) or (b) rename to `GEMINI_CLI` / `CODEX_CLI`. **Recommendation: keep names** — minimizes blast radius and the value is just an identifier.

### `providers/__init__.py`
Remove dropped provider exports.

### `server.py`
Drop any direct imports of dropped providers, env-key validation for dropped vendors. Update the env-key precondition error to mention only `OPENROUTER_API_KEY` + CLI install.

### `tools/listmodels.py`
Drop sections that enumerate Gemini/OpenAI/Azure/XAI/DIAL/Custom catalogues. Keep only OpenRouter + the two CLI providers.

### `utils/env.py` / `.env.example`
Strip env vars for dropped providers:
- `GEMINI_API_KEY`, `OPENAI_API_KEY` (keep only if you want to allow direct fallback inside the CLI itself — but that's the CLI's concern, not ours)
- `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_API_VERSION`
- `XAI_API_KEY`
- `DIAL_API_KEY`, `DIAL_API_HOST`, `DIAL_API_VERSION`
- `CUSTOM_API_KEY`, `CUSTOM_API_URL`, `CUSTOM_MODEL_NAME`

Keep: `OPENROUTER_API_KEY`, `OPENROUTER_ALLOWED_MODELS`, log/diagnostic vars.

### `utils/model_restrictions.py`
Currently keys restrictions by `ProviderType`. After deletions, only `GOOGLE` (gemini_cli), `OPENAI` (codex_cli), `OPENROUTER` survive. Sweep for unreachable code paths.

### Documentation
- `README.md` — rewrite "Configuration" section: drop multi-provider setup, document CLI-first model with OpenRouter fallback.
- `docs/getting-started.md` — same.
- `docs/troubleshooting.md` — drop provider-specific sections.
- `docs/wsl-setup.md` — same.
- Drop or rewrite any `docs/*provider*.md`.

### Configs
- `conf/__init__.py` — drop references to deleted JSONs.
- Loader code in `providers/openai_compatible.py` (or wherever model JSONs are loaded) — strip per-vendor loader branches.

---

## 4. Migration Steps (ordered)

1. **Snapshot** — commit current state (PAL→Mesh rebrand still pending, finish that sweep first).
2. **Branch** — `feat/cli-first-only`.
3. **Phase 1: rip out direct providers**
   - Delete the 6 provider `.py` files.
   - Delete the 6 conf JSONs.
   - Strip `configure_providers()` and `_get_api_key_for_provider()` in `registry.py`.
   - Strip imports in `providers/__init__.py`, `server.py`.
   - Run `ruff check .` — fix all unused-import warnings.
   - Commit: `refactor(providers): drop direct API providers, CLI-first only`.
4. **Phase 2: prune tests**
   - Delete the provider-specific test files listed above.
   - Update `tests/conftest.py` — drop fixtures for dropped vendors.
   - Update `tests/test_providers.py` and `tests/test_provider_routing_bugs.py` to reflect the new 3-provider world.
   - Run `pytest -x` — fix failures.
   - Commit: `test: prune tests for dropped providers`.
5. **Phase 3: env + docs**
   - Trim `.env.example`, `utils/env.py` allow-list.
   - Rewrite README configuration section.
   - Update `docs/getting-started.md`, `docs/troubleshooting.md`.
   - Commit: `docs: simplify configuration for CLI-first model`.
6. **Phase 4: model catalogue cleanup**
   - `tools/listmodels.py` — collapse to 3 sections.
   - Verify `conf/openrouter_models.json` covers the model aliases users currently rely on (e.g. `o3`, `gpt5`, `gemini-2.5-pro`).
   - Commit: `refactor(tools): simplify listmodels output`.
7. **Smoke test** — start MCP server, run `chat`, `debug`, `codereview` tools through Claude Desktop with each path:
   - Gemini CLI installed only
   - Codex CLI installed only
   - Neither CLI, only `OPENROUTER_API_KEY`
   - Verify error messaging when no provider available.

---

## 5. Test Impact Estimate

| Category | Before | After | Delta |
|---|---|---|---|
| Provider tests | ~12 files | ~5 files | −7 |
| Test LOC (providers) | ~3,500 | ~1,700 | −1,800 |
| Provider source LOC | 4,458 | ~2,800 | −1,650 |
| Conf files | 7 | 1 | −6 |
| Env vars in `.env.example` | ~25 | ~5 | −20 |

Expected `pytest` runtime drop: ~30–40% (no more cassette replays for direct APIs).

---

## 6. Risks & Mitigations

| Risk | Mitigation |
|---|---|
| OpenRouter outage = total outage | Document the failure mode. CLI fallback partially mitigates. Optionally: keep a tiny direct-Anthropic provider as last resort (out of current scope). |
| OpenRouter strips features (caching, tool use) | Accepted trade-off. Surface limitation in README. |
| Existing users with `GEMINI_API_KEY` etc. in `.env` | Boot-time warning if recognized but unused vars are present. Don't error. |
| Model alias drift — users invoke `o3` expecting direct OpenAI | OpenRouter catalogue covers most aliases; verify in Phase 4. |
| Tests in CI that hit real APIs | Audit `run_integration_tests.sh` — strip vendor-specific suites. |
| `ProviderType.GOOGLE` / `OPENAI` semantically misleading | Live with it; rename later if confusion arises. |

---

## 7. Out of Scope (explicitly)

- Rust port — rejected (vanity for this workload).
- Greenfield rewrite — not needed; in-place deletion is sufficient.
- Renaming `ProviderType` enum values — defer.
- Adding direct Anthropic provider for caching — separate decision.
- Adding new tools or capabilities — refactor only.

---

## 8. Open Questions for Approval

1. **`ProviderType` enum renaming** — leave as `GOOGLE`/`OPENAI` (cheap) or rename to `GEMINI_CLI`/`CODEX_CLI` (cleaner, more churn)?
2. **Default fallback model string** in `get_preferred_fallback_model()` — currently hardcoded `gemini-2.5-flash`. Replace with what OpenRouter alias?
3. **Recognized-but-unused env vars** — silently ignore, warn, or error?
4. **Integration test suite** — keep VCR cassettes for OpenRouter only, drop the rest?
5. **Phase ordering** — is this acceptable, or do you want a single "big bang" commit?

---

## 9. Estimated Effort

- Phase 1 (delete + rewire registry): **2–3 hours**
- Phase 2 (test pruning): **1–2 hours**
- Phase 3 (env + docs): **1 hour**
- Phase 4 (listmodels + smoke test): **1–2 hours**

**Total: ~1 working day** with conservative scope discipline.
