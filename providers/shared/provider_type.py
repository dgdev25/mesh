"""Enumeration describing which backend owns a given model."""

from enum import Enum

__all__ = ["ProviderType"]


class ProviderType(Enum):
    """Canonical identifiers for every supported provider backend.

    Mesh uses a CLI-first architecture: the Gemini and Codex CLIs run as
    subprocesses, with OpenRouter as the only HTTP fallback.
    """

    GEMINI_CLI = "gemini_cli"
    CODEX_CLI = "codex_cli"
    OPENROUTER = "openrouter"
