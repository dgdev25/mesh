"""Real subprocess integration tests for the CLI providers.

These tests actually shell out to the installed `gemini` / `codex` binaries.
They are gated behind the ``MESH_RUN_CLI_TESTS`` env var because:

  - They require the real CLIs to be installed on PATH.
  - They make real LLM calls (cost real tokens).
  - They take 5–30 seconds each.

Run with:

    MESH_RUN_CLI_TESTS=1 pytest tests/test_cli_integration.py -v
"""

import asyncio
import os
import shutil

import pytest

pytestmark = pytest.mark.skipif(
    os.environ.get("MESH_RUN_CLI_TESTS") != "1",
    reason="set MESH_RUN_CLI_TESTS=1 to run real-CLI integration tests",
)


@pytest.mark.skipif(shutil.which("gemini") is None, reason="gemini CLI not on PATH")
def test_gemini_cli_real_invocation():
    """Verify GeminiCliProvider works against the real `gemini` binary."""
    from providers.gemini_cli import GeminiCliProvider

    provider = GeminiCliProvider(cli_path="gemini", timeout_s=60)
    response = asyncio.run(
        provider.generate_content(
            prompt="Reply with exactly the single word: PONG",
            model_name="gemini-2.5-flash",
        )
    )
    assert "PONG" in response.content.upper()
    assert response.provider.value == "gemini_cli"
    assert response.usage["total_tokens"] > 0


@pytest.mark.skipif(shutil.which("codex") is None, reason="codex CLI not on PATH")
def test_codex_cli_real_invocation():
    """Verify CodexCliProvider works against the real `codex` binary."""
    from providers.codex_cli import CodexCliProvider

    provider = CodexCliProvider(cli_path="codex", timeout_s=120)
    response = asyncio.run(
        provider.generate_content(
            prompt="Reply with exactly the single word: PONG",
            model_name="gpt-5.3-codex",
        )
    )
    assert "PONG" in response.content.upper()
    assert response.provider.value == "codex_cli"
    assert response.usage["total_tokens"] > 0
