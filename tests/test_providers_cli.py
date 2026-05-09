"""Unit tests for CLI-based providers and CLI output parsing."""

import asyncio
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from providers.cli_base import CliProvider
from providers.codex_cli import CodexCliProvider
from providers.gemini_cli import GeminiCliProvider
from providers.shared import ProviderType
from providers.shared.cli_output import (
    CliError,
    CliNotFoundError,
    CliOutput,
    CliResponseParser,
    CliTimeoutError,
)


# ============================================================================
# Module 1: CLI Output Parser Tests
# ============================================================================


class TestCliOutput:
    """Tests for CliOutput dataclass."""

    def test_create_success_output(self):
        """Test creating a successful CLI output."""
        output = CliOutput(
            stdout="test output",
            stderr="",
            exit_code=0,
            command="test command",
            duration_ms=123.45,
        )

        assert output.success is True
        assert output.raw_output == "test output"
        assert output.exit_code == 0

    def test_create_error_output(self):
        """Test creating a failed CLI output."""
        output = CliOutput(
            stdout="",
            stderr="error message",
            exit_code=1,
            command="test command",
            duration_ms=50.0,
        )

        assert output.success is False
        assert output.raw_output == "error message"
        assert output.exit_code == 1

    def test_raw_output_prefers_stdout(self):
        """Test that raw_output returns stdout if available."""
        output = CliOutput(
            stdout="stdout content",
            stderr="stderr content",
            exit_code=0,
            command="test",
            duration_ms=10.0,
        )

        assert output.raw_output == "stdout content"

    def test_raw_output_fallback_to_stderr(self):
        """Test that raw_output falls back to stderr."""
        output = CliOutput(
            stdout="",
            stderr="only stderr",
            exit_code=1,
            command="test",
            duration_ms=10.0,
        )

        assert output.raw_output == "only stderr"

    def test_str_representation(self):
        """Test string representation of CliOutput."""
        output = CliOutput(
            stdout="output",
            stderr="",
            exit_code=0,
            command="test",
            duration_ms=100.0,
        )

        str_repr = str(output)
        assert "success" in str_repr
        assert "100.0" in str_repr


