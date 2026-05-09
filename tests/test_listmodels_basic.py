"""Basic smoke tests for the listmodels tool after the CLI-first refactor."""

import json
import os
from unittest.mock import patch

import pytest
from mcp.types import TextContent

from tools.listmodels import ListModelsTool


@pytest.fixture
def tool():
    return ListModelsTool()


def test_tool_metadata(tool):
    assert tool.name == "listmodels"
    assert tool.get_request_model().__name__ == "ToolRequest"


@pytest.mark.asyncio
async def test_execute_with_no_providers(tool):
    """With no env vars and no CLIs detected, output reports all backends absent."""
    with patch.dict(os.environ, {"DEFAULT_MODEL": "auto"}, clear=True), \
         patch("shutil.which", return_value=None):
        result = await tool.execute({})
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        payload = json.loads(result[0].text)
        content = payload["content"]
        # All three backends should be reported, all unconfigured.
        assert "Gemini CLI" in content
        assert "Codex CLI" in content
        assert "OpenRouter" in content


@pytest.mark.asyncio
async def test_execute_with_openrouter_configured(tool):
    """OPENROUTER_API_KEY makes the OpenRouter backend show as configured."""
    env = {"OPENROUTER_API_KEY": "sk-or-test-fake", "DEFAULT_MODEL": "auto"}
    with patch.dict(os.environ, env, clear=True):
        result = await tool.execute({})
        payload = json.loads(result[0].text)
        content = payload["content"]
        assert "OpenRouter" in content
        # Configured marker (we don't pin to a specific glyph; just check the section
        # mentions OpenRouter and includes the 'Configured' word somewhere nearby).
        assert "Configured" in content


def test_model_category(tool):
    from tools.models import ToolModelCategory

    assert tool.get_model_category() == ToolModelCategory.FAST_RESPONSE
