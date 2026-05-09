# ListModels Tool - List Available Models

**Display all available AI models organized by provider**

The `listmodels` tool shows which providers are configured, available models, their aliases, context windows, and capabilities. This is useful for understanding what models can be used and their characteristics.

## Usage

```
"Use mesh to list available models"
```

## Key Features

- **Provider organization**: Shows all configured providers and their status
- **Model capabilities**: Context windows, thinking mode support, and special features
- **Alias mapping**: Shows shorthand names and their full model mappings
- **Configuration status**: Indicates which providers are available based on API keys
- **Context window information**: Helps you choose models based on your content size needs
- **Capability overview**: Understanding which models support extended thinking, vision, etc.

## Output Information

The tool displays:

**Provider Status:**
- Which providers are configured and available
- API key status (without revealing the actual keys)
- Provider priority order

**Model Details:**
- Full model names and their aliases
- Context window sizes (tokens)
- Special capabilities (thinking modes, vision support, etc.)
- Provider-specific features

**Capability Summary:**
- Which models support extended thinking
- Vision-capable models for image analysis
- Models with largest context windows
- Fastest models for quick tasks

## Example Output

```
# Available AI Models

## Gemini CLI ✅
**Status**: Configured and available

**Models**:
- `gemini-2.5-pro`     — 2M context, extended thinking
- `gemini-2.5-flash`   — 1M context, fast
- `gemini-2.5-flash-lite` — 1M context, lightweight

## Codex CLI ✅
**Status**: Configured and available

**Models**:
- `gpt-5.3-codex`      — 400K context (default)
- `gpt-5.1-codex`      — 400K context
- `gpt-5.1-codex-mini` — 400K context, cost-efficient

## OpenRouter ✅
**Status**: Configured and available

**Top models** (35 total in conf/openrouter_models.json):
- `opus`     → anthropic/claude-opus-4.5
- `sonnet`   → anthropic/claude-sonnet-4.5
- `pro`      → google/gemini-3-pro-preview
- `gpt-5.2`  → openai/gpt-5.2
- `grok`     → x-ai/grok-4
- `deepseek` → deepseek/deepseek-r1-0528
```

## When to Use ListModels

- **Model selection**: When you're unsure which models are available
- **Capability checking**: To verify what features each model supports
- **Configuration validation**: To confirm your API keys are working
- **Context planning**: To choose models based on content size requirements
- **Performance optimization**: To select the right model for speed vs quality trade-offs

## Configuration Dependencies

The available models depend on which backends are configured:

**Backends:**
- `gemini` CLI on PATH — Gemini Pro and Flash models
- `codex` CLI on PATH — GPT-5 / o3 / o4 family
- `OPENROUTER_API_KEY` in `.env` — fallback to any OpenRouter model

**Model Restrictions:**
If you've set model usage restrictions via environment variables, the tool will show:
- Which models are allowed vs restricted
- Active restriction policies
- How to modify restrictions

## Tool Parameters

This tool requires no parameters - it simply queries the server configuration and displays all available information.

## Best Practices

- **Check before planning**: Use this tool to understand your options before starting complex tasks
- **Verify configuration**: Confirm your API keys are working as expected
- **Choose appropriate models**: Match model capabilities to your specific needs
- **Understand limits**: Be aware of context windows when working with large files

## When to Use ListModels vs Other Tools

- **Use `listmodels`** for: Understanding available options and model capabilities
- **Use `chat`** for: General discussions about which model to use for specific tasks
- **Use `version`** for: Server configuration and version information
- **Use other tools** for: Actual analysis, debugging, or development work