class TestCliResponseParser:
    """Tests for CLI response parsing."""

    def test_parse_valid_json(self):
        """Test parsing valid JSON."""
        json_str = '{"key": "value", "number": 42}'
        result = CliResponseParser.parse_json(json_str)

        assert result == {"key": "value", "number": 42}

    def test_parse_json_with_whitespace(self):
        """Test parsing JSON with surrounding whitespace."""
        json_str = '  \n  {"key": "value"}  \n  '
        result = CliResponseParser.parse_json(json_str)

        assert result == {"key": "value"}

    def test_parse_invalid_json_raises_error(self):
        """Test that invalid JSON raises CliError."""
        with pytest.raises(CliError, match="Invalid JSON"):
            CliResponseParser.parse_json('{"invalid": json}')

    def test_parse_empty_json_raises_error(self):
        """Test that empty string raises CliError."""
        with pytest.raises(CliError, match="Empty output"):
            CliResponseParser.parse_json("")

    def test_parse_whitespace_only_raises_error(self):
        """Test that whitespace-only string raises CliError."""
        with pytest.raises(CliError, match="Empty output"):
            CliResponseParser.parse_json("   \n  \n  ")

    def test_parse_text(self):
        """Test parsing plain text."""
        text = "Hello, World!"
        result = CliResponseParser.parse_text(text)

        assert result == "Hello, World!"

    def test_parse_text_with_whitespace(self):
        """Test parsing text with surrounding whitespace."""
        text = "  \n  Hello  \n  "
        result = CliResponseParser.parse_text(text)

        assert result == "Hello"

    def test_parse_empty_text_raises_error(self):
        """Test that empty text raises CliError."""
        with pytest.raises(CliError, match="Empty output"):
            CliResponseParser.parse_text("")

    def test_validate_output_json_success(self):
        """Test successful JSON output validation."""
        output = CliOutput(
            stdout='{"content": "test"}',
            stderr="",
            exit_code=0,
            command="test",
            duration_ms=10.0,
        )

        assert CliResponseParser.validate_output(output, "json") is True

    def test_validate_output_text_success(self):
        """Test successful text output validation."""
        output = CliOutput(
            stdout="plain text",
            stderr="",
            exit_code=0,
            command="test",
            duration_ms=10.0,
        )

        assert CliResponseParser.validate_output(output, "text") is True

    def test_validate_output_invalid_json_raises_error(self):
        """Test that invalid JSON raises CliError."""
        output = CliOutput(
            stdout="not json",
            stderr="",
            exit_code=0,
            command="test",
            duration_ms=10.0,
        )

        with pytest.raises(CliError, match="not valid JSON"):
            CliResponseParser.validate_output(output, "json")

    def test_validate_output_empty_raises_error(self):
        """Test that empty output raises CliError."""
        output = CliOutput(
            stdout="",
            stderr="",
            exit_code=0,
            command="test",
            duration_ms=10.0,
        )

        with pytest.raises(CliError, match="No output"):
            CliResponseParser.validate_output(output, "json")

    def test_validate_output_unknown_format_raises_error(self):
        """Test that unknown format raises CliError."""
        output = CliOutput(
            stdout="data",
            stderr="",
            exit_code=0,
            command="test",
            duration_ms=10.0,
        )

        with pytest.raises(CliError, match="Unknown output format"):
            CliResponseParser.validate_output(output, "unknown")

    def test_extract_json_field_success(self):
        """Test extracting a field from JSON."""
        output = CliOutput(
            stdout='{"name": "test", "value": 42}',
            stderr="",
            exit_code=0,
            command="test",
            duration_ms=10.0,
        )

        result = CliResponseParser.extract_json_field(output, "name")
        assert result == "test"

    def test_extract_json_field_missing_with_default(self):
        """Test extracting missing field with default value."""
        output = CliOutput(
            stdout='{"name": "test"}',
            stderr="",
            exit_code=0,
            command="test",
            duration_ms=10.0,
        )

        result = CliResponseParser.extract_json_field(output, "missing", default="default_value")
        assert result == "default_value"

    def test_extract_json_field_missing_without_default(self):
        """Test extracting missing field without default raises error."""
        output = CliOutput(
            stdout='{"name": "test"}',
            stderr="",
            exit_code=0,
            command="test",
            duration_ms=10.0,
        )

        with pytest.raises(CliError):
            CliResponseParser.extract_json_field(output, "missing")


# ============================================================================
# Module 2: CliProvider Base Class Tests
# ============================================================================


