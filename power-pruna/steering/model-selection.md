# Model Selection Guide

## Quick Decision Tree

**Need an image fast and cheap?** → `p-image` ($0.005, ~1.5s)
**Need the absolute cheapest?** → `flux-2-klein-4b` ($0.0001, ~1s)
**Need highest quality?** → `flux-dev` ($0.005, ~3s) or `qwen-image` ($0.025)
**Need to edit an existing image?** → `p-image-edit` ($0.01)
**Need to upscale?** → `p-image-upscale` ($0.005-0.01)
**Need video?** → `p-video` ($0.02-0.04/s)

## Cost Optimization

- For drafts/iterations: use `flux-2-klein-4b` at $0.0001 — iterate 50x for the price of one DALL-E image
- For final output: switch to `p-image` or `flux-dev`
- For batch generation: `p-image` has 500 req/min rate limit

## All Models

### Text-to-Image (10 models)
| Model | Price | Speed | Notes |
|-------|-------|-------|-------|
| p-image | $0.005 | ~1.5s | Default, best all-rounder |
| p-image-lora | $0.005 | ~1.5s | Custom LoRA support |
| flux-dev | $0.005 | ~3s | High quality |
| flux-dev-lora | $0.01 | ~3s | Flux + custom LoRA |
| flux-2-klein-4b | $0.0001 | ~1s | Ultra-cheap drafts |
| wan-image-small | $0.005 | ~2s | Fast, efficient |
| qwen-image | $0.025 | ~4s | Complex scenes |
| qwen-image-fast | $0.005 | ~2s | Faster Qwen |
| z-image-turbo | $0.005 | ~1.5s | Fast alternative |
| z-image-turbo-lora | $0.008 | ~1.5s | z-image + LoRA |

### Editing (3 models)
| Model | Price | Notes |
|-------|-------|-------|
| p-image-edit | $0.010 | Default editor, 1-5 images |
| p-image-edit-lora | $0.010 | Editor + custom LoRA |
| qwen-image-edit-plus | $0.03 | Advanced manipulation |

### Upscale (1 model)
| Model | Price | Notes |
|-------|-------|-------|
| p-image-upscale | $0.005-0.01 | 1-8 megapixels, detail/realism enhance |

### Video (4 models)
| Model | Price | Notes |
|-------|-------|-------|
| p-video | $0.02-0.04/s | Premium, text+image+audio input |
| wan-t2v | variable | Text-to-video only |
| wan-i2v | variable | Image-to-video |
| vace | variable | Character consistency |
