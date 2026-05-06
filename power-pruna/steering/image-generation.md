# Image Generation Best Practices

## Tool: `generate_image`

### Prompt Composition

Build prompts with this structure:
1. **Subject** — what to generate (be specific)
2. **Style** — photography style, art style, or medium
3. **Lighting** — natural, studio, dramatic, soft
4. **Composition** — centered, rule of thirds, close-up, wide shot
5. **Quality modifiers** — "high resolution", "4k", "professional", "detailed"

### Aspect Ratios

Choose based on use case:
- `1:1` — social media posts, product photos, avatars
- `16:9` — blog headers, YouTube thumbnails, presentations
- `9:16` — Instagram stories, TikTok, mobile wallpapers
- `4:3` — standard photos, documents
- `3:2` — classic photography

### Model Selection for Images

| Model | Best for | Speed | Cost |
|-------|----------|-------|------|
| `p-image` | General purpose, fastest | ~1.5s | $0.005 |
| `flux-dev` | High quality, detailed | ~3s | $0.005 |
| `flux-2-klein-4b` | Cheapest, quick drafts | ~1s | $0.0001 |
| `qwen-image` | Complex scenes | ~4s | $0.025 |

### Examples

**Product photo:**
```
white leather sneakers on clean white studio background, professional product photography, soft studio lighting, centered composition, high resolution
```

**Blog header:**
```
sunset over mountain landscape, dramatic golden hour lighting, wide angle, cinematic composition, 4k photography
```

**Game concept art:**
```
medieval castle on floating island, fantasy RPG, concept art digital painting, dramatic lighting, Unreal Engine 5 quality
```

### Tips

- Always use English prompts — models respond better to English
- Be specific about what you DON'T want by describing what you DO want
- For consistent style across multiple images, reuse the same style/quality modifiers
- Use `seed` parameter for reproducible results when iterating on a prompt