class TestCliProvider:
    """Tests for CliProvider base class."""

    def test_provider_initialization(self):
        """Test CliProvider initialization."""

        class MockCliProvider(CliProvider):
            def _build_args(self, prompt, model, temperature, **kwargs):
                return ["test", "command"]

            def _parse_response(self, output):
                from providers.shared import ModelResponse
                return ModelResponse(content="test", provider=ProviderType.GOOGLE)

            def get_provider_type(self):
                return ProviderType.GOOGLE

            async def generate_content(self, prompt, model_name, **kwargs):
                return None

        provider = MockCliProvider(cli_path="test_cli", timeout_s=60)
        assert provider.cli_path == "test_cli"
        assert provider.timeout_s == 60

    @pytest.mark.asyncio
    async def test_run_cli_success(self):
        """Test successful CLI execution."""

        class MockCliProvider(CliProvider):
            def _build_args(self, prompt, model, temperature, **kwargs):
                return ["echo", "test"]

            def _parse_response(self, output):
                from providers.shared import ModelResponse
                return ModelResponse(content="test", provider=ProviderType.GOOGLE)

            def get_provider_type(self):
                return ProviderType.GOOGLE

            async def generate_content(self, prompt, model_name, **kwargs):
                return None

        provider = MockCliProvider(cli_path="echo")

        # Execute a simple echo command
        output = await provider._run_cli(["echo", "hello"])

        assert output.success
        assert "hello" in output.stdout
        assert output.exit_code == 0
        assert output.duration_ms > 0

    @pytest.mark.asyncio
    async def test_run_cli_failure(self):
        """Test CLI execution with non-zero exit code."""

        class MockCliProvider(CliProvider):
            def _build_args(self, prompt, model, temperature, **kwargs):
                return ["false"]

            def _parse_response(self, output):
                from providers.shared import ModelResponse
                return ModelResponse(content="test", provider=ProviderType.GOOGLE)

            def get_provider_type(self):
                return ProviderType.GOOGLE

            async def generate_content(self, prompt, model_name, **kwargs):
                return None

        provider = MockCliProvider(cli_path="false")
        output = await provider._run_cli(["false"])

        assert not output.success
        assert output.exit_code != 0

    @pytest.mark.asyncio
    async def test_run_cli_timeout(self):
        """Test CLI execution timeout."""

        class MockCliProvider(CliProvider):
            def _build_args(self, prompt, model, temperature, **kwargs):
                return ["sleep", "100"]

            def _parse_response(self, output):
                from providers.shared import ModelResponse
                return ModelResponse(content="test", provider=ProviderType.GOOGLE)

            def get_provider_type(self):
                return ProviderType.GOOGLE

            async def generate_content(self, prompt, model_name, **kwargs):
                return None

        provider = MockCliProvider(timeout_s=1)

        # sleep for much longer than timeout to ensure timeout is triggered
        with pytest.raises(CliTimeoutError):
            await provider._run_cli(["sleep", "100"])

    @pytest.mark.asyncio
    async def test_run_cli_not_found(self):
        """Test CLI execution when binary not found."""

        class MockCliProvider(CliProvider):
            def _build_args(self, prompt, model, temperature, **kwargs):
                return ["nonexistent_command_xyz"]

            def _parse_response(self, output):
                from providers.shared import ModelResponse
                return ModelResponse(content="test", provider=ProviderType.GOOGLE)

            def get_provider_type(self):
                return ProviderType.GOOGLE

            async def generate_content(self, prompt, model_name, **kwargs):
                return None

        provider = MockCliProvider()

        with pytest.raises(CliNotFoundError):
            await provider._run_cli(["nonexistent_command_xyz"])

    def test_classify_error_not_found(self):
        """Test error classification for not found."""

        class MockCliProvider(CliProvider):
            def _build_args(self, prompt, model, temperature, **kwargs):
                return ["test"]

            def _parse_response(self, output):
                pass

            def get_provider_type(self):
                return ProviderType.GOOGLE

            async def generate_content(self, prompt, model_name, **kwargs):
                pass

        provider = MockCliProvider()
        error = CliNotFoundError("binary not found")
        assert provider.classify_error(error) == "not_found"

    def test_classify_error_timeout(self):
        """Test error classification for timeout."""

        class MockCliProvider(CliProvider):
            def _build_args(self, prompt, model, temperature, **kwargs):
                return ["test"]

            def _parse_response(self, output):
                pass

            def get_provider_type(self):
                return ProviderType.GOOGLE

            async def generate_content(self, prompt, model_name, **kwargs):
                pass

        provider = MockCliProvider()
        error = CliTimeoutError("timeout")
        assert provider.classify_error(error) == "timeout"

    def test_should_fallback(self):
        """Test fallback decision logic."""

        class MockCliProvider(CliProvider):
            def _build_args(self, prompt, model, temperature, **kwargs):
                return ["test"]

            def _parse_response(self, output):
                pass

            def get_provider_type(self):
                return ProviderType.GOOGLE

            async def generate_content(self, prompt, model_name, **kwargs):
                pass

        provider = MockCliProvider()

        # All CLI errors should trigger fallback
        assert provider.should_fallback(CliError("test")) is True
        assert provider.should_fallback(CliNotFoundError("test")) is True
        assert provider.should_fallback(CliTimeoutError("test")) is True


# ============================================================================
# Module 3: GeminiCliProvider Tests
# ============================================================================


