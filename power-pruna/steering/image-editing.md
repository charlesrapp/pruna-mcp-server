# Image Editing Best Practices

## Tool: `edit_image`

### How It Works

Pass 1-5 reference images + a text instruction. The model modifies the images according to your prompt while preserving elements you don't mention.

### Prompt Structure

Be explicit about:
1. **What to change** — "transform the background into a beach scene"
2. **What to preserve** — "keep the person's face and clothing unchanged"
3. **Style direction** — "maintain photorealistic quality"

### Common Use Cases

**Background replacement:**
```
Replace the background with a clean white studio backdrop. Keep the subject unchanged.
```

**Style transfer:**
```
Transform into a watercolor painting style with vibrant colors. Preserve the composition and subject.
```

**Virtual staging (real estate):**
```
Furnish this empty living room in modern minimalist style. Add a sofa, coffee table, rug, and plants. Keep the room architecture, windows, and flooring unchanged.
```

**Product variation:**
```
Change the color of the sneakers to navy blue. Keep the same angle, lighting, and background.
```

### Tips

- The more specific your instruction, the better the result
- Use `aspect_ratio: "match_input_image"` (default) to keep original dimensions
- For multi-image edits, all images are used as context — useful for style consistency
- Upload local files directly — the server handles upload automatically
