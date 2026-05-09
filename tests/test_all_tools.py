"""Integration tests verifying all Mesh tool patterns work with CLI providers.

Coverage:
1. Provider integration (GeminiCliProvider, CodexCliProvider) – response format,
   temperature variants, max_tokens variants, system prompts.
2. Fallback chain – Gemini-not-found → Codex, Codex-timeout → OpenRouter,
   both CLIs missing → OpenRouter, no providers → RuntimeError.
3. Edge cases – empty prompt, huge prompt, unicode/emoji, code blocks,
   concurrent requests, malformed JSON from CLI, empty CLI output.
4. Response format consistency – required fields, usage stats, no stderr leakage.
5. Configuration loading – env-var overrides, defaults, timeout, API keys.
"""

from __future__ import annotations

import asyncio
import json
import os
from typing import Any
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from providers.cli_base import CliProvider
from providers.codex_cli import CodexCliProvider
from providers.gemini_cli import GeminiCliProvider
from providers.registry import ModelProviderRegistry
from providers.shared import ModelResponse, ProviderType
from providers.shared.cli_output import (
    CliError,
    CliNotFoundError,
    CliOutput,
    CliTimeoutError,
)
from utils.env import validate_cli_environment, validate_provider_environment


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_gemini_json(
    content: str = "Hello from Gemini",
    input_tokens: int = 10,
    output_tokens: int = 20,
    model: str = "gemini-2-flash",
) -> str:
    return json.dumps({
        "content": content,
        "usage": {
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": input_tokens + output_tokens,
        },
        "model": model,
        "finish_reason": "STOP",
        "is_blocked_by_safety": False,
    })


def _make_codex_json(
    content: str = "Hello from Codex",
    prompt_tokens: int = 10,
    completion_tokens: int = 20,
    model: str = "gpt-4",
) -> str:
    return json.dumps({
        "content": content,
        "usage": {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens,
        },
        "model": model,
        "finish_reason": "stop",
    })


def _cli_output(stdout: str, exit_code: int = 0, stderr: str = "") -> CliOutput:
    return CliOutput(
        stdout=stdout,
        stderr=stderr,
        exit_code=exit_code,
        command="test",
        duration_ms=50.0,
    )


def _mock_success_response(content: str = "ok") -> MagicMock:
    resp = MagicMock(spec=ModelResponse)
    resp.content = content
    resp.success = True
    resp.usage = {"input_tokens": 5, "output_tokens": 10, "total_tokens": 15}
    resp.model_name = "test-model"
    resp.friendly_name = "Test Provider"
    resp.provider = ProviderType.GOOGLE
    resp.metadata = {}
    return resp


# ===========================================================================
# Section 1: Provider Integration Tests
# ===========================================================================


class TestGeminiCliProviderIntegration:
    """Integration tests for GeminiCliProvider response path."""

    def test_parse_response_small_prompt_returns_model_response(self):
        """should return ModelResponse when CLI output is a minimal JSON payload."""
        provider = GeminiCliProvider(cli_path="gemini")
        output = _cli_output(_make_gemini_json(content="Short answer"))
        response = provider._parse_response(output)
        assert isinstance(response, ModelResponse)

    def test_parse_response_content_populated_correctly(self):
        """should populate response.content from JSON 'content' field."""
        provider = GeminiCliProvider(cli_path="gemini")
        output = _cli_output(_make_gemini_json(content="Medium sized answer " * 20))
        response = provider._parse_response(output)
        assert "Medium sized answer" in response.content

    def test_parse_response_large_content_field(self):
        """should handle content larger than 10 KB without truncation."""
        large_text = "x" * 15_000
        provider = GeminiCliProvider(cli_path="gemini")
        output = _cli_output(_make_gemini_json(content=large_text))
        response = provider._parse_response(output)
        assert len(response.content) == 15_000

    def test_parse_response_provider_type_is_google(self):
        """should tag response with ProviderType.GOOGLE."""
        provider = GeminiCliProvider(cli_path="gemini")
        output = _cli_output(_make_gemini_json())
        response = provider._parse_response(output)
        assert response.provider == ProviderType.GOOGLE

    def test_parse_response_friendly_name_is_gemini_cli(self):
        """should set friendly_name to 'Gemini (CLI)'."""
        provider = GeminiCliProvider(cli_path="gemini")
        output = _cli_output(_make_gemini_json())
        response = provider._parse_response(output)
        assert response.friendly_name == "Gemini (CLI)"

    def test_parse_response_usage_stats_populated(self):
        """should populate usage dict with input_tokens and output_tokens."""
        provider = GeminiCliProvider(cli_path="gemini")
        output = _cli_output(_make_gemini_json(input_tokens=100, output_tokens=200))
        response = provider._parse_response(output)
        assert response.usage["input_tokens"] == 100
        assert response.usage["output_tokens"] == 200
        assert response.usage["total_tokens"] == 300

    def test_parse_response_model_name_preserved(self):
        """should preserve the model name reported by the CLI."""
        provider = GeminiCliProvider(cli_path="gemini")
        output = _cli_output(_make_gemini_json(model="gemini-3-pro"))
        response = provider._parse_response(output)
        assert response.model_name == "gemini-3-pro"

    def test_build_args_temperature_zero(self):
        """should pass temperature=0.0 as string to CLI args."""
        provider = GeminiCliProvider(cli_path="gemini")
        args = provider._build_args(prompt="test", model="gemini-2-flash", temperature=0.0)
        assert "--temperature" in args
        idx = args.index("--temperature")
        assert args[idx + 1] == "0.0"

    def test_build_args_temperature_half(self):
        """should pass temperature=0.5 as string to CLI args."""
        provider = GeminiCliProvider(cli_path="gemini")
        args = provider._build_args(prompt="test", model="gemini-2-flash", temperature=0.5)
        assert "0.5" in args

    def test_build_args_temperature_one(self):
        """should pass temperature=1.0 as string to CLI args."""
        provider = GeminiCliProvider(cli_path="gemini")
        args = provider._build_args(prompt="test", model="gemini-2-flash", temperature=1.0)
        assert "1.0" in args

    def test_build_args_max_tokens_100(self):
        """should emit --max-output-tokens when max_output_tokens=100."""
        provider = GeminiCliProvider(cli_path="gemini")
        args = provider._build_args(
            prompt="test", model="gemini-2-flash", temperature=0.7, max_output_tokens=100
        )
        assert "--max-output-tokens" in args
        assert "100" in args

    def test_build_args_max_tokens_4096(self):
        """should emit --max-output-tokens 4096 correctly."""
        provider = GeminiCliProvider(cli_path="gemini")
        args = provider._build_args(
            prompt="test", model="gemini-2-flash", temperature=0.7, max_output_tokens=4096
        )
        idx = args.index("--max-output-tokens")
        assert args[idx + 1] == "4096"

    def test_build_args_omits_max_tokens_when_none(self):
        """should not include --max-output-tokens when not provided."""
        provider = GeminiCliProvider(cli_path="gemini")
        args = provider._build_args(prompt="test", model="gemini-2-flash", temperature=0.7)
        assert "--max-output-tokens" not in args

    def test_stderr_never_appears_in_response_content(self):
        """should never include CLI stderr in response.content."""
        provider = GeminiCliProvider(cli_path="gemini")
        output = CliOutput(
            stdout=_make_gemini_json(content="Real answer"),
            stderr="WARNING: Some debug message",
            exit_code=0,
            command="gemini generate",
            duration_ms=100.0,
        )
        response = provider._parse_response(output)
        assert "WARNING" not in response.content
        assert "debug message" not in response.content


