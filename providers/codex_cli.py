"""Codex (OpenAI) CLI-based model provider.

Shells out to the real ``codex`` binary in non-interactive ``exec`` mode using
``--json`` to receive structured JSONL events on stdout.

Real CLI invocation:
    codex exec --json --skip-git-repo-check [-m MODEL] "<prompt>"

Each line of stdout is a JSON event. We collect:
  - ``item.completed`` events with ``item.type == "agent_message"`` for content
  - ``turn.completed`` events for token usage
  - ``item.completed`` events with ``item.type == "error"`` for errors
"""

import json
import logging
from typing import ClassVar, Optional

from .cli_base import CliProvider
from .shared import ModelCapabilities, ModelResponse, ProviderType
from .shared.cli_output import CliError, CliOutput

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
        supports_streaming=False,
        supports_images=True,
        supports_function_calling=True,
        # Codex CLI does not honour temperature on the wire; it is controlled
        # by the bundled config and ChatGPT-account routing rules.
        supports_temperature=False,
    )


_CODEX_MODELS: dict[str, ModelCapabilities] = {
    "gpt-5.3-codex": _codex_caps(
        "gpt-5.3-codex",
        "GPT-5.3 Codex (CLI)",
        score=19,
        ctx=400_000,
        out=128_000,
        aliases=["codex", "gpt-codex", "default"],
    ),
    "gpt-5.1-codex": _codex_caps(
        "gpt-5.1-codex",
        "GPT-5.1 Codex (CLI)",
        score=18,
        ctx=400_000,
        out=128_000,
        aliases=["gpt-5.1", "gpt5.1-codex"],
    ),
    "gpt-5.1-codex-mini": _codex_caps(
        "gpt-5.1-codex-mini",
        "GPT-5.1 Codex Mini (CLI)",
        score=15,
        ctx=400_000,
        out=128_000,
        aliases=["codex-mini", "gpt-5.1-mini"],
    ),
}


class CodexCliProvider(CliProvider):
    """OpenAI model provider that shells out to the ``codex`` CLI binary."""

    MODEL_CAPABILITIES: ClassVar[dict[str, ModelCapabilities]] = _CODEX_MODELS

    def __init__(self, cli_path: str = "codex", timeout_s: int = 180, **kwargs):
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
        full_prompt = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt
        # codex exec --json --skip-git-repo-check -m MODEL PROMPT
        # --skip-git-repo-check avoids a "not in a git repo" prompt for non-repo CWDs.
        args = [self.cli_path, "exec", "--json", "--skip-git-repo-check", "-m", model, full_prompt]
        logger.debug("Built Codex CLI args: %s exec --json -m %s ... (prompt hidden)", self.cli_path, model)
        return args

    def _parse_response(self, output: CliOutput) -> ModelResponse:
        """Parse `codex exec --json` JSONL stream into a ModelResponse.

        The stream contains a sequence of events. We aggregate the final
        ``agent_message`` text and the ``turn.completed`` usage block.
        """
        agent_messages: list[str] = []
        usage_block: dict = {}
        errors: list[str] = []

        for raw_line in output.raw_output.splitlines():
            raw_line = raw_line.strip()
            if not raw_line:
                continue
            try:
                event = json.loads(raw_line)
            except json.JSONDecodeError:
                # Non-JSON noise in stdout — ignore.
                continue

            event_type = event.get("type")
            item = event.get("item") or {}

            if event_type == "item.completed" and item.get("type") == "agent_message":
                text = item.get("text") or ""
                if text:
                    agent_messages.append(text)
            elif event_type == "item.completed" and item.get("type") == "error":
                # These are usually deprecation warnings; collect for metadata.
                msg = item.get("message") or ""
                if msg:
                    errors.append(msg)
            elif event_type == "turn.completed":
                usage_block = event.get("usage") or {}

        if not agent_messages:
            raise CliError(
                "Codex CLI emitted no agent_message events. "
                f"Errors collected: {errors[:3] if errors else '(none)'}"
            )

        content = "\n\n".join(agent_messages)

        usage = {
            "input_tokens": usage_block.get("input_tokens", 0),
            "output_tokens": usage_block.get("output_tokens", 0),
            "total_tokens": (
                usage_block.get("input_tokens", 0)
                + usage_block.get("output_tokens", 0)
                + usage_block.get("reasoning_output_tokens", 0)
            ),
        }

        metadata = {
            "cached_input_tokens": usage_block.get("cached_input_tokens", 0),
            "reasoning_output_tokens": usage_block.get("reasoning_output_tokens", 0),
            "diagnostics": errors,
        }

        return ModelResponse(
            content=content,
            usage=usage,
            model_name="codex",
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