class TestGeminiCliProvider:
    """Tests for Gemini CLI provider."""

    def test_provider_type(self):
        """Test that provider reports correct type."""
        provider = GeminiCliProvider(cli_path="test_gemini")
        assert provider.get_provider_type() == ProviderType.GOOGLE

    def test_build_args_basic(self):
        """Test CLI argument building with basic parameters."""
        provider = GeminiCliProvider(cli_path="gemini")

        args = provider._build_args(
            prompt="Hello, world!",
            model="gemini-2-flash",
            temperature=0.7,
        )

        assert args[0] == "gemini"
        assert args[1] == "generate"
        assert "--prompt" in args
        assert "Hello, world!" in args
        assert "--model" in args
        assert "gemini-2-flash" in args
        assert "--temperature" in args
        assert "0.7" in args

    def test_build_args_with_system_prompt(self):
        """Test CLI argument building with system prompt."""
        provider = GeminiCliProvider(cli_path="gemini")

        args = provider._build_args(
            prompt="User prompt",
            model="gemini-2-flash",
            temperature=0.5,
            system_prompt="You are helpful.",
        )

        # Combined prompt should include both system and user
        combined = " ".join(args)
        assert "You are helpful." in combined
        assert "User prompt" in combined

    def test_build_args_with_max_tokens(self):
        """Test CLI argument building with max tokens."""
        provider = GeminiCliProvider(cli_path="gemini")

        args = provider._build_args(
            prompt="test",
            model="gemini-2-flash",
            temperature=0.7,
            max_output_tokens=1000,
        )

        assert "--max-output-tokens" in args
        assert "1000" in args

    def test_build_args_with_thinking_mode(self):
        """Test CLI argument building with thinking mode."""
        provider = GeminiCliProvider(cli_path="gemini")

        args = provider._build_args(
            prompt="test",
            model="gemini-2-flash",
            temperature=0.7,
            thinking_mode="high",
        )

        assert "--thinking-mode" in args
        assert "high" in args

    def test_parse_response_success(self):
        """Test parsing successful Gemini response."""
        provider = GeminiCliProvider(cli_path="gemini")

        json_output = json.dumps({
            "content": "This is the response",
            "usage": {
                "input_tokens": 10,
                "output_tokens": 20,
                "total_tokens": 30,
            },
            "model": "gemini-2-flash",
            "finish_reason": "STOP",
            "is_blocked_by_safety": False,
        })

        output = CliOutput(
            stdout=json_output,
            stderr="",
            exit_code=0,
            command="test",
            duration_ms=100.0,
        )

        response = provider._parse_response(output)

        assert response.content == "This is the response"
        assert response.usage["input_tokens"] == 10
        assert response.usage["output_tokens"] == 20
        assert response.model_name == "gemini-2-flash"
        assert response.provider == ProviderType.GOOGLE
        assert response.friendly_name == "Gemini (CLI)"

    def test_parse_response_missing_content(self):
        """Test parsing Gemini response with missing content field."""
        provider = GeminiCliProvider(cli_path="gemini")

        json_output = json.dumps({
            "usage": {"input_tokens": 10},
        })

        output = CliOutput(
            stdout=json_output,
            stderr="",
            exit_code=0,
            command="test",
            duration_ms=100.0,
        )

        with pytest.raises(CliError, match="missing 'content'"):
            provider._parse_response(output)

    def test_parse_response_invalid_json(self):
        """Test parsing Gemini response with invalid JSON."""
        provider = GeminiCliProvider(cli_path="gemini")

        output = CliOutput(
            stdout="not json",
            stderr="",
            exit_code=0,
            command="test",
            duration_ms=100.0,
        )

        with pytest.raises(CliError):
            provider._parse_response(output)


# ============================================================================
# Module 4: CodexCliProvider Tests
# ============================================================================


