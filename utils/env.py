"""Centralized environment variable access for Mesh MCP Server."""

from __future__ import annotations

import logging
import os
import shutil
from collections.abc import Mapping
from contextlib import contextmanager
from pathlib import Path

try:
    from dotenv import dotenv_values, load_dotenv
except ImportError:  # pragma: no cover - optional dependency
    dotenv_values = None  # type: ignore[assignment]
    load_dotenv = None  # type: ignore[assignment]

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_ENV_PATH = _PROJECT_ROOT / ".env"

_DOTENV_VALUES: dict[str, str | None] = {}
_FORCE_ENV_OVERRIDE = False


def _read_dotenv_values() -> dict[str, str | None]:
    if dotenv_values is not None and _ENV_PATH.exists():
        loaded = dotenv_values(_ENV_PATH)
        return dict(loaded)
    return {}


def _compute_force_override(values: Mapping[str, str | None]) -> bool:
    raw = (values.get("MESH_MCP_FORCE_ENV_OVERRIDE") or "false").strip().lower()
    return raw == "true"


def reload_env(dotenv_mapping: Mapping[str, str | None] | None = None) -> None:
    """Reload .env values and recompute override semantics.

    Args:
        dotenv_mapping: Optional mapping used instead of reading the .env file.
            Intended for tests; when provided, load_dotenv is not invoked.
    """

    global _DOTENV_VALUES, _FORCE_ENV_OVERRIDE

    if dotenv_mapping is not None:
        _DOTENV_VALUES = dict(dotenv_mapping)
        _FORCE_ENV_OVERRIDE = _compute_force_override(_DOTENV_VALUES)
        return

    _DOTENV_VALUES = _read_dotenv_values()
    _FORCE_ENV_OVERRIDE = _compute_force_override(_DOTENV_VALUES)

    if load_dotenv is not None and _ENV_PATH.exists():
        load_dotenv(dotenv_path=_ENV_PATH, override=_FORCE_ENV_OVERRIDE)


reload_env()


def env_override_enabled() -> bool:
    """Return True when MESH_MCP_FORCE_ENV_OVERRIDE is enabled via the .env file."""

    return _FORCE_ENV_OVERRIDE


def get_env(key: str, default: str | None = None) -> str | None:
    """Retrieve environment variables respecting MESH_MCP_FORCE_ENV_OVERRIDE."""

    if env_override_enabled():
        if key in _DOTENV_VALUES:
            value = _DOTENV_VALUES[key]
            return value if value is not None else default
        return default

    return os.getenv(key, default)


def get_env_bool(key: str, default: bool = False) -> bool:
    """Boolean helper that respects override semantics."""

    raw_default = "true" if default else "false"
    raw_value = get_env(key, raw_default)
    return (raw_value or raw_default).strip().lower() == "true"


def get_all_env() -> dict[str, str | None]:
    """Expose the loaded .env mapping for diagnostics/logging."""

    return dict(_DOTENV_VALUES)


@contextmanager
def suppress_env_vars(*names: str):
    """Temporarily remove environment variables during the context.

    Args:
        names: Environment variable names to remove. Empty or falsy names are ignored.
    """

    removed: dict[str, str] = {}
    try:
        for name in names:
            if not name:
                continue
            if name in os.environ:
                removed[name] = os.environ[name]
                del os.environ[name]
        yield
    finally:
        for name, value in removed.items():
            os.environ[name] = value


def validate_cli_environment() -> dict[str, bool]:
    """Validate CLI tools availability and log results.

    Checks if CLI binaries are available in PATH:
    - gemini: Gemini CLI (from GEMINI_CLI_PATH or "gemini")
    - codex: OpenAI CLI (from CODEX_CLI_PATH or "codex")

    Returns:
        Dictionary mapping CLI name to availability (True = found, False = missing)
    """
    log = logging.getLogger(__name__)
    cli_paths = {
        "gemini": get_env("GEMINI_CLI_PATH", "gemini") or "gemini",
        "codex": get_env("CODEX_CLI_PATH", "codex") or "codex",
    }

    results = {}
    for cli_name, cli_path in cli_paths.items():
        if shutil.which(cli_path):
            results[cli_name] = True
            log.info(f"✓ {cli_name} CLI found: {cli_path}")
        else:
            results[cli_name] = False
            log.warning(f"✗ {cli_name} CLI not found at '{cli_path}', will use fallback")

    return results


def validate_provider_environment() -> dict[str, bool]:
    """Validate provider availability (API keys, CLI tools, etc.).

    Returns:
        Dictionary mapping provider name to availability
    """
    log = logging.getLogger(__name__)
    results = {}

    # Check OpenRouter
    openrouter_key = get_env("OPENROUTER_API_KEY")
    if openrouter_key:
        results["openrouter"] = True
        log.info("✓ OpenRouter API key configured")
    else:
        results["openrouter"] = False
        log.warning("✗ OpenRouter API key not set, will skip OpenRouter fallback")

    # Check CLI tools
    cli_results = validate_cli_environment()
    results.update(cli_results)

    return results
