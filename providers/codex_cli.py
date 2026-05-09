"""Codex (OpenAI) CLI-based model provider.

Executes the ``codex`` binary as a subprocess. Capabilities for supported
OpenAI models are declared inline; no JSON registry is loaded.
"""

import logging
from typing import ClassVar, Optional

from .cli_base import CliProvider
from .shared import ModelCapabilities, ModelResponse, ProviderType
from .shared.cli_output import CliError, CliOutput, CliResponseParser

logger = logging.getLogger(__name__)


def _codex_caps(name: str, friendly: str, score: int, ctx: int, out: int, aliases: list[str]) -> ModelCapabilities:
    return ModelCapabilities(
        provider=ProviderType.CODEX_CLI,
        model_name=name,
        friendly_name=friendly,
        intelligence_score=score,
        context_window=ctx,
        max_output_tokens=out,
        aliases=aliases,
        supports_streaming=False,  # CLI is request/response, no streaming
        supports_images=True,
        supports_function_calling=True,
    )


_CODEX_MODELS: dict[str, ModelCapabilities] = {
    "gpt-5": _codex_caps(
        "gpt-5",
        "GPT-5 (CLI)",
        score=18,
        ctx=400_000,
        out=128_000,
        aliases=["gpt5"],
    ),
    "gpt-5.2": _codex_caps(
        "gpt-5.2",
        "GPT-5.2 (CLI)",
        score=19,
        ctx=400_000,
        out=128_000,
        aliases=["gpt5.2"],
    ),
    "o3": _codex_caps(
        "o3",
        "OpenAI o3 (CLI)",
        score=18,
        ctx=200_000,
        out=100_000,
        aliases=[],
    ),
    "o3-mini": _codex_caps(
        "o3-mini",
        "OpenAI o3-mini (CLI)",
        score=14,
        ctx=200_000,
        out=100_000,
        aliases=["o3mini"],
    ),
    "o4-mini": _codex_caps(
        "o4-mini",
        "OpenAI o4-mini (CLI)",
        score=15,
        ctx=200_000,
        out=100_000,
        aliases=["o4mini"],
    ),
}


class CodexCliProvider(CliProvider):
    """OpenAI model provider that shells out to the ``codex`` CLI binary."""

    MODEL_CAPABILITIES: ClassVar[dict[str, ModelCapabilities]] = _CODEX_MODELS

    def __init__(self, cli_path: str = "codex", timeout_s: int = 30, **kwargs):
        kwargs["api_key"] = "cli"
        super().__init__(cli_path=cli_path, timeout_s=timeout_s, **kwargs)

    def get_provider_type(self) -> ProviderType:
        return ProviderType.CODEX_CLI

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
        args: list[str] = [self.cli_path, "chat-completion"]
        full_prompt = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt
        args.extend(["--message", full_prompt, "--model", model, "--temperature", str(temperature)])
        if max_output_tokens:
            args.extend(["--max-tokens", str(max_output_tokens)])
        for opt, flag in (("top_p", "--top-p"), ("frequency_penalty", "--frequency-penalty"), ("presence_penalty", "--presence-penalty")):
            value = kwargs.get(opt)
            if value is not None:
                args.extend([flag, str(value)])
        logger.debug(f"Built Codex CLI args: {args[0:3]} ... (message hidden)")
        return args

    def _parse_response(self, output: CliOutput) -> ModelResponse:
        CliResponseParser.validate_output(output, expected_format="json")
        try:
            data = CliResponseParser.parse_json(output.raw_output)
        except CliError as e:
            raise CliError(f"Failed to parse Codex CLI response: {e}") from e

        content = data.get("content", "")
        if not content:
            raise CliError("Codex CLI response missing 'content' field")

        usage_data = data.get("usage", {})
        usage = {
            "input_tokens": usage_data.get("prompt_tokens", 0),
            "output_tokens": usage_data.get("completion_tokens", 0),
            "total_tokens": usage_data.get("total_tokens", 0),
        }

        metadata = data.get("metadata", {})
        metadata.setdefault("finish_reason", data.get("finish_reason", "stop"))

        return ModelResponse(
            content=content,
            usage=usage,
            model_name=data.get("model", "gpt-unknown"),
            friendly_name="OpenAI (CLI)",
            provider=ProviderType.CODEX_CLI,
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
            raise RuntimeError(f"Codex CLI execution failed: {e}") from e

        if not output.success:
            raise RuntimeError(f"Codex CLI exited with code {output.exit_code}: {output.stderr}")

        try:
            return self._parse_response(output)
        except CliError as e:
            raise RuntimeError(f"Failed to parse Codex CLI response: {e}") from e
