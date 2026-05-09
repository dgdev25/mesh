"""Codex (OpenAI) CLI-based model provider."""

import logging
from typing import ClassVar, List, Optional

from .cli_base import CliProvider
from .registries.openai import OpenAIModelRegistry
from .registry_provider_mixin import RegistryBackedProviderMixin
from .shared import ModelCapabilities, ModelResponse, ProviderType
from .shared.cli_output import CliError, CliOutput, CliResponseParser

logger = logging.getLogger(__name__)


class CodexCliProvider(RegistryBackedProviderMixin, CliProvider):
    """OpenAI model provider using the Codex CLI binary.

    This provider executes the `codex` CLI command to generate content,
    bypassing the OpenAI SDK and allowing for containerized execution.

    CLI Usage:
        codex chat-completion --message "text" --model "gpt-4" --temperature 0.7
    """

    REGISTRY_CLASS = OpenAIModelRegistry
    MODEL_CAPABILITIES: ClassVar[dict[str, ModelCapabilities]] = {}

    def __init__(self, cli_path: str = "codex", timeout_s: int = 30, **kwargs):
        """Initialize Codex CLI provider.

        Args:
            cli_path: Path to codex binary (default: "codex")
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
        return ProviderType.OPENAI

    def _build_args(
        self,
        prompt: str,
        model: str,
        temperature: float = 0.7,
        max_output_tokens: Optional[int] = None,
        system_prompt: Optional[str] = None,
        **kwargs,
    ) -> List[str]:
        """Build CLI arguments for codex command.

        Args:
            prompt: User prompt text
            model: Model name (resolved)
            temperature: Sampling temperature (0.0-2.0)
            max_output_tokens: Max tokens to generate
            system_prompt: Optional system instructions
            **kwargs: Additional parameters (top_p, etc.)

        Returns:
            Command arguments: ["codex", "chat-completion", "--message", ..., "--model", ...]
        """
        args: List[str] = [self.cli_path, "chat-completion"]

        # Combine system and user prompts if both present
        if system_prompt:
            full_prompt = f"{system_prompt}\n\n{prompt}"
        else:
            full_prompt = prompt

        # Add message (required)
        args.extend(["--message", full_prompt])

        # Add model (required)
        args.extend(["--model", model])

        # Add temperature
        args.extend(["--temperature", str(temperature)])

        # Add max tokens if specified
        if max_output_tokens:
            args.extend(["--max-tokens", str(max_output_tokens)])

        # Add top_p if specified
        top_p = kwargs.get("top_p")
        if top_p is not None:
            args.extend(["--top-p", str(top_p)])

        # Add frequency_penalty if specified
        frequency_penalty = kwargs.get("frequency_penalty")
        if frequency_penalty is not None:
            args.extend(["--frequency-penalty", str(frequency_penalty)])

        # Add presence_penalty if specified
        presence_penalty = kwargs.get("presence_penalty")
        if presence_penalty is not None:
            args.extend(["--presence-penalty", str(presence_penalty)])

        logger.debug(f"Built Codex CLI args: {args[0:3]} ... (message hidden)")
        return args

    def _parse_response(self, output: CliOutput) -> ModelResponse:
        """Parse Codex CLI JSON output into ModelResponse.

        Expected JSON format:
        {
            "content": "response text",
            "usage": {
                "prompt_tokens": 100,
                "completion_tokens": 50,
                "total_tokens": 150
            },
            "model": "gpt-4",
            "finish_reason": "stop",
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
            raise CliError(f"Failed to parse Codex CLI response: {e}") from e

        # Extract required fields
        content = data.get("content", "")
        if not content:
            raise CliError("Codex CLI response missing 'content' field")

        # Extract model name
        model_name = data.get("model", "gpt-4-unknown")

        # Extract usage data (OpenAI uses prompt_tokens/completion_tokens)
        usage_data = data.get("usage", {})
        usage = {
            "input_tokens": usage_data.get("prompt_tokens", 0),
            "output_tokens": usage_data.get("completion_tokens", 0),
            "total_tokens": usage_data.get("total_tokens", 0),
        }

        # Extract metadata
        metadata = data.get("metadata", {})
        metadata.setdefault("finish_reason", data.get("finish_reason", "stop"))

        return ModelResponse(
            content=content,
            usage=usage,
            model_name=model_name,
            friendly_name="OpenAI (CLI)",
            provider=ProviderType.OPENAI,
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
        """Generate content using Codex CLI.

        Args:
            prompt: User prompt
            model_name: Model name (or alias)
            system_prompt: Optional system instructions
            temperature: Sampling temperature (0.0-2.0)
            max_output_tokens: Max tokens in response
            **kwargs: Additional parameters (top_p, etc.)

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
            raise RuntimeError(f"Codex CLI execution failed: {e}") from e

        # Check for non-zero exit
        if not output.success:
            raise RuntimeError(f"Codex CLI exited with code {output.exit_code}: {output.stderr}")

        # Parse response
        try:
            return self._parse_response(output)
        except CliError as e:
            raise RuntimeError(f"Failed to parse Codex CLI response: {e}") from e


# Ensure registry loads at import time
CodexCliProvider._ensure_registry()
