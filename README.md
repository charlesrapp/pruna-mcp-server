# 🎨 pruna-mcp-server

[![CI](https://github.com/charlesrapp/pruna-mcp-server/actions/workflows/ci.yml/badge.svg)](https://github.com/charlesrapp/pruna-mcp-server/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/pruna-mcp-server)](https://pypi.org/project/pruna-mcp-server/)
[![Python](https://img.shields.io/pypi/pyversions/pruna-mcp-server)](https://pypi.org/project/pruna-mcp-server/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

MCP server for [Pruna AI](https://pruna.ai) — ultra-fast image generation, editing, upscaling, and video generation directly from your AI assistant.

[Pruna AI](https://pruna.ai) is an inference API specialized in image and video generation. It offers sub-2-second image generation starting at $0.005/image, with models for text-to-image, image editing, upscaling, and video generation. This MCP server wraps their API so any MCP-compatible client (Claude Desktop, Kiro, Cursor) can generate visual content natively.

Conforms to [MCP Specification 2025-11-25](https://modelcontextprotocol.io/specification/2025-11-25).

## Features

- **6 MCP Tools**: `generate_image`, `edit_image`, `upscale_image`, `generate_video`, `list_models`, `upload_file`
- **7 MCP Prompts**: Product photos, virtual staging, social media visuals, game concept art, ad creatives, video ads, image enhancement
- **2 MCP Resources**: `pruna://models` catalog for model discovery without tool calls
- **18 models**: 10 text-to-image, 3 editing, 1 upscale, 4 video
- **Smart sync/async**: Sync for fast image models, async with polling for video
- **Transparent file handling**: Pass local paths or URLs — auto-upload handled
- **Native MCP image return**: `ImageContent` blocks for clients that support inline display
- **Full MCP compliance**: Tool annotations, structured content, progress notifications

## Quick Start

```bash
# With uvx (zero install)
uvx pruna-mcp-server

# Or with pip
pip install pruna-mcp-server
pruna-mcp
```

Set your API key — get one at [pruna.ai](https://pruna.ai) (go to the [developer portal](https://docs.api.pruna.ai/) or [contact Pruna](https://pruna.ai/contact) to request access):

```bash
# macOS Keychain (recommended)
security add-generic-password -a $USER -s PRUNA_API_KEY -w "your-api-key"

# Or environment variable
export PRUNA_API_KEY="your-api-key"
```

## MCP Client Configuration

### Kiro CLI

Add to your agent config (e.g. `~/.kiro/agents/default.json`):

In `mcpServers`:
```json
"pruna": {
  "command": "sh",
  "args": ["-c", "PRUNA_API_KEY=$(security find-generic-password -a $USER -s PRUNA_API_KEY -w) uv run --directory /path/to/pruna-mcp-server pruna-mcp"],
  "autoApprove": ["generate_image", "edit_image", "upscale_image", "generate_video", "list_models", "upload_file"]
}
```

In `tools`, add: `"@pruna/*"`

In `allowedTools`, add: `"generate_image", "edit_image", "upscale_image", "generate_video", "list_models", "upload_file"`

> **Note**: Kiro agents use a `tools` whitelist with `@server-name/*` syntax and an `allowedTools` list. Both must include the Pruna tools for them to be available.

### Claude Desktop

Add to `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS):

```json
{
  "mcpServers": {
    "pruna": {
      "command": "sh",
      "args": ["-c", "PRUNA_API_KEY=$(security find-generic-password -a $USER -s PRUNA_API_KEY -w) /path/to/uv run --directory /path/to/pruna-mcp-server pruna-mcp"]
    }
  }
}
```

> **Important**: Use the full path to `uv` (e.g. `/Users/you/.local/bin/uv`) — Claude Desktop launches processes with a minimal PATH that doesn't include `~/.local/bin`.

> **Note**: Claude Desktop does not render `ImageContent` inline in the chat. The image is generated and saved locally — Claude will reference the file path in its response.

### Cursor

Add to `.cursor/mcp.json`:

```json
{
  "mcpServers": {
    "pruna": {
      "command": "uvx",
      "args": ["pruna-mcp-server"],
      "env": { "PRUNA_API_KEY": "your-api-key" }
    }
  }
}
```

## Tools

| Tool | Description | Pricing |
|------|-------------|---------|
| `generate_image` | Text-to-image with 10 models | From $0.0001/image |
| `edit_image` | Edit 1-5 images with text instructions | From $0.010/image |
| `upscale_image` | AI upscaling to 1-8 megapixels | From $0.005/image |
| `generate_video` | Text/image/audio to video | From $0.005/s |
| `list_models` | Browse all available models with pricing | Free |
| `upload_file` | Upload files for editing/video workflows | Free |

Image tools return both a JSON metadata block and a native MCP `ImageContent` block (base64, for images < 5MB).

## Prompts

Built-in workflow templates for common use cases:

| Prompt | Use Case | Example |
|--------|----------|---------|
| `product-photo` | E-commerce product shots | "white leather sneakers on clean background" |
| `virtual-staging` | Real estate room staging | Stage empty rooms with furniture |
| `social-media-visual` | Platform-optimized visuals | Auto aspect ratio per platform |
| `game-concept-art` | Game assets & environments | Characters, weapons, landscapes |
| `ad-creative` | Digital ads with text overlay | Headlines rendered in the image |
| `video-ad` | Short video ads | Talking heads, product demos |
| `image-enhance` | Upscale + enhance workflow | AI-generated image refinement |

## Configuration

| Environment Variable | Required | Default | Description |
|---------------------|----------|---------|-------------|
| `PRUNA_API_KEY` | ✅ | — | Your Pruna AI API key |
| `PRUNA_OUTPUT_DIR` | — | `./pruna-output` | Directory for downloaded files |
| `PRUNA_POLL_INTERVAL` | — | `2` | Seconds between async polls |
| `PRUNA_TIMEOUT` | — | `120` | HTTP timeout in seconds |
| `PRUNA_MAX_RETRIES` | — | `3` | Max retries on transient errors |

## Client Compatibility

| Client | Transport | Status | Notes |
|--------|-----------|--------|-------|
| Kiro CLI | STDIO | ✅ Tested | Requires `tools` + `allowedTools` config |
| Claude Desktop | STDIO | ✅ Tested | Use full path to `uv`; no inline image display |
| Cursor | STDIO | 🔲 Planned | — |
| Claude Code | STDIO | 🔲 Planned | — |

## Development

```bash
git clone https://github.com/charlesrapp/pruna-mcp-server.git
cd pruna-mcp-server
uv sync --extra dev

# Run tests (100 tests, 94% coverage)
uv run pytest --cov

# Lint & type check
uv run ruff check src/ tests/
uv run mypy src/
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

MIT — see [LICENSE](LICENSE).

<!-- mcp-name: io.github.charlesrapp/pruna -->
