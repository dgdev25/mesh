"""Unit tests for CLI-based providers and CLI output parsing."""

import json

import pytest

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
                return ModelResponse(content="test", provider=ProviderType.GEMINI_CLI)

            def get_provider_type(self):
                return ProviderType.GEMINI_CLI

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
                return ModelResponse(content="test", provider=ProviderType.GEMINI_CLI)

            def get_provider_type(self):
                return ProviderType.GEMINI_CLI

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
                return ModelResponse(content="test", provider=ProviderType.GEMINI_CLI)

            def get_provider_type(self):
                return ProviderType.GEMINI_CLI

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
                return ModelResponse(content="test", provider=ProviderType.GEMINI_CLI)

            def get_provider_type(self):
                return ProviderType.GEMINI_CLI

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
                return ModelResponse(content="test", provider=ProviderType.GEMINI_CLI)

            def get_provider_type(self):
                return ProviderType.GEMINI_CLI

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
                return ProviderType.GEMINI_CLI

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
                return ProviderType.GEMINI_CLI

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
                return ProviderType.GEMINI_CLI

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
        assert provider.get_provider_type() == ProviderType.GEMINI_CLI

    def test_build_args_basic(self):
        """`gemini -p PROMPT -m MODEL -o json` is the real shape."""
        provider = GeminiCliProvider(cli_path="gemini")
        args = provider._build_args(prompt="Hello, world!", model="gemini-2.5-flash", temperature=0.7)
        assert args == ["gemini", "-p", "Hello, world!", "-m", "gemini-2.5-flash", "-o", "json"]

    def test_build_args_with_system_prompt(self):
        """System prompt is concatenated into the -p prompt."""
        provider = GeminiCliProvider(cli_path="gemini")
        args = provider._build_args(
            prompt="User prompt",
            model="gemini-2.5-flash",
            temperature=0.5,
            system_prompt="You are helpful.",
        )
        prompt_index = args.index("-p") + 1
        assert "You are helpful." in args[prompt_index]
        assert "User prompt" in args[prompt_index]

    def test_build_args_max_tokens_and_thinking_mode_silently_ignored(self):
        """The real Gemini CLI does not accept --max-output-tokens or --thinking-mode flags."""
        provider = GeminiCliProvider(cli_path="gemini")
        args = provider._build_args(
            prompt="t",
            model="gemini-2.5-flash",
            temperature=0.7,
            max_output_tokens=1000,
            thinking_mode="high",
        )
        # No --max-output-tokens / --thinking-mode in the real CLI's surface
        assert "--max-output-tokens" not in args
        assert "--thinking-mode" not in args

    def test_parse_response_success(self):
        """Parse the real `gemini -o json` envelope: {session_id, response, stats}."""
        provider = GeminiCliProvider(cli_path="gemini")
        gemini_json = json.dumps({
            "session_id": "abc-123",
            "response": "This is the response",
            "stats": {
                "models": {
                    "gemini-2.5-flash": {
                        "tokens": {"input": 10, "prompt": 850, "candidates": 20, "total": 30},
                    }
                },
            },
        })
        output = CliOutput(stdout=gemini_json, stderr="", exit_code=0, command="test", duration_ms=100.0)
        response = provider._parse_response(output)
        assert response.content == "This is the response"
        assert response.usage["input_tokens"] == 850
        assert response.usage["output_tokens"] == 20
        assert response.usage["total_tokens"] == 30
        assert response.model_name == "gemini-2.5-flash"
        assert response.provider == ProviderType.GEMINI_CLI
        assert response.friendly_name == "Gemini (CLI)"

    def test_parse_response_missing_content(self):
        """A response with no `response` key must raise."""
        provider = GeminiCliProvider(cli_path="gemini")
        gemini_json = json.dumps({"session_id": "x", "stats": {}})
        output = CliOutput(stdout=gemini_json, stderr="", exit_code=0, command="test", duration_ms=100.0)
        with pytest.raises(CliError, match="missing 'response'"):
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
        assert provider.get_provider_type() == ProviderType.CODEX_CLI

    def test_build_args_basic(self):
        """`codex exec --json --skip-git-repo-check -m MODEL PROMPT` is the real shape."""
        provider = CodexCliProvider(cli_path="codex")
        args = provider._build_args(prompt="Hello, world!", model="gpt-5.3-codex", temperature=0.7)
        assert args == [
            "codex", "exec", "--json", "--skip-git-repo-check",
            "-m", "gpt-5.3-codex", "Hello, world!",
        ]

    def test_build_args_with_system_prompt(self):
        """System prompt is concatenated into the positional prompt."""
        provider = CodexCliProvider(cli_path="codex")
        args = provider._build_args(
            prompt="User prompt",
            model="gpt-5.3-codex",
            temperature=0.5,
            system_prompt="You are helpful.",
        )
        # Last arg is the prompt; check both system + user merged into it.
        assert "You are helpful." in args[-1]
        assert "User prompt" in args[-1]

    def test_build_args_unsupported_flags_silently_dropped(self):
        """Real codex CLI doesn't honour --max-tokens / --top-p / penalty flags."""
        provider = CodexCliProvider(cli_path="codex")
        args = provider._build_args(
            prompt="t",
            model="gpt-5.3-codex",
            temperature=0.7,
            max_output_tokens=2000,
            top_p=0.9,
            frequency_penalty=0.5,
            presence_penalty=0.5,
        )
        for flag in ("--max-tokens", "--top-p", "--frequency-penalty", "--presence-penalty"):
            assert flag not in args, f"{flag} should not be passed to real codex CLI"

    def test_parse_response_success(self):
        """Parse the real `codex exec --json` JSONL stream."""
        provider = CodexCliProvider(cli_path="codex")
        jsonl = "\n".join([
            '{"type":"thread.started","thread_id":"abc"}',
            '{"type":"turn.started"}',
            '{"type":"item.completed","item":{"id":"item_0","type":"agent_message","text":"This is the response"}}',
            '{"type":"turn.completed","usage":{"input_tokens":100,"cached_input_tokens":40,"output_tokens":50,"reasoning_output_tokens":10}}',
        ])
        output = CliOutput(stdout=jsonl, stderr="", exit_code=0, command="test", duration_ms=100.0)
        response = provider._parse_response(output)
        assert response.content == "This is the response"
        assert response.usage["input_tokens"] == 100
        assert response.usage["output_tokens"] == 50
        assert response.usage["total_tokens"] == 160  # input + output + reasoning
        assert response.model_name == "codex"
        assert response.provider == ProviderType.CODEX_CLI
        assert response.metadata["cached_input_tokens"] == 40
        assert response.metadata["reasoning_output_tokens"] == 10

    def test_parse_response_missing_agent_message(self):
        """A stream with no agent_message must raise."""
        provider = CodexCliProvider(cli_path="codex")
        jsonl = '{"type":"turn.completed","usage":{"input_tokens":1,"output_tokens":0}}'
        output = CliOutput(stdout=jsonl, stderr="", exit_code=0, command="test", duration_ms=100.0)
        with pytest.raises(CliError, match="no agent_message"):
            provider._parse_response(output)

    def test_parse_response_ignores_non_json_lines(self):
        """Real CLI sometimes emits non-JSON noise; parser must skip cleanly."""
        provider = CodexCliProvider(cli_path="codex")
        jsonl = "\n".join([
            "Reading additional input from stdin...",
            '{"type":"item.completed","item":{"type":"agent_message","text":"hello"}}',
            '{"type":"turn.completed","usage":{"input_tokens":1,"output_tokens":1}}',
        ])
        output = CliOutput(stdout=jsonl, stderr="", exit_code=0, command="test", duration_ms=100.0)
        response = provider._parse_response(output)
        assert response.content == "hello"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