class TestCodexCliProviderIntegration:
    """Integration tests for CodexCliProvider response path."""

    def test_parse_response_small_prompt_returns_model_response(self):
        """should return ModelResponse from a minimal valid JSON payload."""
        provider = CodexCliProvider(cli_path="codex")
        output = _cli_output(_make_codex_json(content="Short answer"))
        response = provider._parse_response(output)
        assert isinstance(response, ModelResponse)

    def test_parse_response_content_populated_correctly(self):
        """should populate response.content from JSON 'content' field."""
        provider = CodexCliProvider(cli_path="codex")
        output = _cli_output(_make_codex_json(content="Medium sized answer " * 20))
        response = provider._parse_response(output)
        assert "Medium sized answer" in response.content

    def test_parse_response_large_content_field(self):
        """should handle content larger than 10 KB without truncation."""
        large_text = "y" * 15_000
        provider = CodexCliProvider(cli_path="codex")
        output = _cli_output(_make_codex_json(content=large_text))
        response = provider._parse_response(output)
        assert len(response.content) == 15_000

    def test_parse_response_provider_type_is_openai(self):
        """should tag response with ProviderType.OPENAI."""
        provider = CodexCliProvider(cli_path="codex")
        output = _cli_output(_make_codex_json())
        response = provider._parse_response(output)
        assert response.provider == ProviderType.OPENAI

    def test_parse_response_friendly_name_is_openai_cli(self):
        """should set friendly_name to 'OpenAI (CLI)'."""
        provider = CodexCliProvider(cli_path="codex")
        output = _cli_output(_make_codex_json())
        response = provider._parse_response(output)
        assert response.friendly_name == "OpenAI (CLI)"

    def test_parse_response_openai_token_names_mapped_to_standard(self):
        """should map prompt_tokens → input_tokens and completion_tokens → output_tokens."""
        provider = CodexCliProvider(cli_path="codex")
        output = _cli_output(_make_codex_json(prompt_tokens=77, completion_tokens=33))
        response = provider._parse_response(output)
        assert response.usage["input_tokens"] == 77
        assert response.usage["output_tokens"] == 33
        assert response.usage["total_tokens"] == 110

    def test_build_args_temperature_zero(self):
        """should pass temperature=0.0 to CLI args."""
        provider = CodexCliProvider(cli_path="codex")
        args = provider._build_args(prompt="test", model="gpt-4", temperature=0.0)
        assert "0.0" in args

    def test_build_args_temperature_one(self):
        """should pass temperature=1.0 to CLI args."""
        provider = CodexCliProvider(cli_path="codex")
        args = provider._build_args(prompt="test", model="gpt-4", temperature=1.0)
        assert "1.0" in args

    def test_build_args_max_tokens_1000(self):
        """should emit --max-tokens 1000."""
        provider = CodexCliProvider(cli_path="codex")
        args = provider._build_args(
            prompt="test", model="gpt-4", temperature=0.7, max_output_tokens=1000
        )
        assert "--max-tokens" in args
        assert "1000" in args

    def test_stderr_never_appears_in_response_content(self):
        """should never include CLI stderr in response.content."""
        provider = CodexCliProvider(cli_path="codex")
        output = CliOutput(
            stdout=_make_codex_json(content="Real answer"),
            stderr="stderr garbage",
            exit_code=0,
            command="codex chat-completion",
            duration_ms=100.0,
        )
        response = provider._parse_response(output)
        assert "stderr garbage" not in response.content


