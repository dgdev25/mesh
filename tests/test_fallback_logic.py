"""Tests for fallback chain logic in ModelProviderRegistry.

This module tests:
1. Error classification (CliNotFoundError, CliTimeoutError, etc.)
2. Fallback chain ordering (CLI tools -> OpenRouter)
3. Provider selection based on availability
4. Graceful degradation when providers fail
5. Configuration loading and validation
"""

import logging
from unittest.mock import AsyncMock, Mock, patch

import pytest

from providers.registry import ModelProviderRegistry
from providers.shared import ModelResponse
from providers.shared.cli_output import (
    CliError,
    CliNotFoundError,
    CliTimeoutError,
)
from utils.env import validate_cli_environment, validate_provider_environment


class TestErrorClassification:
    """Test error classification logic in CliProvider."""

    def test_classify_cli_not_found_error(self):
        """CLI binary not found should be classified as 'not_found'."""
        from providers.cli_base import CliProvider

        # Create mock provider instance
        provider = Mock(spec=CliProvider)
        provider.classify_error = CliProvider.classify_error.__get__(provider, CliProvider)

        error = CliNotFoundError("gemini binary not found")
        classification = provider.classify_error(error)

        assert classification == "not_found"

    def test_classify_cli_timeout_error(self):
        """CLI timeout should be classified as 'timeout'."""
        from providers.cli_base import CliProvider

        provider = Mock(spec=CliProvider)
        provider.classify_error = CliProvider.classify_error.__get__(provider, CliProvider)

        error = CliTimeoutError("CLI command exceeded 30s timeout")
        classification = provider.classify_error(error)

        assert classification == "timeout"

    def test_classify_cli_invalid_json_error(self):
        """CLI error with JSON mention should be classified as 'invalid_output'."""
        from providers.cli_base import CliProvider

        provider = Mock(spec=CliProvider)
        provider.classify_error = CliProvider.classify_error.__get__(provider, CliProvider)

        error = CliError("Invalid JSON in CLI output: Unexpected token")
        classification = provider.classify_error(error)

        assert classification == "invalid_output"

    def test_classify_unknown_error(self):
        """Other errors should be classified as 'unknown'."""
        from providers.cli_base import CliProvider

        provider = Mock(spec=CliProvider)
        provider.classify_error = CliProvider.classify_error.__get__(provider, CliProvider)

        error = CliError("Some other error")
        classification = provider.classify_error(error)

        assert classification == "unknown"

    def test_should_fallback_on_cli_errors(self):
        """All CliError types should trigger fallback."""
        from providers.cli_base import CliProvider

        provider = Mock(spec=CliProvider)
        provider.should_fallback = CliProvider.should_fallback.__get__(provider, CliProvider)

        for error_class in [CliError, CliNotFoundError, CliTimeoutError]:
            error = error_class("Test error")
            assert provider.should_fallback(error) is True

    def test_should_not_fallback_on_other_errors(self):
        """Non-CLI errors should not trigger fallback."""
        from providers.cli_base import CliProvider

        provider = Mock(spec=CliProvider)
        provider.should_fallback = CliProvider.should_fallback.__get__(provider, CliProvider)

        error = ValueError("Some other error")
        assert provider.should_fallback(error) is False


