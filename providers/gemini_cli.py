"""Gemini CLI-based model provider.

This provider executes the ``gemini`` binary as a subprocess. It does not use
a JSON capability registry — capabilities for the small handful of supported
Gemini models are declared inline below.
"""

import logging
from typing import ClassVar, Optional

from .cli_base import CliProvider
from .shared import ModelCapabilities, ModelResponse, ProviderType
from .shared.cli_output import CliError, CliOutput, CliResponseParser

logger = logging.getLogger(__name__)


def _gemini_caps(name: str, friendly: str, score: int, ctx: int, out: int, aliases: list[str]) -> ModelCapabilities:
    return ModelCapabilities(
        provider=ProviderType.GEMINI_CLI,
        model_name=name,
        friendly_name=friendly,
        intelligence_score=score,
        context_window=ctx,
        max_output_tokens=out,
        aliases=aliases,
        supports_streaming=False,  # CLI is request/response, no streaming
        supports_images=True,
        supports_extended_thinking=True,
        supports_function_calling=False,
    )


_GEMINI_MODELS: dict[str, ModelCapabilities] = {
    "gemini-2.5-pro": _gemini_caps(
        "gemini-2.5-pro",
        "Gemini 2.5 Pro (CLI)",
        score=18,
        ctx=2_000_000,
        out=65_536,
        aliases=["gemini-pro", "pro", "gemini2.5-pro"],
    ),
    "gemini-2.5-flash": _gemini_caps(
        "gemini-2.5-flash",
        "Gemini 2.5 Flash (CLI)",
        score=14,
        ctx=1_000_000,
        out=65_536,
        aliases=["gemini-flash", "flash", "gemini2.5-flash"],
    ),
    "gemini-2.5-flash-lite": _gemini_caps(
        "gemini-2.5-flash-lite",
        "Gemini 2.5 Flash Lite (CLI)",
        score=11,
        ctx=1_000_000,
        out=65_536,
        aliases=["flash-lite", "gemini-flash-lite"],
    ),
}


class GeminiCliProvider(CliProvider):
    """Gemini model provider that shells out to the ``gemini`` CLI binary."""

    MODEL_CAPABILITIES: ClassVar[dict[str, ModelCapabilities]] = _GEMINI_MODELS

    def __init__(self, cli_path: str = "gemini", timeout_s: int = 30, **kwargs):
        kwargs["api_key"] = "cli"
        super().__init__(cli_path=cli_path, timeout_s=timeout_s, **kwargs)

    def get_provider_type(self) -> ProviderType:
        return ProviderType.GEMINI_CLI

    def get_all_model_capabilities(self) -> dict[str, ModelCapabilities]:
        return self.MODEL_CAPABILITIES

    def _build_args(
        self,
        prompt: str,
        model: str,
        temperature: float = 0.7,
        max_output_tokens: Optional[int] = None,
        system_prompt: Optional[str] = None,
        **kwargs,
    ) -> list[str]:
        args: list[str] = [self.cli_path, "generate"]
        full_prompt = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt
        args.extend(["--prompt", full_prompt, "--model", model, "--temperature", str(temperature)])
        if max_output_tokens:
            args.extend(["--max-output-tokens", str(max_output_tokens)])
        thinking_mode = kwargs.get("thinking_mode")
        if thinking_mode:
            args.extend(["--thinking-mode", thinking_mode])
        logger.debug(f"Built Gemini CLI args: {args[0:3]} ... (prompt hidden)")
        return args

    def _parse_response(self, output: CliOutput) -> ModelResponse:
        CliResponseParser.validate_output(output, expected_format="json")
        try:
            data = CliResponseParser.parse_json(output.raw_output)
        except CliError as e:
            raise CliError(f"Failed to parse Gemini CLI response: {e}") from e

        content = data.get("content", "")
        if not content:
            raise CliError("Gemini CLI response missing 'content' field")

        usage_data = data.get("usage", {})
        usage = {
            "input_tokens": usage_data.get("input_tokens", 0),
            "output_tokens": usage_data.get("output_tokens", 0),
            "total_tokens": usage_data.get("total_tokens", 0),
        }

        metadata = data.get("metadata", {})
        metadata.setdefault("finish_reason", data.get("finish_reason", "STOP"))
        metadata.setdefault("is_blocked_by_safety", data.get("is_blocked_by_safety", False))
        metadata.setdefault("safety_feedback", data.get("safety_feedback"))

        return ModelResponse(
            content=content,
            usage=usage,
            model_name=data.get("model", "gemini-unknown"),
            friendly_name="Gemini (CLI)",
            provider=ProviderType.GEMINI_CLI,
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
        self.validate_parameters(model_name, temperature)
        resolved_model = self._resolve_model_name(model_name)

        args = self._build_args(
            prompt=prompt,
            model=resolved_model,
            temperature=temperature,
            max_output_tokens=max_output_tokens,
            system_prompt=system_prompt,
            **kwargs,
        )

        try:
            output = await self._run_cli(args)
        except Exception as e:
            raise RuntimeError(f"Gemini CLI execution failed: {e}") from e

        if not output.success:
            raise RuntimeError(f"Gemini CLI exited with code {output.exit_code}: {output.stderr}")

        try:
            return self._parse_response(output)
        except CliError as e:
            raise RuntimeError(f"Failed to parse Gemini CLI response: {e}") from e