class TestCodexCliProvider:
    """Tests for Codex (OpenAI) CLI provider."""

    def test_provider_type(self):
        """Test that provider reports correct type."""
        provider = CodexCliProvider(cli_path="test_codex")
        assert provider.get_provider_type() == ProviderType.OPENAI

    def test_build_args_basic(self):
        """Test CLI argument building with basic parameters."""
        provider = CodexCliProvider(cli_path="codex")

        args = provider._build_args(
            prompt="Hello, world!",
            model="gpt-4",
            temperature=0.7,
        )

        assert args[0] == "codex"
        assert args[1] == "chat-completion"
        assert "--message" in args
        assert "Hello, world!" in args
        assert "--model" in args
        assert "gpt-4" in args
        assert "--temperature" in args
        assert "0.7" in args

    def test_build_args_with_system_prompt(self):
        """Test CLI argument building with system prompt."""
        provider = CodexCliProvider(cli_path="codex")

        args = provider._build_args(
            prompt="User prompt",
            model="gpt-4",
            temperature=0.5,
            system_prompt="You are helpful.",
        )

        # Combined message should include both system and user
        combined = " ".join(args)
        assert "You are helpful." in combined
        assert "User prompt" in combined

    def test_build_args_with_max_tokens(self):
        """Test CLI argument building with max tokens."""
        provider = CodexCliProvider(cli_path="codex")

        args = provider._build_args(
            prompt="test",
            model="gpt-4",
            temperature=0.7,
            max_output_tokens=2000,
        )

        assert "--max-tokens" in args
        assert "2000" in args

    def test_build_args_with_top_p(self):
        """Test CLI argument building with top_p."""
        provider = CodexCliProvider(cli_path="codex")

        args = provider._build_args(
            prompt="test",
            model="gpt-4",
            temperature=0.7,
            top_p=0.9,
        )

        assert "--top-p" in args
        assert "0.9" in args

    def test_build_args_with_frequency_penalty(self):
        """Test CLI argument building with frequency penalty."""
        provider = CodexCliProvider(cli_path="codex")

        args = provider._build_args(
            prompt="test",
            model="gpt-4",
            temperature=0.7,
            frequency_penalty=0.5,
        )

        assert "--frequency-penalty" in args
        assert "0.5" in args

    def test_build_args_with_presence_penalty(self):
        """Test CLI argument building with presence penalty."""
        provider = CodexCliProvider(cli_path="codex")

        args = provider._build_args(
            prompt="test",
            model="gpt-4",
            temperature=0.7,
            presence_penalty=0.5,
        )

        assert "--presence-penalty" in args
        assert "0.5" in args

    def test_parse_response_success(self):
        """Test parsing successful Codex response."""
        provider = CodexCliProvider(cli_path="codex")

        json_output = json.dumps({
            "content": "This is the response",
            "usage": {
                "prompt_tokens": 10,
                "completion_tokens": 20,
                "total_tokens": 30,
            },
            "model": "gpt-4",
            "finish_reason": "stop",
        })

        output = CliOutput(
            stdout=json_output,
            stderr="",
            exit_code=0,
            command="test",
            duration_ms=100.0,
        )

        response = provider._parse_response(output)

        assert response.content == "This is the response"
        assert response.usage["input_tokens"] == 10
        assert response.usage["output_tokens"] == 20
        assert response.model_name == "gpt-4"
        assert response.provider == ProviderType.OPENAI
        assert response.friendly_name == "OpenAI (CLI)"

    def test_parse_response_missing_content(self):
        """Test parsing Codex response with missing content field."""
        provider = CodexCliProvider(cli_path="codex")

        json_output = json.dumps({
            "usage": {"prompt_tokens": 10},
        })

        output = CliOutput(
            stdout=json_output,
            stderr="",
            exit_code=0,
            command="test",
            duration_ms=100.0,
        )

        with pytest.raises(CliError, match="missing 'content'"):
            provider._parse_response(output)

    def test_parse_response_invalid_json(self):
        """Test parsing Codex response with invalid JSON."""
        provider = CodexCliProvider(cli_path="codex")

        output = CliOutput(
            stdout="not json",
            stderr="",
            exit_code=0,
            command="test",
            duration_ms=100.0,
        )

        with pytest.raises(CliError):
            provider._parse_response(output)

    def test_parse_response_openai_token_names(self):
        """Test that Codex parses OpenAI-style token counts."""
        provider = CodexCliProvider(cli_path="codex")

        json_output = json.dumps({
            "content": "Response",
            "usage": {
                "prompt_tokens": 100,  # OpenAI style
                "completion_tokens": 50,  # OpenAI style
                "total_tokens": 150,
            },
            "model": "gpt-4",
        })

        output = CliOutput(
            stdout=json_output,
            stderr="",
            exit_code=0,
            command="test",
            duration_ms=100.0,
        )

        response = provider._parse_response(output)

        # Should be converted to standard names
        assert response.usage["input_tokens"] == 100
        assert response.usage["output_tokens"] == 50
        assert response.usage["total_tokens"] == 150


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