# ===========================================================================
# Section 2: Fallback Chain Tests
# ===========================================================================


class TestFallbackChain:
    """Tests for invoke_with_fallback() in ModelProviderRegistry."""

    @pytest.mark.asyncio
    async def test_gemini_not_found_falls_back_to_codex(self):
        """should try Codex after Gemini CLI is not found."""
        registry = ModelProviderRegistry()
        success_response = _mock_success_response("from codex")

        mock_gemini = Mock()
        mock_gemini.generate_content = AsyncMock(
            side_effect=CliNotFoundError("gemini binary not found")
        )
        mock_codex = Mock()
        mock_codex.generate_content = AsyncMock(return_value=success_response)

        with patch("providers.registry.which") as mock_which, \
             patch("providers.registry.get_env") as mock_get_env, \
             patch.object(ModelProviderRegistry, "get_provider") as mock_get_provider:
            # gemini found, codex found
            mock_which.side_effect = lambda name: f"/usr/bin/{name}" if name in ("gemini", "codex") else None
            mock_get_env.return_value = None  # no OpenRouter
            mock_get_provider.side_effect = [mock_gemini, mock_codex]

            request = {"prompt": "hello", "model_name": "gpt-4", "temperature": 1.0}
            response = await registry.invoke_with_fallback(request)

        assert response is success_response
        assert mock_gemini.generate_content.call_count == 1
        assert mock_codex.generate_content.call_count == 1

    @pytest.mark.asyncio
    async def test_codex_not_found_falls_back_to_openrouter(self):
        """should try OpenRouter after Codex CLI is not found."""
        registry = ModelProviderRegistry()
        success_response = _mock_success_response("from openrouter")

        mock_codex = Mock()
        mock_codex.generate_content = AsyncMock(
            side_effect=CliNotFoundError("codex not found")
        )
        mock_openrouter = Mock()
        mock_openrouter.generate_content = AsyncMock(return_value=success_response)

        with patch("providers.registry.which") as mock_which, \
             patch("providers.registry.get_env") as mock_get_env, \
             patch.object(ModelProviderRegistry, "get_provider") as mock_get_provider:
            # only codex detected (gemini not found)
            mock_which.side_effect = lambda name: "/usr/bin/codex" if name == "codex" else None
            mock_get_env.return_value = "sk-or-test-key"  # OpenRouter enabled
            mock_get_provider.side_effect = [mock_codex, mock_openrouter]

            request = {"prompt": "hello", "model_name": "test-model", "temperature": 1.0}
            response = await registry.invoke_with_fallback(request)

        assert response is success_response
        assert mock_openrouter.generate_content.call_count == 1

    @pytest.mark.asyncio
    async def test_both_clis_timeout_falls_back_to_openrouter(self):
        """should try OpenRouter after both CLIs time out."""
        registry = ModelProviderRegistry()
        success_response = _mock_success_response("from openrouter after timeouts")

        mock_gemini = Mock()
        mock_gemini.generate_content = AsyncMock(
            side_effect=CliTimeoutError("gemini timeout")
        )
        mock_codex = Mock()
        mock_codex.generate_content = AsyncMock(
            side_effect=CliTimeoutError("codex timeout")
        )
        mock_openrouter = Mock()
        mock_openrouter.generate_content = AsyncMock(return_value=success_response)

        with patch("providers.registry.which") as mock_which, \
             patch("providers.registry.get_env") as mock_get_env, \
             patch.object(ModelProviderRegistry, "get_provider") as mock_get_provider:
            mock_which.side_effect = lambda name: f"/usr/bin/{name}" if name in ("gemini", "codex") else None
            mock_get_env.return_value = "sk-or-key"
            mock_get_provider.side_effect = [mock_gemini, mock_codex, mock_openrouter]

            request = {"prompt": "hello", "model_name": "test-model", "temperature": 1.0}
            response = await registry.invoke_with_fallback(request)

        assert response is success_response
        assert mock_gemini.generate_content.call_count == 1
        assert mock_codex.generate_content.call_count == 1
        assert mock_openrouter.generate_content.call_count == 1

    @pytest.mark.asyncio
    async def test_all_providers_fail_raises_runtime_error(self):
        """should raise RuntimeError with 'All providers exhausted' when every provider fails."""
        registry = ModelProviderRegistry()

        mock_gemini = Mock()
        mock_gemini.generate_content = AsyncMock(
            side_effect=CliNotFoundError("gemini not found")
        )
        mock_codex = Mock()
        mock_codex.generate_content = AsyncMock(
            side_effect=CliTimeoutError("codex timeout")
        )

        with patch("providers.registry.which") as mock_which, \
             patch("providers.registry.get_env") as mock_get_env, \
             patch.object(ModelProviderRegistry, "get_provider") as mock_get_provider:
            mock_which.side_effect = lambda name: f"/usr/bin/{name}" if name in ("gemini", "codex") else None
            mock_get_env.return_value = None
            mock_get_provider.side_effect = [mock_gemini, mock_codex]

            request = {"prompt": "hello", "model_name": "test-model", "temperature": 1.0}
            with pytest.raises(RuntimeError, match="All providers exhausted"):
                await registry.invoke_with_fallback(request)

    @pytest.mark.asyncio
    async def test_no_providers_available_raises_runtime_error(self):
        """should raise RuntimeError immediately when no CLIs found and no OpenRouter key."""
        registry = ModelProviderRegistry()

        with patch("providers.registry.which") as mock_which, \
             patch("providers.registry.get_env") as mock_get_env:
            mock_which.return_value = None  # no CLIs
            mock_get_env.return_value = None  # no OpenRouter

            request = {"prompt": "hello", "model_name": "test-model", "temperature": 1.0}
            with pytest.raises(RuntimeError, match="No providers available"):
                await registry.invoke_with_fallback(request)

    @pytest.mark.asyncio
    async def test_no_openrouter_key_not_added_to_chain(self):
        """should not include OpenRouter in chain when OPENROUTER_API_KEY is absent."""
        registry = ModelProviderRegistry()
        success_response = _mock_success_response("from gemini")

        mock_gemini = Mock()
        mock_gemini.generate_content = AsyncMock(return_value=success_response)

        with patch("providers.registry.which") as mock_which, \
             patch("providers.registry.get_env") as mock_get_env, \
             patch.object(ModelProviderRegistry, "get_provider") as mock_get_provider:
            mock_which.return_value = "/usr/bin/gemini"
            mock_get_env.return_value = None  # no OpenRouter key
            mock_get_provider.return_value = mock_gemini

            request = {"prompt": "hello", "model_name": "test-model", "temperature": 1.0}
            response = await registry.invoke_with_fallback(request)

        assert response is success_response
        # OpenRouter mock should never be called
        assert mock_gemini.generate_content.call_count == 1

    @pytest.mark.asyncio
    async def test_gemini_is_tried_before_codex(self):
        """should always attempt Gemini before Codex in the chain."""
        call_order: list[str] = []

        async def gemini_side_effect(*args, **kwargs):
            call_order.append("gemini")
            raise CliNotFoundError("not found")

        async def codex_side_effect(*args, **kwargs):
            call_order.append("codex")
            return _mock_success_response("from codex")

        registry = ModelProviderRegistry()
        mock_gemini = Mock()
        mock_gemini.generate_content = AsyncMock(side_effect=gemini_side_effect)
        mock_codex = Mock()
        mock_codex.generate_content = AsyncMock(side_effect=codex_side_effect)

        with patch("providers.registry.which") as mock_which, \
             patch("providers.registry.get_env") as mock_get_env, \
             patch.object(ModelProviderRegistry, "get_provider") as mock_get_provider:
            mock_which.side_effect = lambda name: f"/usr/bin/{name}" if name in ("gemini", "codex") else None
            mock_get_env.return_value = None
            mock_get_provider.side_effect = [mock_gemini, mock_codex]

            request = {"prompt": "hello", "model_name": "test-model", "temperature": 1.0}
            await registry.invoke_with_fallback(request)

        assert call_order == ["gemini", "codex"]

    @pytest.mark.asyncio
    async def test_fallback_logs_failed_provider(self, caplog):
        """should log a warning when a provider fails and fallback is triggered."""
        import logging
        caplog.set_level(logging.WARNING)
        registry = ModelProviderRegistry()
        success_response = _mock_success_response()

        mock_gemini = Mock()
        mock_gemini.generate_content = AsyncMock(
            side_effect=CliNotFoundError("gemini not found")
        )
        mock_codex = Mock()
        mock_codex.generate_content = AsyncMock(return_value=success_response)

        with patch("providers.registry.which") as mock_which, \
             patch("providers.registry.get_env") as mock_get_env, \
             patch.object(ModelProviderRegistry, "get_provider") as mock_get_provider:
            mock_which.side_effect = lambda name: f"/usr/bin/{name}" if name in ("gemini", "codex") else None
            mock_get_env.return_value = None
            mock_get_provider.side_effect = [mock_gemini, mock_codex]

            request = {"prompt": "hello", "model_name": "test-model", "temperature": 1.0}
            await registry.invoke_with_fallback(request)

        warning_messages = [r.message for r in caplog.records if r.levelname == "WARNING"]
        assert any("failed" in m.lower() or "gemini" in m.lower() for m in warning_messages)

    @pytest.mark.asyncio
    async def test_fallback_logs_success(self, caplog):
        """should log INFO when a provider succeeds."""
        import logging
        caplog.set_level(logging.INFO)
        registry = ModelProviderRegistry()
        success_response = _mock_success_response()

        mock_gemini = Mock()
        mock_gemini.generate_content = AsyncMock(return_value=success_response)

        with patch("providers.registry.which") as mock_which, \
             patch("providers.registry.get_env") as mock_get_env, \
             patch.object(ModelProviderRegistry, "get_provider") as mock_get_provider:
            mock_which.return_value = "/usr/bin/gemini"
            mock_get_env.return_value = None
            mock_get_provider.return_value = mock_gemini

            request = {"prompt": "hello", "model_name": "test-model", "temperature": 1.0}
            await registry.invoke_with_fallback(request)

        info_messages = [r.message for r in caplog.records if r.levelname == "INFO"]
        assert any("successfully" in m.lower() for m in info_messages)

    @pytest.mark.asyncio
    async def test_none_provider_is_skipped_in_chain(self):
        """should skip a None provider and continue to the next valid one."""
        registry = ModelProviderRegistry()
        success_response = _mock_success_response("from second")

        mock_openrouter = Mock()
        mock_openrouter.generate_content = AsyncMock(return_value=success_response)

        with patch("providers.registry.which") as mock_which, \
             patch("providers.registry.get_env") as mock_get_env, \
             patch.object(ModelProviderRegistry, "get_provider") as mock_get_provider:
            # gemini detected but provider returns None, codex skipped too
            mock_which.side_effect = lambda name: "/usr/bin/gemini" if name == "gemini" else None
            mock_get_env.return_value = "key"  # OpenRouter enabled
            # gemini provider returns None (uninitialized), openrouter succeeds
            mock_get_provider.side_effect = [None, mock_openrouter]

            request = {"prompt": "hello", "model_name": "test-model", "temperature": 1.0}
            response = await registry.invoke_with_fallback(request)

        assert response is success_response

    @pytest.mark.asyncio
    async def test_fallback_chain_all_attempts_logged(self, caplog):
        """should record a log entry for each failed provider attempt."""
        import logging
        caplog.set_level(logging.WARNING)
        registry = ModelProviderRegistry()

        mock_gemini = Mock()
        mock_gemini.generate_content = AsyncMock(
            side_effect=CliNotFoundError("gemini not found")
        )
        mock_codex = Mock()
        mock_codex.generate_content = AsyncMock(
            side_effect=CliTimeoutError("codex timeout")
        )

        with patch("providers.registry.which") as mock_which, \
             patch("providers.registry.get_env") as mock_get_env, \
             patch.object(ModelProviderRegistry, "get_provider") as mock_get_provider:
            mock_which.side_effect = lambda name: f"/usr/bin/{name}" if name in ("gemini", "codex") else None
            mock_get_env.return_value = None
            mock_get_provider.side_effect = [mock_gemini, mock_codex]

            request = {"prompt": "hello", "model_name": "test-model", "temperature": 1.0}
            with pytest.raises(RuntimeError):
                await registry.invoke_with_fallback(request)

        warning_messages = [r.message for r in caplog.records if r.levelname == "WARNING"]
        # At least two warning entries, one per failed provider
        assert len(warning_messages) >= 2

    @pytest.mark.asyncio
    async def test_fallback_returns_same_model_response_type(self):
        """should return a ModelResponse-compatible object regardless of which provider succeeds."""
        registry = ModelProviderRegistry()
        success_response = _mock_success_response("final")

        mock_gemini = Mock()
        mock_gemini.generate_content = AsyncMock(
            side_effect=CliNotFoundError("not found")
        )
        mock_codex = Mock()
        mock_codex.generate_content = AsyncMock(return_value=success_response)

        with patch("providers.registry.which") as mock_which, \
             patch("providers.registry.get_env") as mock_get_env, \
             patch.object(ModelProviderRegistry, "get_provider") as mock_get_provider:
            mock_which.side_effect = lambda name: f"/usr/bin/{name}" if name in ("gemini", "codex") else None
            mock_get_env.return_value = None
            mock_get_provider.side_effect = [mock_gemini, mock_codex]

            request = {"prompt": "hello", "model_name": "test-model", "temperature": 1.0}
            response = await registry.invoke_with_fallback(request)

        # Must expose .content and .success
        assert hasattr(response, "content")
        assert hasattr(response, "success")

    @pytest.mark.asyncio
    async def test_failed_response_triggers_next_provider(self):
        """should continue to next provider when provider returns response with success=False."""
        registry = ModelProviderRegistry()
        failed_response = MagicMock(spec=ModelResponse)
        failed_response.success = False
        failed_response.content = ""

        success_response = _mock_success_response("second succeeded")

        mock_gemini = Mock()
        mock_gemini.generate_content = AsyncMock(return_value=failed_response)
        mock_codex = Mock()
        mock_codex.generate_content = AsyncMock(return_value=success_response)

        with patch("providers.registry.which") as mock_which, \
             patch("providers.registry.get_env") as mock_get_env, \
             patch.object(ModelProviderRegistry, "get_provider") as mock_get_provider:
            mock_which.side_effect = lambda name: f"/usr/bin/{name}" if name in ("gemini", "codex") else None
            mock_get_env.return_value = None
            mock_get_provider.side_effect = [mock_gemini, mock_codex]

            request = {"prompt": "hello", "model_name": "test-model", "temperature": 1.0}
            response = await registry.invoke_with_fallback(request)

        assert response is success_response
        assert mock_codex.generate_content.call_count == 1


