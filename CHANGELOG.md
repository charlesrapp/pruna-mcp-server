# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/).

## [0.1.0] - 2026-04-13

### Added
- 6 MCP tools: `generate_image`, `edit_image`, `upscale_image`, `generate_video`, `list_models`, `upload_file`
- 7 MCP prompts: `product-photo`, `virtual-staging`, `social-media-visual`, `game-concept-art`, `ad-creative`, `video-ad`, `image-enhance`
- 2 MCP resources: `pruna://models`, `pruna://models/{model_id}`
- 18-model static registry with pricing and rate limits
- Pruna API client with exponential backoff retry (429, 502-504)
- Smart sync/async: sync for image models, async polling for video
- Transparent file handling: local paths auto-uploaded via `/v1/files`
- Native MCP `ImageContent` return for inline display in compatible clients
- MCP tool annotations (title, readOnlyHint, destructiveHint, idempotentHint, openWorldHint)
- Path traversal protection on file upload/download
- URL validation on Pruna delivery URLs
- API key protection (never logged, never in results)
- Configurable output directory, poll interval, timeout, max retries
- Sync-to-async fallback: image tools automatically retry via async polling on sync timeout
- Progress notifications via `ctx.report_progress()` during async polling
- Structured logging via Python `logging` module on all tool invocations
- 100 tests, 94% coverage
- CI/CD: GitHub Actions (ruff, mypy strict, pytest, build, PyPI publish)
- Dockerfile for containerized deployment
- macOS Keychain integration for API key storage
