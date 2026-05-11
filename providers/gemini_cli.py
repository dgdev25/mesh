"""Gemini CLI-based model provider.

Shells out to the real ``gemini`` binary using ``-o json`` for structured output.

Real CLI invocation:
    gemini -p "<prompt>" -m <model> -o json

Output structure:
    {"session_id": "...", "response": "<text>", "stats": {"models": {...}}}
"""

import json
import logging
from typing import ClassVar

from .cli_base import CliProvider
from .shared import ModelCapabilities, ModelResponse, ProviderType
from .shared.cli_output import CliError, CliOutput

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
        supports_streaming=False,
        supports_images=True,
        supports_extended_thinking=True,
        supports_function_calling=False,
    )


_GEMINI_MODELS: dict[str, ModelCapabilities] = {
    "gemini-3-pro-preview": _gemini_caps(
        "gemini-3-pro-preview",
        "Gemini 3 Pro Preview (CLI)",
        score=19,
        ctx=1_048_576,
        out=65_536,
        aliases=[
            "pro",
            "gemini-pro",
            "gemini",
            "gemini3",
            "gemini-3",
            "google/gemini-3-pro-preview",
        ],
    ),
    "gemini-3-flash-preview": _gemini_caps(
        "gemini-3-flash-preview",
        "Gemini 3 Flash Preview (CLI)",
        score=15,
        ctx=1_048_576,
        out=65_536,
        aliases=[
            "flash3",
            "gemini-3-flash",
            "flash-3",
            "google/gemini-3-flash-preview",
        ],
    ),
    "gemini-2.5-pro": _gemini_caps(
        "gemini-2.5-pro",
        "Gemini 2.5 Pro (CLI)",
        score=18,
        ctx=2_000_000,
        out=65_536,
        aliases=["gemini-2.5", "gemini-2.5-pro", "gemini2.5-pro"],
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

    def __init__(self, cli_path: str = "gemini", timeout_s: int = 120, **kwargs):
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
        max_output_tokens: int | None = None,
        system_prompt: str | None = None,
        **kwargs,
    ) -> list[str]:
        full_prompt = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt
        # gemini CLI: -p prompt, -m model, -o json (structured output).
        # --temperature / --max-output-tokens are not exposed by the CLI; they
        # are controlled via gemini config files, so we omit them silently.
        args = [self.cli_path, "-p", full_prompt, "-m", model, "-o", "json"]
        logger.debug("Built Gemini CLI args: %s ... (prompt hidden)", args[0:1] + ["-p", "<hidden>", "-m", model, "-o", "json"])
        return args

    def _parse_response(self, output: CliOutput, requested_model: str | None = None) -> ModelResponse:
        """Parse `gemini -o json` output into a ModelResponse."""
        try:
            data = json.loads(output.raw_output)
        except json.JSONDecodeError as exc:
            raise CliError(f"Gemini CLI did not emit valid JSON: {exc}") from exc

        content = data.get("response", "")
        if not content:
            raise CliError("Gemini CLI response missing 'response' field")

        # Extract token usage from stats.models (first/only model).
        usage = {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}
        models_stats = data.get("stats", {}).get("models", {})
        if models_stats:
            first_model_stats = next(iter(models_stats.values()))
            tokens = first_model_stats.get("tokens", {})
            usage["input_tokens"] = tokens.get("prompt", tokens.get("input", 0))
            usage["output_tokens"] = tokens.get("candidates", 0)
            usage["total_tokens"] = tokens.get("total", 0)

        # Prefer the model name reported in CLI stats; fall back to the requested
        # model so telemetry reflects what the caller actually asked for instead
        # of an opaque sentinel string.
        fallback = requested_model or "gemini-unknown"
        model_name = next(iter(models_stats.keys()), fallback) if models_stats else fallback

        metadata = {
            "session_id": data.get("session_id"),
            "stats": data.get("stats"),
        }

        return ModelResponse(
            content=content,
            usage=usage,
            model_name=model_name,
            friendly_name="Gemini (CLI)",
            provider=ProviderType.GEMINI_CLI,
            metadata=metadata,
        )

    async def generate_content(
        self,
        prompt: str,
        model_name: str,
        system_prompt: str | None = None,
        temperature: float = 0.3,
        max_output_tokens: int | None = None,
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
            return self._parse_response(output, requested_model=resolved_model)
        except CliError as e:
            raise RuntimeError(f"Failed to parse Gemini CLI response: {e}") from e
