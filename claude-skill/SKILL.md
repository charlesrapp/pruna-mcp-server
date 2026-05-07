---
name: pruna
description: Generate images, edit photos, upscale, and create videos using Pruna AI. Use when the user asks to create, generate, or edit an image or video, or mentions visuals, thumbnails, banners, illustrations, or product photos.
when_to_use: "Trigger phrases: generate image, create image, make a picture, edit photo, upscale, generate video, product photo, concept art, thumbnail, banner, hero image, illustration"
allowed-tools: Bash(uvx pruna-mcp-server *) mcp__pruna__generate_image mcp__pruna__edit_image mcp__pruna__upscale_image mcp__pruna__generate_video mcp__pruna__list_models mcp__pruna__upload_file
---

# Pruna AI — Image & Video Generation

Generate images, edit photos, upscale, and create videos directly from Claude Code using Pruna AI's ultra-fast inference API.

## Setup

Ensure `PRUNA_API_KEY` is set:
```bash
# macOS Keychain
export PRUNA_API_KEY=$(security find-generic-password -a $USER -s PRUNA_API_KEY -w)
# Or set directly
export PRUNA_API_KEY="your-key"
```

The MCP server must be configured in `.claude/settings.local.json`:
```json
{
  "mcpServers": {
    "pruna": {
      "command": "uvx",
      "args": ["pruna-mcp-server"],
      "env": { "PRUNA_API_KEY": "${PRUNA_API_KEY}" }
    }
  }
}
```

## Image Generation

Use `generate_image` with these guidelines:

**Prompt structure:** Subject + Style + Lighting + Composition + Quality modifiers

**Aspect ratios:**
- `1:1` — social media, product photos
- `16:9` — blog headers, YouTube thumbnails
- `9:16` — stories, TikTok, mobile
- `4:3` — standard photos

**Model selection:**
- `p-image` — default, fastest (~1.5s, $0.005)
- `flux-dev` — highest quality (~3s, $0.005)
- `flux-2-klein-4b` — cheapest drafts (~1s, $0.0001)

Always use English prompts. Use `seed` for reproducible results when iterating.

## Image Editing

Use `edit_image` with 1-5 reference images + text instruction.

Be explicit about what to change AND what to preserve. Default `aspect_ratio: "match_input_image"`.

## Video Generation

Use `generate_video` with prompt structure: [Subject] + [Action] + [Camera] + [Style]

- `p-video` — premium quality, supports image+audio input ($0.02-0.04/s)
- `wan-t2v` — text-to-video only
- `wan-i2v` — animate a static image

Keep duration short (5s) for iterations. Use `720p` for drafts, `1080p` for final.

## Upscaling

Use `upscale_image` with `target` 1-8 megapixels. Set `enhance_realism=true` for AI-generated images.