# ===========================================================================
# Section 3: Edge Case Tests
# ===========================================================================


class TestEdgeCases:
    """Edge cases for CLI output parsing and provider robustness."""

    def test_empty_prompt_still_builds_valid_gemini_args(self):
        """should not crash when building Gemini args with an empty prompt."""
        provider = GeminiCliProvider(cli_path="gemini")
        args = provider._build_args(prompt="", model="gemini-2-flash", temperature=0.7)
        # The prompt arg is still included (even if empty)
        assert "--prompt" in args

    def test_empty_prompt_still_builds_valid_codex_args(self):
        """should not crash when building Codex args with an empty prompt."""
        provider = CodexCliProvider(cli_path="codex")
        args = provider._build_args(prompt="", model="gpt-4", temperature=0.7)
        assert "--message" in args

    def test_very_long_prompt_preserved_in_gemini_args(self):
        """should preserve a 12KB prompt string in Gemini CLI args."""
        large_prompt = "A" * 12_000
        provider = GeminiCliProvider(cli_path="gemini")
        args = provider._build_args(
            prompt=large_prompt, model="gemini-2-flash", temperature=0.7
        )
        combined = " ".join(args)
        assert large_prompt in combined

    def test_very_long_prompt_preserved_in_codex_args(self):
        """should preserve a 12KB prompt string in Codex CLI args."""
        large_prompt = "B" * 12_000
        provider = CodexCliProvider(cli_path="codex")
        args = provider._build_args(prompt=large_prompt, model="gpt-4", temperature=0.7)
        combined = " ".join(args)
        assert large_prompt in combined

    def test_unicode_in_gemini_response_content(self):
        """should handle unicode characters in Gemini CLI response content."""
        unicode_content = "日本語テキスト 🎉 Arabic: مرحبا"
        provider = GeminiCliProvider(cli_path="gemini")
        output = _cli_output(_make_gemini_json(content=unicode_content))
        response = provider._parse_response(output)
        assert response.content == unicode_content

    def test_emoji_in_codex_response_content(self):
        """should handle emoji in Codex CLI response content."""
        emoji_content = "Result: ✅🚀💡🔥"
        provider = CodexCliProvider(cli_path="codex")
        output = _cli_output(_make_codex_json(content=emoji_content))
        response = provider._parse_response(output)
        assert response.content == emoji_content

    def test_newlines_in_gemini_prompt_args(self):
        """should preserve newline characters in Gemini prompt arg."""
        multiline_prompt = "Line 1\nLine 2\nLine 3"
        provider = GeminiCliProvider(cli_path="gemini")
        args = provider._build_args(
            prompt=multiline_prompt, model="gemini-2-flash", temperature=0.7
        )
        combined = " ".join(args)
        assert "Line 1" in combined and "Line 3" in combined

    def test_code_blocks_with_backticks_in_gemini_response(self):
        """should handle backtick code blocks in Gemini response content."""
        code_content = "Here is code:\n```python\ndef hello():\n    return 'world'\n```"
        provider = GeminiCliProvider(cli_path="gemini")
        output = _cli_output(_make_gemini_json(content=code_content))
        response = provider._parse_response(output)
        assert "```python" in response.content

    def test_malformed_json_from_cli_raises_cli_error(self):
        """should raise CliError when CLI output is not valid JSON."""
        provider = GeminiCliProvider(cli_path="gemini")
        output = _cli_output('{"content": "oops", bad json here')
        with pytest.raises(CliError):
            provider._parse_response(output)

    def test_empty_cli_output_raises_cli_error(self):
        """should raise CliError when CLI produces empty stdout and stderr."""
        provider = GeminiCliProvider(cli_path="gemini")
        output = _cli_output("")
        with pytest.raises(CliError):
            provider._parse_response(output)

    def test_non_json_text_from_cli_raises_cli_error(self):
        """should raise CliError when CLI output is plain text (not JSON)."""
        provider = GeminiCliProvider(cli_path="gemini")
        output = _cli_output("Error: quota exceeded")
        with pytest.raises(CliError):
            provider._parse_response(output)

    def test_non_json_text_from_codex_cli_raises_cli_error(self):
        """should raise CliError when Codex CLI output is plain text."""
        provider = CodexCliProvider(cli_path="codex")
        output = _cli_output("rate limit exceeded")
        with pytest.raises(CliError):
            provider._parse_response(output)

    def test_gemini_json_missing_content_field_raises_cli_error(self):
        """should raise CliError when JSON lacks 'content' field."""
        provider = GeminiCliProvider(cli_path="gemini")
        payload = json.dumps({"usage": {"input_tokens": 5}, "model": "gemini-2-flash"})
        output = _cli_output(payload)
        with pytest.raises(CliError, match="missing 'content'"):
            provider._parse_response(output)

    def test_codex_json_missing_content_field_raises_cli_error(self):
        """should raise CliError when JSON lacks 'content' field."""
        provider = CodexCliProvider(cli_path="codex")
        payload = json.dumps({"usage": {"prompt_tokens": 5}, "model": "gpt-4"})
        output = _cli_output(payload)
        with pytest.raises(CliError, match="missing 'content'"):
            provider._parse_response(output)

    @pytest.mark.asyncio
    async def test_cli_timeout_raises_cli_timeout_error(self):
        """should raise CliTimeoutError when subprocess exceeds timeout."""
        provider = GeminiCliProvider(cli_path="sleep", timeout_s=1)
        with pytest.raises(CliTimeoutError):
            await provider._run_cli(["sleep", "100"])

    @pytest.mark.asyncio
    async def test_cli_binary_not_found_raises_cli_not_found_error(self):
        """should raise CliNotFoundError when the CLI binary is absent."""
        provider = GeminiCliProvider(cli_path="nonexistent_xyz_cli_42")
        with pytest.raises(CliNotFoundError):
            await provider._run_cli(["nonexistent_xyz_cli_42", "generate"])

    @pytest.mark.asyncio
    async def test_concurrent_parse_calls_are_deterministic(self):
        """should produce consistent results when _parse_response is called concurrently."""
        provider = GeminiCliProvider(cli_path="gemini")

        async def parse_one(idx: int) -> str:
            output = _cli_output(_make_gemini_json(content=f"response_{idx}"))
            return provider._parse_response(output).content

        results = await asyncio.gather(*[parse_one(i) for i in range(20)])
        for i, result in enumerate(results):
            assert result == f"response_{i}"

    @pytest.mark.asyncio
    async def test_concurrent_generate_content_uses_independent_runs(self):
        """should not share state when multiple generate_content calls run concurrently."""
        provider = GeminiCliProvider(cli_path="gemini")

        async def mocked_run(args):
            idx = args[args.index("--prompt") + 1]
            return _cli_output(_make_gemini_json(content=f"answer_{idx}"))

        with patch.object(provider, "_run_cli", side_effect=mocked_run), \
             patch.object(provider, "validate_parameters"), \
             patch.object(provider, "_resolve_model_name", return_value="gemini-2-flash"):
            tasks = [
                provider.generate_content(
                    prompt=str(i),
                    model_name="gemini-2.5-flash",
                    temperature=0.7,
                )
                for i in range(10)
            ]
            results = await asyncio.gather(*tasks)

        for i, resp in enumerate(results):
            assert resp.content == f"answer_{i}"

    def test_whitespace_only_cli_output_raises_cli_error(self):
        """should raise CliError for output that is only whitespace."""
        provider = GeminiCliProvider(cli_path="gemini")
        output = _cli_output("   \n\n   \t  ")
        with pytest.raises(CliError):
            provider._parse_response(output)


