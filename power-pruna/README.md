# 🎨 Pruna AI — Kiro Power

Generate images, edit photos, upscale, and create videos directly in your Kiro workflow using [Pruna AI](https://pruna.ai).

[![Install in Kiro](https://img.shields.io/badge/Install_in_Kiro-Open_Power_Config-blue?style=for-the-badge&logo=data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAyNCAyNCI+PHBhdGggZmlsbD0id2hpdGUiIGQ9Ik0xMyAzTDQgMTRoN2wtMSA3IDktMTFoLTdsMS03eiIvPjwvc3ZnPg==)](https://github.com/charlesrapp/pruna-mcp-server/tree/main/power-pruna)

> **To install:** In Kiro IDE → Powers panel → "Add power from GitHub" → paste `https://github.com/charlesrapp/pruna-mcp-server/tree/main/power-pruna`

## What it does

When you mention images, videos, or visuals in your conversation, Kiro automatically:
1. Activates the Pruna power
2. Starts the `pruna-mcp-server` MCP server
3. Loads relevant steering (prompting best practices, model selection)
4. Gives you access to 6 tools and 18 models

## Tools available

| Tool | Description | Cost |
|------|-------------|------|
| `generate_image` | Text-to-image, 10 models | From $0.0001 |
| `edit_image` | Edit 1-5 images with text | $0.01 |
| `upscale_image` | AI upscale to 8MP | $0.005 |
| `generate_video` | Text/image to video | $0.02-0.04/s |
| `list_models` | Browse catalog | Free |
| `upload_file` | Upload for editing | Free |

## Prerequisites

- [Pruna AI API key](https://docs.api.pruna.ai/) — store in env or macOS Keychain
- [uv](https://docs.astral.sh/uv/) installed (for `uvx`)

## Links

- [GitHub repo](https://github.com/charlesrapp/pruna-mcp-server)
- [PyPI](https://pypi.org/project/pruna-mcp-server/)
- [Pruna AI](https://pruna.ai)
