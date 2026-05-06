# Video Generation Best Practices

## Tool: `generate_video`

### Prompt Structure

Follow Pruna's video prompting format:
1. **[Subject]** — describe the main subject
2. **[Action]** — what happens in the video
3. **[Camera]** — camera movement (pan, zoom, static, tracking)
4. **[Style]** — visual style and quality
5. **[Audio]** — optional, for speech or sound effects

### Model Selection

| Model | Best for | Input | Duration |
|-------|----------|-------|----------|
| `p-video` | Premium quality, all inputs | text + image + audio | 1-20s |
| `wan-t2v` | Text-to-video | text only | 1-20s |
| `wan-i2v` | Animate a static image | text + image | 1-20s |
| `vace` | Character consistency | text + image | 1-20s |

### Examples

**Product demo:**
```
[Subject]: A sleek smartphone on a marble surface
[Action]: The phone slowly rotates 360 degrees, screen lights up showing an app
[Camera]: Smooth orbit around the product
[Style]: Commercial quality, professional studio lighting, shallow depth of field
```

**Talking head (with image input):**
```
[Subject]: The person in the image
[Action]: Speaking naturally, slight head movements, friendly expression
[Camera]: Static medium shot
[Style]: Professional, well-lit, clean background
```

### Tips

- Video generation takes 30-60 seconds — the server polls automatically
- Use `image` parameter to animate a specific image (product, person, scene)
- Keep duration short (5s) for first iterations, increase once satisfied
- `720p` is faster and cheaper; use `1080p` for final output
- Always use `p-video` for best quality; `wan-t2v`/`wan-i2v` for budget runs