# ===========================================================================
# Section 4: Response Format Consistency Tests
# ===========================================================================


class TestResponseFormatConsistency:
    """Verify that all providers produce structurally identical ModelResponse objects."""

    def test_gemini_response_has_content_field(self):
        """should expose a non-empty .content string."""
        provider = GeminiCliProvider(cli_path="gemini")
        response = provider._parse_response(_cli_output(_make_gemini_json()))
        assert isinstance(response.content, str)
        assert len(response.content) > 0

    def test_codex_response_has_content_field(self):
        """should expose a non-empty .content string."""
        provider = CodexCliProvider(cli_path="codex")
        response = provider._parse_response(_cli_output(_make_codex_json()))
        assert isinstance(response.content, str)
        assert len(response.content) > 0

    def test_gemini_response_has_usage_dict(self):
        """should expose a dict with at least input_tokens, output_tokens, total_tokens."""
        provider = GeminiCliProvider(cli_path="gemini")
        response = provider._parse_response(_cli_output(_make_gemini_json()))
        for key in ("input_tokens", "output_tokens", "total_tokens"):
            assert key in response.usage

    def test_codex_response_has_usage_dict(self):
        """should expose a dict with input_tokens, output_tokens, total_tokens."""
        provider = CodexCliProvider(cli_path="codex")
        response = provider._parse_response(_cli_output(_make_codex_json()))
        for key in ("input_tokens", "output_tokens", "total_tokens"):
            assert key in response.usage

    def test_gemini_response_usage_values_are_ints(self):
        """should store usage token counts as integers."""
        provider = GeminiCliProvider(cli_path="gemini")
        response = provider._parse_response(_cli_output(_make_gemini_json()))
        for key in ("input_tokens", "output_tokens", "total_tokens"):
            assert isinstance(response.usage[key], int)

    def test_codex_response_usage_values_are_ints(self):
        """should store usage token counts as integers."""
        provider = CodexCliProvider(cli_path="codex")
        response = provider._parse_response(_cli_output(_make_codex_json()))
        for key in ("input_tokens", "output_tokens", "total_tokens"):
            assert isinstance(response.usage[key], int)

    def test_gemini_response_has_model_name_field(self):
        """should expose a non-empty .model_name string."""
        provider = GeminiCliProvider(cli_path="gemini")
        response = provider._parse_response(_cli_output(_make_gemini_json()))
        assert isinstance(response.model_name, str)
        assert len(response.model_name) > 0

    def test_codex_response_has_model_name_field(self):
        """should expose a non-empty .model_name string."""
        provider = CodexCliProvider(cli_path="codex")
        response = provider._parse_response(_cli_output(_make_codex_json()))
        assert isinstance(response.model_name, str)
        assert len(response.model_name) > 0

    def test_gemini_response_metadata_is_dict(self):
        """should expose .metadata as a dict."""
        provider = GeminiCliProvider(cli_path="gemini")
        response = provider._parse_response(_cli_output(_make_gemini_json()))
        assert isinstance(response.metadata, dict)

    def test_codex_response_metadata_is_dict(self):
        """should expose .metadata as a dict."""
        provider = CodexCliProvider(cli_path="codex")
        response = provider._parse_response(_cli_output(_make_codex_json()))
        assert isinstance(response.metadata, dict)

    def test_total_tokens_matches_sum_of_parts_gemini(self):
        """should have total_tokens == input_tokens + output_tokens for Gemini responses."""
        provider = GeminiCliProvider(cli_path="gemini")
        response = provider._parse_response(
            _cli_output(_make_gemini_json(input_tokens=40, output_tokens=60))
        )
        assert response.usage["total_tokens"] == 100

    def test_total_tokens_matches_sum_of_parts_codex(self):
        """should have total_tokens == input_tokens + output_tokens for Codex responses."""
        provider = CodexCliProvider(cli_path="codex")
        response = provider._parse_response(
            _cli_output(_make_codex_json(prompt_tokens=40, completion_tokens=60))
        )
        assert response.usage["total_tokens"] == 100

    def test_gemini_and_codex_response_fields_match_same_schema(self):
        """both providers should expose identical top-level field names on ModelResponse."""
        gemini_provider = GeminiCliProvider(cli_path="gemini")
        codex_provider = CodexCliProvider(cli_path="codex")

        g_resp = gemini_provider._parse_response(_cli_output(_make_gemini_json()))
        c_resp = codex_provider._parse_response(_cli_output(_make_codex_json()))

        gemini_fields = set(vars(g_resp).keys())
        codex_fields = set(vars(c_resp).keys())
        assert gemini_fields == codex_fields