class TestFallbackChainLogic:
    """Test the fallback chain in ModelProviderRegistry."""

    @pytest.mark.asyncio
    async def test_fallback_chain_all_providers_fail(self):
        """When all providers fail, should raise RuntimeError with last error."""
        registry = ModelProviderRegistry()

        # Mock providers to fail
        mock_gemini = Mock()
        mock_gemini.generate_content = AsyncMock(
            side_effect=CliNotFoundError("gemini not found")
        )

        mock_codex = Mock()
        mock_codex.generate_content = AsyncMock(
            side_effect=CliTimeoutError("codex timeout")
        )

        with patch.object(ModelProviderRegistry, "get_provider") as mock_get_provider:
            mock_get_provider.side_effect = [mock_gemini, mock_codex, None]

            with patch("shutil.which") as mock_which:
                mock_which.side_effect = [True, True]  # Both CLIs "exist"

                with patch("utils.env.get_env") as mock_get_env:
                    mock_get_env.return_value = None  # No OpenRouter key

                    request = {
                        "prompt": "test",
                        "model_name": "gemini-2.5-flash",
                        "temperature": 1.0,
                    }

                    with pytest.raises(RuntimeError, match="All providers exhausted"):
                        await registry.invoke_with_fallback(request)

    @pytest.mark.asyncio
    async def test_fallback_chain_first_provider_succeeds(self):
        """When first provider succeeds, should return immediately."""
        registry = ModelProviderRegistry()

        # Mock successful response
        success_response = Mock(spec=ModelResponse)
        success_response.success = True
        success_response.content = "Generated content"

        mock_gemini = Mock()
        mock_gemini.generate_content = AsyncMock(return_value=success_response)

        with patch.object(ModelProviderRegistry, "get_provider") as mock_get_provider:
            mock_get_provider.return_value = mock_gemini

            with patch("shutil.which") as mock_which:
                mock_which.return_value = "/usr/bin/gemini"

                with patch("utils.env.get_env") as mock_get_env:
                    mock_get_env.return_value = None

                    request = {
                        "prompt": "test",
                        "model_name": "gemini-2.5-flash",
                        "temperature": 1.0,
                    }

                    response = await registry.invoke_with_fallback(request)

                    assert response == success_response
                    # Verify we only called one provider (no fallback)
                    assert mock_gemini.generate_content.call_count == 1

    @pytest.mark.asyncio
    async def test_fallback_chain_tries_next_on_failure(self):
        """When first provider fails, should try next provider."""
        registry = ModelProviderRegistry()

        # First provider fails
        mock_gemini = Mock()
        mock_gemini.generate_content = AsyncMock(
            side_effect=CliNotFoundError("gemini not found")
        )

        # Second provider succeeds
        success_response = Mock(spec=ModelResponse)
        success_response.success = True
        success_response.content = "Generated content"

        mock_codex = Mock()
        mock_codex.generate_content = AsyncMock(return_value=success_response)

        with patch.object(ModelProviderRegistry, "get_provider") as mock_get_provider:
            mock_get_provider.side_effect = [mock_gemini, mock_codex]

            with patch("shutil.which") as mock_which:
                # First "which" is for gemini, second for codex
                mock_which.side_effect = [True, True]

                with patch("utils.env.get_env") as mock_get_env:
                    mock_get_env.return_value = None

                    request = {
                        "prompt": "test",
                        "model": "gpt-4",
                        "temperature": 1.0,
                    }

                    response = await registry.invoke_with_fallback(request)

                    assert response == success_response
                    # Verify both were called (fallback happened)
                    assert mock_gemini.generate_content.call_count == 1
                    assert mock_codex.generate_content.call_count == 1

    @pytest.mark.asyncio
    async def test_fallback_chain_skips_none_providers(self):
        """Fallback chain should skip None providers gracefully."""
        registry = ModelProviderRegistry()

        # Second provider is None (not initialized)
        mock_gemini = Mock()
        mock_gemini.generate_content = AsyncMock(
            side_effect=CliNotFoundError("gemini not found")
        )

        # Third provider succeeds
        success_response = Mock(spec=ModelResponse)
        success_response.success = True

        mock_openrouter = Mock()
        mock_openrouter.generate_content = AsyncMock(return_value=success_response)

        with patch.object(ModelProviderRegistry, "get_provider") as mock_get_provider:
            # Return: Gemini (fail), None (skip), OpenRouter (succeed)
            mock_get_provider.side_effect = [mock_gemini, None, mock_openrouter]

            with patch("shutil.which") as mock_which:
                mock_which.side_effect = [True, False]  # gemini exists, codex missing

                with patch("utils.env.get_env") as mock_get_env:
                    mock_get_env.return_value = "test-key"  # OpenRouter enabled

                    request = {
                        "prompt": "test",
                        "model": "mistral-medium",
                        "temperature": 1.0,
                    }

                    response = await registry.invoke_with_fallback(request)

                    assert response == success_response
                    # Verify OpenRouter was called after Gemini failed
                    assert mock_openrouter.generate_content.call_count == 1

    @pytest.mark.asyncio
    async def test_fallback_chain_no_providers_available(self):
        """When no providers available, should raise error immediately."""
        registry = ModelProviderRegistry()

        with patch("shutil.which") as mock_which:
            mock_which.return_value = None  # No CLIs found

            with patch("utils.env.get_env") as mock_get_env:
                mock_get_env.return_value = None  # No OpenRouter key

                request = {
                    "prompt": "test",
                    "model_name": "test-model",
                    "temperature": 1.0,
                }

                with pytest.raises(
                    RuntimeError, match="No providers available|All providers exhausted"
                ):
                    await registry.invoke_with_fallback(request)


