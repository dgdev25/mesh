"""Model provider abstractions for Mesh's CLI-first architecture."""

from .base import ModelProvider
from .codex_cli import CodexCliProvider
from .gemini_cli import GeminiCliProvider
from .openai_compatible import OpenAICompatibleProvider
from .openrouter import OpenRouterProvider
from .registry import ModelProviderRegistry
from .shared import ModelCapabilities, ModelResponse

__all__ = [
    "ModelProvider",
    "ModelResponse",
    "ModelCapabilities",
    "ModelProviderRegistry",
    "CodexCliProvider",
    "GeminiCliProvider",
    "OpenAICompatibleProvider",
    "OpenRouterProvider",
]
