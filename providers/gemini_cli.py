"""Gemini CLI-based model provider."""

import json
import logging
from typing import ClassVar, List, Optional

from .cli_base import CliProvider
from .registries.gemini import GeminiModelRegistry
from .registry_provider_mixin import RegistryBackedProviderMixin
from .shared import ModelCapabilities, ModelResponse, ProviderType
from .shared.cli_output import CliError, CliOutput, CliResponseParser

logger = logging.getLogger(__name__)


class GeminiCliProvider(RegistryBackedProviderMixin, CliProvider):
    """Gemini model provider using the CLI binary.

    This provider executes the `gemini` CLI command to generate content,
    bypassing the SDK and allowing for containerized execution.

    CLI Usage:
        gemini generate --prompt "text" --model "gemini-2-flash" --temperature 0.7
    """

    REGISTRY_CLASS = GeminiModelRegistry
    MODEL_CAPABILITIES: ClassVar[dict[str, ModelCapabilities]] = {}

    def __init__(self, cli_path: str = "gemini", timeout_s: int = 30, **kwargs):
        """Initialize Gemini CLI provider.

        Args:
            cli_path: Path to gemini binary (default: "gemini")
            timeout_s: Subprocess timeout in seconds (default: 30)
            **kwargs: Additional config (ignored, CLI has no API key)
        """
        self._ensure_registry()
        # CLI providers don't use API keys, but parent expects one
        kwargs["api_key"] = "cli"
        CliProvider.__init__(self, cli_path=cli_path, timeout_s=timeout_s, **kwargs)
        self._invalidate_capability_cache()

    def get_provider_type(self) -> ProviderType:
        """Return the provider identity."""
        return ProviderType.GOOGLE

    def _build_args(
        self,
        prompt: str,
        model: str,
        temperature: float = 0.7,
        max_output_tokens: Optional[int] = None,
        system_prompt: Optional[str] = None,
        **kwargs,
    ) -> List[str]:
        """Build CLI arguments for gemini command.

        Args:
            prompt: User prompt text
            model: Model name (resolved)
            temperature: Sampling temperature (0.0-2.0)
            max_output_tokens: Max tokens to generate
            system_prompt: Optional system instructions
            **kwargs: Additional parameters (thinking_mode, etc.)

        Returns:
            Command arguments: ["gemini", "generate", "--prompt", ..., "--model", ...]
        """
        args: List[str] = [self.cli_path, "generate"]

        # Combine system and user prompts if both present
        if system_prompt:
            full_prompt = f"{system_prompt}\n\n{prompt}"
        else:
            full_prompt = prompt

        # Add prompt (required)
        args.extend(["--prompt", full_prompt])

        # Add model (required)
        args.extend(["--model", model])

        # Add temperature
        args.extend(["--temperature", str(temperature)])

        # Add max output tokens if specified
        if max_output_tokens:
            args.extend(["--max-output-tokens", str(max_output_tokens)])

        # Add thinking mode if specified
        thinking_mode = kwargs.get("thinking_mode")
        if thinking_mode:
            args.extend(["--thinking-mode", thinking_mode])

        logger.debug(f"Built Gemini CLI args: {args[0:3]} ... (prompt hidden)")
        return args

    def _parse_response(self, output: CliOutput) -> ModelResponse:
        """Parse Gemini CLI JSON output into ModelResponse.

        Expected JSON format:
        {
            "content": "response text",
            "usage": {
                "input_tokens": 100,
                "output_tokens": 50,
                "total_tokens": 150
            },
            "model": "gemini-2-flash",
            "metadata": {...}
        }

        Args:
            output: CliOutput with JSON content

        Returns:
            ModelResponse with parsed data

        Raises:
            CliError: If JSON parsing fails or required fields missing
        """
        # Validate output is JSON
        CliResponseParser.validate_output(output, expected_format="json")

        # Parse JSON
        try:
            data = CliResponseParser.parse_json(output.raw_output)
        except CliError as e:
            raise CliError(f"Failed to parse Gemini CLI response: {e}") from e

        # Extract required fields
        content = data.get("content", "")
        if not content:
            raise CliError("Gemini CLI response missing 'content' field")

        # Extract model name
        model_name = data.get("model", "gemini-unknown")

        # Extract usage data
        usage_data = data.get("usage", {})
        usage = {
            "input_tokens": usage_data.get("input_tokens", 0),
            "output_tokens": usage_data.get("output_tokens", 0),
            "total_tokens": usage_data.get("total_tokens", 0),
        }

        # Extract metadata
        metadata = data.get("metadata", {})
        metadata.setdefault("finish_reason", data.get("finish_reason", "STOP"))
        metadata.setdefault("is_blocked_by_safety", data.get("is_blocked_by_safety", False))
        metadata.setdefault("safety_feedback", data.get("safety_feedback"))

        return ModelResponse(
            content=content,
            usage=usage,
            model_name=model_name,
            friendly_name="Gemini (CLI)",
            provider=ProviderType.GOOGLE,
            metadata=metadata,
        )

    async def generate_content(
        self,
        prompt: str,
        model_name: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.3,
        max_output_tokens: Optional[int] = None,
        **kwargs,
    ) -> ModelResponse:
        """Generate content using Gemini CLI.

        Args:
            prompt: User prompt
            model_name: Model name (or alias)
            system_prompt: Optional system instructions
            temperature: Sampling temperature (0.0-2.0)
            max_output_tokens: Max tokens in response
            **kwargs: Additional parameters (thinking_mode, etc.)

        Returns:
            ModelResponse with generated content

        Raises:
            ValueError: If model not supported or parameters invalid
            RuntimeError: If CLI execution fails
        """
        # Validate and resolve model name
        self.validate_parameters(model_name, temperature)
        resolved_model = self._resolve_model_name(model_name)

        # Build CLI arguments
        args = self._build_args(
            prompt=prompt,
            model=resolved_model,
            temperature=temperature,
            max_output_tokens=max_output_tokens,
            system_prompt=system_prompt,
            **kwargs,
        )

        # Execute CLI
        try:
            output = await self._run_cli(args)
        except Exception as e:
            raise RuntimeError(f"Gemini CLI execution failed: {e}") from e

        # Check for non-zero exit
        if not output.success:
            raise RuntimeError(f"Gemini CLI exited with code {output.exit_code}: {output.stderr}")

        # Parse response
        try:
            return self._parse_response(output)
        except CliError as e:
            raise RuntimeError(f"Failed to parse Gemini CLI response: {e}") from e


# Ensure registry loads at import time
GeminiCliProvider._ensure_registry()