class TestConfigurationLoading:
    """Test configuration loading for CLI paths and timeouts."""

    def test_cli_paths_config_loaded(self):
        """CLI_PATHS config should load from environment variables."""
        import config

        # Should have gemini and codex keys
        assert "gemini" in config.CLI_PATHS
        assert "codex" in config.CLI_PATHS

        # Should be strings
        assert isinstance(config.CLI_PATHS["gemini"], str)
        assert isinstance(config.CLI_PATHS["codex"], str)

    def test_cli_timeout_config_loaded(self):
        """CLI_TIMEOUT_SECONDS should load as integer."""
        import config

        assert isinstance(config.CLI_TIMEOUT_SECONDS, int)
        assert config.CLI_TIMEOUT_SECONDS > 0

    def test_openrouter_config_loaded(self):
        """OPENROUTER_API_KEY and OPENROUTER_ENABLED should load correctly."""
        import config

        # Should be either None or string
        assert config.OPENROUTER_API_KEY is None or isinstance(
            config.OPENROUTER_API_KEY, str
        )

        # OPENROUTER_ENABLED should be bool
        assert isinstance(config.OPENROUTER_ENABLED, bool)

        # Consistency: if key is set, enabled should be True
        if config.OPENROUTER_API_KEY:
            assert config.OPENROUTER_ENABLED is True


class TestEnvironmentValidation:
    """Test environment validation functions."""

    def test_validate_cli_environment_returns_dict(self):
        """validate_cli_environment should return dict of availability."""
        results = validate_cli_environment()

        assert isinstance(results, dict)
        assert "gemini" in results
        assert "codex" in results
        assert all(isinstance(v, bool) for v in results.values())

    def test_validate_provider_environment_returns_dict(self):
        """validate_provider_environment should return dict of availability."""
        results = validate_provider_environment()

        assert isinstance(results, dict)
        assert "openrouter" in results
        assert "gemini" in results
        assert "codex" in results
        assert all(isinstance(v, bool) for v in results.values())

    def test_validate_cli_environment_detects_missing_tools(self):
        """validate_cli_environment should detect missing CLI tools."""
        with patch("utils.env.shutil.which") as mock_which:
            mock_which.return_value = None  # No CLIs found

            results = validate_cli_environment()

            # Both should be False
            assert results["gemini"] is False
            assert results["codex"] is False

    def test_validate_cli_environment_detects_available_tools(self):
        """validate_cli_environment should detect available CLI tools."""
        with patch("utils.env.shutil.which") as mock_which:
            mock_which.return_value = "/usr/bin/tool"  # Tools found

            results = validate_cli_environment()

            # Both should be True
            assert results["gemini"] is True
            assert results["codex"] is True


class TestLoggingAndDiagnostics:
    """Test logging output for provider selection and fallback."""

    @pytest.mark.asyncio
    async def test_logging_on_provider_success(self, caplog):
        """Should log success when provider succeeds."""
        caplog.set_level(logging.INFO)
        registry = ModelProviderRegistry()

        success_response = Mock(spec=ModelResponse)
        success_response.success = True

        mock_gemini = Mock()
        mock_gemini.generate_content = AsyncMock(return_value=success_response)

        with patch.object(ModelProviderRegistry, "get_provider") as mock_get_provider:
            mock_get_provider.return_value = mock_gemini

            with patch("shutil.which") as mock_which:
                mock_which.return_value = "/usr/bin/gemini"

                with patch("utils.env.get_env") as mock_get_env:
                    mock_get_env.return_value = None

                    request = {
                        "prompt": "test",
                        "model": "test-model",
                        "temperature": 1.0,
                    }

                    await registry.invoke_with_fallback(request)

                    # Check that success was logged
                    assert any(
                        "Successfully used" in record.message
                        for record in caplog.records
                        if record.levelname == "INFO"
                    )

    @pytest.mark.asyncio
    async def test_logging_on_provider_fallback(self, caplog):
        """Should log fallback attempts."""
        caplog.set_level(logging.WARNING)
        registry = ModelProviderRegistry()

        mock_gemini = Mock()
        mock_gemini.generate_content = AsyncMock(
            side_effect=CliNotFoundError("gemini not found")
        )

        success_response = Mock(spec=ModelResponse)
        success_response.success = True

        mock_codex = Mock()
        mock_codex.generate_content = AsyncMock(return_value=success_response)

        with patch.object(ModelProviderRegistry, "get_provider") as mock_get_provider:
            mock_get_provider.side_effect = [mock_gemini, mock_codex]

            with patch("shutil.which") as mock_which:
                mock_which.side_effect = [True, True]

                with patch("utils.env.get_env") as mock_get_env:
                    mock_get_env.return_value = None

                    request = {
                        "prompt": "test",
                        "model_name": "test-model",
                        "temperature": 1.0,
                    }

                    await registry.invoke_with_fallback(request)

                    # Check that fallback was logged
                    assert any(
                        "failed" in record.message.lower()
                        for record in caplog.records
                        if record.levelname == "WARNING"
                    )
