---
name: "pruna"
displayName: "Pruna AI — Image & Video Generation"
description: "Generate images, edit photos, upscale, and create videos directly in your workflow using Pruna AI's ultra-fast inference API"
keywords: ["image", "generate image", "photo", "picture", "visual", "video", "upscale", "edit image", "pruna", "illustration", "thumbnail", "banner", "hero image", "product photo", "concept art"]
author: "Charles Rapp"
---

# Onboarding

## Step 1: Validate API key

Before using Pruna AI tools, ensure you have a valid API key:
- Check if `PRUNA_API_KEY` is set in your environment or macOS Keychain
- If not, get one at https://docs.api.pruna.ai/ or contact https://pruna.ai/contact
- Store it securely:
  - macOS: `security add-generic-password -a $USER -s PRUNA_API_KEY -w "your-key"`
  - Other: `export PRUNA_API_KEY="your-key"`

## Step 2: Verify server is running

After installation, verify the MCP server is connected by asking: "list available Pruna models"

If the `list_models` tool responds with a model catalog, you're ready.

# When to Load Steering Files

- Generating images from text → `image-generation.md`
- Editing or modifying existing images → `image-editing.md`
- Creating videos → `video-generation.md`
- Choosing the right model or optimizing cost → `model-selection.md`