# ===========================================================================
# Section 5: Configuration Loading Tests
# ===========================================================================


class TestConfigurationLoading:
    """Tests for config module and environment variable behaviour."""

    def test_cli_paths_config_has_gemini_key(self):
        """config.CLI_PATHS should contain a 'gemini' entry."""
        import config
        assert "gemini" in config.CLI_PATHS

    def test_cli_paths_config_has_codex_key(self):
        """config.CLI_PATHS should contain a 'codex' entry."""
        import config
        assert "codex" in config.CLI_PATHS

    def test_cli_paths_values_are_strings(self):
        """config.CLI_PATHS values should all be strings."""
        import config
        for key, value in config.CLI_PATHS.items():
            assert isinstance(value, str), f"CLI_PATHS['{key}'] is not a string"

    def test_cli_timeout_is_positive_integer(self):
        """config.CLI_TIMEOUT_SECONDS should be a positive integer."""
        import config
        assert isinstance(config.CLI_TIMEOUT_SECONDS, int)
        assert config.CLI_TIMEOUT_SECONDS > 0

    def test_openrouter_api_key_is_none_or_string(self):
        """config.OPENROUTER_API_KEY should be None or a string."""
        import config
        assert config.OPENROUTER_API_KEY is None or isinstance(config.OPENROUTER_API_KEY, str)

    def test_openrouter_enabled_is_bool(self):
        """config.OPENROUTER_ENABLED should be a bool."""
        import config
        assert isinstance(config.OPENROUTER_ENABLED, bool)

    def test_openrouter_enabled_true_when_key_set(self):
        """config.OPENROUTER_ENABLED should be True when OPENROUTER_API_KEY is non-empty."""
        import config
        if config.OPENROUTER_API_KEY:
            assert config.OPENROUTER_ENABLED is True

    def test_gemini_cli_path_can_be_overridden_via_env(self, monkeypatch):
        """validate_cli_environment should use GEMINI_CLI_PATH env var when set."""
        monkeypatch.setenv("GEMINI_CLI_PATH", "/custom/path/gemini")
        with patch("utils.env.shutil.which") as mock_which:
            mock_which.side_effect = lambda p: "/custom/path/gemini" if p == "/custom/path/gemini" else None
            from utils.env import validate_cli_environment
            results = validate_cli_environment()
        # gemini should be True because our custom path was "found"
        assert results["gemini"] is True

    def test_missing_cli_tools_detected(self, monkeypatch):
        """validate_cli_environment should report False for missing tools."""
        with patch("utils.env.shutil.which") as mock_which:
            mock_which.return_value = None
            results = validate_cli_environment()
        assert results["gemini"] is False
        assert results["codex"] is False

    def test_present_cli_tools_detected(self):
        """validate_cli_environment should report True for tools that exist in PATH."""
        with patch("utils.env.shutil.which") as mock_which:
            mock_which.return_value = "/usr/bin/tool"
            results = validate_cli_environment()
        assert results["gemini"] is True
        assert results["codex"] is True

    def test_validate_provider_environment_returns_dict(self):
        """validate_provider_environment should return a dict with known keys."""
        results = validate_provider_environment()
        assert isinstance(results, dict)
        assert "openrouter" in results
        assert "gemini" in results
        assert "codex" in results

    def test_validate_provider_environment_all_values_are_bool(self):
        """validate_provider_environment should return booleans for all values."""
        results = validate_provider_environment()
        for key, val in results.items():
            assert isinstance(val, bool), f"results['{key}'] is not bool"

    def test_codex_cli_path_can_be_overridden_via_env(self, monkeypatch):
        """validate_cli_environment should use CODEX_CLI_PATH env var when set."""
        monkeypatch.setenv("CODEX_CLI_PATH", "/opt/bin/codex")
        with patch("utils.env.shutil.which") as mock_which:
            mock_which.side_effect = lambda p: "/opt/bin/codex" if p == "/opt/bin/codex" else None
            from utils.env import validate_cli_environment
            results = validate_cli_environment()
        assert results["codex"] is True
