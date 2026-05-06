# pruna-mcp-server — Specification

> MCP server for [Pruna AI](https://pruna.ai) — Image generation, editing, upscaling, and video generation.
>
> Conforms to [MCP Specification 2025-11-25](https://modelcontextprotocol.io/specification/2025-11-25).

## 1. Overview

### 1.1 Problem

There is no MCP server for Pruna AI. Pruna offers ultra-fast, cost-effective image and video generation through a simple REST API (17 models, $0.005/image). Integrating it as an MCP server makes these capabilities available to any MCP-compatible client (Kiro, Claude Desktop, Cursor, etc.).

### 1.2 Goals

- Expose all Pruna AI capabilities as MCP tools with full spec compliance (annotations, structured content, progress)
- Provide MCP Prompts for common industry workflows (e-commerce, social media, gaming, real estate)
- Publish on PyPI as `pruna-mcp-server` (installable via `uvx`)
- Production-quality: typed, tested, documented, CI/CD
- Support both sync and async Pruna API workflows
- Download generated files locally with configurable output directory
- Return image content inline (base64) for MCP clients that support it

### 1.3 Non-Goals

- Web UI or HTTP/SSE transport (STDIO only for v1)
- LoRA training workflows (async-only, long-running — deferred to v2)

## 2. Pruna API Surface

Base URL: `https://api.pruna.ai`
Auth: `apikey` header on all requests.

### 2.1 Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/v1/predictions` | Submit generation request |
| `GET` | `/v1/predictions/status/{id}` | Poll prediction status (async) |
| `GET` | `/v1/predictions/delivery/{path}` | Download generated content |
| `POST` | `/v1/files` | Upload a file (for editing/upscaling/i2v) |

### 2.2 Models by Category

**Text-to-Image (10 models):**
`p-image`, `p-image-lora`, `flux-dev`, `flux-dev-lora`, `flux-2-klein-4b`, `wan-image-small`, `qwen-image`, `qwen-image-fast`, `z-image-turbo`, `z-image-turbo-lora`

**Image Editing (3 models):**
`p-image-edit`, `p-image-edit-lora`, `qwen-image-edit-plus`

**Image Upscaling (1 model):**
`p-image-upscale`

**Video Generation (4 models):**
`p-video`, `wan-t2v`, `wan-i2v`, `vace`

### 2.3 Sync vs Async

- **Sync** (`Try-Sync: true`): Waits up to 60s, returns `generation_url` directly. Best for fast image models.
- **Async** (default): Returns `get_url` for polling. Required for video and complex edits.

The server handles both transparently: sync for image models, async with polling for video models.

## 3. MCP Server Capabilities

The server declares the following MCP capabilities at initialization:

```json
{
  "capabilities": {
    "tools": { "listChanged": false },
    "resources": { "subscribe": false, "listChanged": false },
    "prompts": { "listChanged": false }
  }
}
```

## 4. MCP Tools

### 4.1 Tool Annotations

Every tool declares [MCP annotations](https://modelcontextprotocol.io/specification/2025-11-25/server/tools) to help clients determine confirmation behavior and trust level.

| Tool | `title` | `readOnlyHint` | `destructiveHint` | `idempotentHint` | `openWorldHint` | `costHint` |
|------|---------|----------------|--------------------|--------------------|------------------|------------|
| `generate_image` | Image Generation (Pruna AI) | `false` | `false` | `false` | `true` | `low` |
| `edit_image` | Image Editing (Pruna AI) | `false` | `false` | `false` | `true` | `low` |
| `upscale_image` | Image Upscaling (Pruna AI) | `false` | `false` | `true` | `true` | `low` |
| `generate_video` | Video Generation (Pruna AI) | `false` | `false` | `false` | `true` | `medium` |
| `list_models` | List Pruna AI Models | `true` | `false` | `true` | `false` | `none` |
| `upload_file` | Upload File to Pruna AI | `false` | `false` | `true` | `true` | `none` |

Rationale:
- All generation tools are `openWorldHint: true` (network calls to Pruna API)
- `list_models` is `readOnlyHint: true` (pure local data, no API call)
- `generate_video` is `costHint: medium` (higher price per generation than images)
- `upscale_image` and `upload_file` are `idempotentHint: true` (same input → same output)

### 4.2 `generate_image`

Generate an image from a text prompt.

**Input Parameters:**

| Parameter | Type | Required | Default | Constraints | Description |
|-----------|------|----------|---------|-------------|-------------|
| `prompt` | `str` | ✅ | — | min 1 char | Text description of the image |
| `model` | `str` | — | `p-image` | enum: see §2.2 text-to-image | Model to use |
| `aspect_ratio` | `str` | — | `16:9` | enum: `1:1`, `16:9`, `9:16`, `4:3`, `3:4`, `3:2`, `2:3`, `custom` | Output aspect ratio |
| `width` | `int` | — | — | 256-1440, multiple of 16 | Custom width. Only when `aspect_ratio=custom` |
| `height` | `int` | — | — | 256-1440, multiple of 16 | Custom height. Only when `aspect_ratio=custom` |
| `seed` | `int` | — | random | ≥ 0 | For reproducible generation |

**Output Schema:**

```json
{
  "type": "object",
  "properties": {
    "file_path":          { "type": "string", "description": "Local path to the downloaded image" },
    "model":              { "type": "string", "description": "Model used for generation" },
    "width":              { "type": "integer" },
    "height":             { "type": "integer" },
    "seed":               { "type": "integer", "description": "Seed used (for reproducibility)" },
    "generation_time_ms": { "type": "integer", "description": "Server-side generation time" }
  },
  "required": ["file_path", "model"]
}
```

**Return content:** The tool returns a list of MCP content blocks:
1. `TextContent` — JSON string with metadata (file_path, model, timing, seed)
2. `ImageContent` — base64-encoded image with mimeType (for images < 5MB)

### 4.3 `edit_image`

Edit one or more images with text instructions.

**Input Parameters:**

| Parameter | Type | Required | Default | Constraints | Description |
|-----------|------|----------|---------|-------------|-------------|
| `prompt` | `str` | ✅ | — | min 1 char | Edit instruction |
| `images` | `list[str]` | ✅ | — | 1-5 items, each URL or local path | Image URLs or local file paths |
| `model` | `str` | — | `p-image-edit` | enum: see §2.2 editing | Model to use |
| `aspect_ratio` | `str` | — | `match_input_image` | enum: `match_input_image`, `1:1`, `16:9`, `9:16`, `4:3`, `3:4`, `3:2`, `2:3` | Output aspect ratio |
| `seed` | `int` | — | — | ≥ 0 | For reproducible generation |

When local file paths are provided, the server uploads them via `/v1/files` first.

**Output Schema:**

```json
{
  "type": "object",
  "properties": {
    "file_path":          { "type": "string", "description": "Local path to the edited image" },
    "model":              { "type": "string" },
    "source_images":      { "type": "integer", "description": "Number of input images used" },
    "generation_time_ms": { "type": "integer" }
  },
  "required": ["file_path", "model"]
}
```

**Return content:** `TextContent` (JSON metadata) + `ImageContent` (base64) — same pattern as `generate_image`.

### 4.4 `upscale_image`

Upscale an image using AI.

**Input Parameters:**

| Parameter | Type | Required | Default | Constraints | Description |
|-----------|------|----------|---------|-------------|-------------|
| `image` | `str` | ✅ | — | URL or local path | Image to upscale |
| `target` | `int` | — | `4` | 1-8 | Target resolution in megapixels |
| `output_format` | `str` | — | `jpg` | enum: `webp`, `jpg`, `png` | Output format |
| `enhance_details` | `bool` | — | `false` | — | Enhance fine textures |
| `enhance_realism` | `bool` | — | `false` | — | Improve realism (recommended for AI-generated images) |

**Output Schema:**

```json
{
  "type": "object",
  "properties": {
    "file_path":          { "type": "string" },
    "target_mp":          { "type": "integer", "description": "Target megapixels" },
    "output_format":      { "type": "string" },
    "generation_time_ms": { "type": "integer" }
  },
  "required": ["file_path", "target_mp", "output_format"]
}
```

**Return content:** `TextContent` (JSON metadata) + `ImageContent` (base64).

### 4.5 `generate_video`

Generate a video from text, image, or audio.

**Input Parameters:**

| Parameter | Type | Required | Default | Constraints | Description |
|-----------|------|----------|---------|-------------|-------------|
| `prompt` | `str` | ✅ | — | min 1 char | Text prompt for video generation |
| `model` | `str` | — | `p-video` | enum: `p-video`, `wan-t2v`, `wan-i2v`, `vace` | Model to use |
| `image` | `str` | — | — | URL or local path | Input image (for image-to-video) |
| `audio` | `str` | — | — | URL or local path | Input audio (for audio-conditioned video) |
| `duration` | `int` | — | `5` | 1-20 | Duration in seconds |
| `resolution` | `str` | — | `720p` | enum: `720p`, `1080p` | Video resolution |
| `aspect_ratio` | `str` | — | `16:9` | enum: `16:9`, `9:16`, `4:3`, `3:4`, `3:2`, `2:3`, `1:1` | Ignored when input image is provided |
| `fps` | `int` | — | `24` | enum: `24`, `48` | Frames per second |
| `seed` | `int` | — | random | ≥ 0 | For reproducible generation |

Always uses async workflow with polling. Emits MCP progress notifications during polling (see §7.7).

**Output Schema:**

```json
{
  "type": "object",
  "properties": {
    "file_path":          { "type": "string", "description": "Local path to the downloaded video" },
    "model":              { "type": "string" },
    "duration":           { "type": "integer", "description": "Actual video duration in seconds" },
    "resolution":         { "type": "string" },
    "generation_time_ms": { "type": "integer" }
  },
  "required": ["file_path", "model"]
}
```

**Return content:** `TextContent` with JSON metadata only (no inline video — too large for base64).

### 4.6 `list_models`

List available Pruna models with their capabilities and pricing.

**Input Parameters:**

| Parameter | Type | Required | Default | Constraints | Description |
|-----------|------|----------|---------|-------------|-------------|
| `category` | `str` | — | — | enum: `image`, `editing`, `upscale`, `video` | Filter by category |

**Output Schema:**

```json
{
  "type": "object",
  "properties": {
    "models": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "name":        { "type": "string" },
          "category":    { "type": "string" },
          "description": { "type": "string" },
          "pricing":     { "type": "string" },
          "rate_limit":  { "type": "string" }
        },
        "required": ["name", "category", "pricing"]
      }
    },
    "count": { "type": "integer" }
  },
  "required": ["models", "count"]
}
```

**Return content:** `TextContent` with formatted model table.

### 4.7 `upload_file`

Upload a local file to Pruna for use in editing/video workflows.

**Input Parameters:**

| Parameter | Type | Required | Default | Constraints | Description |
|-----------|------|----------|---------|-------------|-------------|
| `file_path` | `str` | ✅ | — | Must exist, max 20MB | Local file path to upload |

**Output Schema:**

```json
{
  "type": "object",
  "properties": {
    "url":          { "type": "string", "description": "Temporary Pruna file URL" },
    "file_id":      { "type": "string" },
    "content_type": { "type": "string" },
    "size_bytes":   { "type": "integer" },
    "expires_at":   { "type": "string", "format": "date-time" }
  },
  "required": ["url", "file_id"]
}
```

## 5. MCP Resources

The server exposes read-only resources for model discovery without consuming tool calls.

### 5.1 Resource List

| URI | Name | Description | MIME Type |
|-----|------|-------------|-----------|
| `pruna://models` | Pruna AI Models | Complete model catalog with pricing and capabilities | `application/json` |
| `pruna://models/{model_id}` | Model Details | Detailed info for a specific model (parameters, constraints, examples) | `application/json` |

### 5.2 Resource Schema

`pruna://models` returns:

```json
{
  "models": [
    {
      "name": "p-image",
      "category": "text-to-image",
      "description": "Ultra-fast text-to-image generation by Pruna",
      "pricing": "$0.005/image",
      "rate_limit": "500/min",
      "supports_sync": true,
      "parameters": ["prompt", "aspect_ratio", "width", "height", "seed"]
    }
  ]
}
```

`pruna://models/{model_id}` returns the same object for a single model, plus:
- `example_prompts`: array of example prompts
- `parameter_details`: full parameter constraints (types, ranges, enums)

Resources are served from the static model registry — no API calls to Pruna.

## 6. MCP Prompts

The server exposes reusable prompt templates for common Pruna use cases. These are discoverable via `prompts/list` and invokable via `prompts/get`. They guide the LLM through structured workflows aligned with Pruna's key industry verticals.

### 6.1 Prompt List

| Name | Description | Arguments |
|------|-------------|-----------|
| `product-photo` | Generate an e-commerce product photo on a clean background | `product`, `background`, `style` |
| `virtual-staging` | Stage an empty room with furniture and decor | `room_image`, `style`, `room_type` |
| `social-media-visual` | Create a visual optimized for a specific social platform | `topic`, `platform`, `tone` |
| `game-concept-art` | Generate game concept art (characters, environments, items) | `subject`, `game_genre`, `art_style` |
| `ad-creative` | Create a digital advertising visual with text overlay | `product`, `headline`, `target_audience` |
| `video-ad` | Generate a short video ad from a product image | `product_image`, `script`, `duration` |
| `image-enhance` | Multi-step workflow: upscale + enhance an AI-generated image | `image`, `target_mp` |

### 6.2 Prompt Details

#### `product-photo`

**Use case:** E-commerce / Retail Media — Pruna's Looties case study shows AI-powered marketplace listings with product photos. Virtual try-on is a key demo on pruna.ai.

**Arguments:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `product` | `str` | ✅ | Product description (e.g., "white leather sneakers", "ceramic coffee mug") |
| `background` | `str` | — | Background description (default: "clean white studio background") |
| `style` | `str` | — | Photography style (default: "professional product photography, soft studio lighting") |

**Generated messages:**

```json
[
  {
    "role": "user",
    "content": {
      "type": "text",
      "text": "Generate a product photo using Pruna AI.\n\nProduct: {product}\nBackground: {background}\nStyle: {style}\n\nUse the generate_image tool with model p-image, aspect_ratio 1:1. Compose the prompt as: '{product}, {background}, {style}, high resolution, commercial photography, centered composition'."
    }
  }
]
```

#### `virtual-staging`

**Use case:** Real Estate — Pruna demos include a virtual staging playground. p-image-edit can transform empty rooms into furnished spaces.

**Arguments:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `room_image` | `str` | ✅ | Path or URL to the empty room photo |
| `style` | `str` | — | Interior design style (default: "modern minimalist") |
| `room_type` | `str` | — | Room type (default: "living room") |

**Generated messages:**

```json
[
  {
    "role": "user",
    "content": {
      "type": "text",
      "text": "Stage this empty room using Pruna AI.\n\nRoom image: {room_image}\nStyle: {style}\nRoom type: {room_type}\n\nUse the edit_image tool with model p-image-edit. Prompt: 'Furnish this empty {room_type} in {style} style. Add appropriate furniture, decor, rugs, and lighting. Keep the room architecture, windows, and flooring unchanged.'"
    }
  }
]
```

#### `social-media-visual`

**Use case:** Digital Ads — Pruna highlights social ads as a key vertical for both p-image and p-video. Platform-specific aspect ratios are critical.

**Arguments:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `topic` | `str` | ✅ | Visual subject or campaign topic |
| `platform` | `str` | — | Target platform (default: "instagram"). Determines aspect ratio: instagram→1:1, story→9:16, youtube→16:9, linkedin→4:3 |
| `tone` | `str` | — | Visual tone (default: "vibrant and eye-catching") |

**Generated messages:**

```json
[
  {
    "role": "user",
    "content": {
      "type": "text",
      "text": "Create a social media visual using Pruna AI.\n\nTopic: {topic}\nPlatform: {platform}\nTone: {tone}\n\nUse the generate_image tool with model p-image. Set aspect_ratio based on platform (instagram→1:1, story/reels/tiktok→9:16, youtube/linkedin→16:9). Compose the prompt as: '{topic}, {tone}, social media visual, bold colors, clean composition, trending aesthetic'."
    }
  }
]
```

#### `game-concept-art`

**Use case:** Gaming — Pruna showcases gaming as a primary vertical with examples like "Cinematic screenshot from a third-person action RPG, Unreal Engine 5 render" and "female mage in a swamp at twilight".

**Arguments:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `subject` | `str` | ✅ | What to generate (character, environment, weapon, creature, etc.) |
| `game_genre` | `str` | — | Game genre (default: "fantasy RPG") |
| `art_style` | `str` | — | Art style (default: "concept art, digital painting") |

**Generated messages:**

```json
[
  {
    "role": "user",
    "content": {
      "type": "text",
      "text": "Generate game concept art using Pruna AI.\n\nSubject: {subject}\nGenre: {game_genre}\nArt style: {art_style}\n\nUse the generate_image tool with model p-image, aspect_ratio 16:9. Compose the prompt as: '{subject}, {game_genre} game, {art_style}, highly detailed, dramatic lighting, cinematic composition, Unreal Engine 5 quality'."
    }
  }
]
```

#### `ad-creative`

**Use case:** Digital Advertising — Pruna highlights text rendering as a key capability ("Precise, styled text rendering without misspelling"). p-image excels at generating visuals with embedded text for ads.

**Arguments:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `product` | `str` | ✅ | Product or brand to advertise |
| `headline` | `str` | ✅ | Ad headline text to render on the image |
| `target_audience` | `str` | — | Target audience (default: "general consumer") |

**Generated messages:**

```json
[
  {
    "role": "user",
    "content": {
      "type": "text",
      "text": "Create a digital ad creative using Pruna AI.\n\nProduct: {product}\nHeadline: \"{headline}\"\nAudience: {target_audience}\n\nUse the generate_image tool with model p-image, aspect_ratio 1:1 (or 9:16 for stories). Compose the prompt as: 'Professional advertisement for {product}, bold text reading \"{headline}\", appealing to {target_audience}, clean modern design, vibrant colors, commercial quality'. P-image has strong text rendering — the headline should appear correctly in the image."
    }
  }
]
```

#### `video-ad`

**Use case:** Video Ads — Pruna's p-video page showcases social ads with talking heads: "The woman says: Find the house that's perfect for you" and product videos with camera motion.

**Arguments:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `product_image` | `str` | ✅ | Path or URL to the product/person image |
| `script` | `str` | ✅ | What happens in the video (action, speech, camera movement) |
| `duration` | `int` | — | Video duration in seconds (default: 5) |

**Generated messages:**

```json
[
  {
    "role": "user",
    "content": {
      "type": "text",
      "text": "Create a video ad using Pruna AI.\n\nProduct image: {product_image}\nScript: {script}\nDuration: {duration}s\n\nUse the generate_video tool with model p-video, the provided image, and duration. Compose the prompt following Pruna's video prompting structure:\n- [Subject]: describe the subject from the image\n- [Action]: {script}\n- [Camera]: appropriate camera movement\n- [Style]: commercial quality, professional lighting\n- [Audio]: include speech if the script contains dialogue"
    }
  }
]
```

#### `image-enhance`

**Use case:** Image Enhancement — Multi-step workflow combining generation and upscaling. Pruna's Scenario case study highlights upscaling as a key production step.

**Arguments:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `image` | `str` | ✅ | Path or URL to the image to enhance |
| `target_mp` | `int` | — | Target megapixels (default: 4) |

**Generated messages:**

```json
[
  {
    "role": "user",
    "content": {
      "type": "text",
      "text": "Enhance this image using Pruna AI.\n\nImage: {image}\nTarget: {target_mp} megapixels\n\nUse the upscale_image tool with model p-image-upscale, target={target_mp}, enhance_details=true, enhance_realism=true, output_format=png. This will upscale the image and enhance both fine details and realism."
    }
  }
]
```

## 7. Architecture

### 7.1 Project Structure

```
pruna-mcp-server/
├── src/
│   └── pruna_mcp_server/
│       ├── __init__.py          # Version (__version__)
│       ├── __main__.py          # Entry point (python -m pruna_mcp_server)
│       ├── server.py            # MCP server, tool + resource + prompt definitions
│       ├── client.py            # Pruna API client (httpx async)
│       ├── models.py            # Model registry + metadata
│       ├── prompts.py           # MCP prompt templates
│       ├── config.py            # Configuration (env vars, validation)
│       └── py.typed             # PEP 561 marker
├── tests/
│   ├── conftest.py              # Shared fixtures, respx mocks
│   ├── test_client.py           # API client unit tests
│   ├── test_server.py           # MCP tool integration tests
│   ├── test_models.py           # Model registry tests
│   ├── test_resources.py        # MCP resource tests
│   ├── test_prompts.py          # MCP prompt tests
│   └── test_mcp_protocol.py     # End-to-end MCP protocol tests
├── pyproject.toml
├── README.md
├── CHANGELOG.md
├── CONTRIBUTING.md
├── CODE_OF_CONDUCT.md
├── LICENSE                      # MIT
├── Dockerfile
├── .env.example                 # Example environment variables
└── .github/
    └── workflows/
        ├── ci.yml               # Lint → type check → test → build
        └── publish.yml          # PyPI publish on tag push
```

### 7.2 Key Design Decisions

1. **Single `client.py` module** — All HTTP interactions with Pruna API in one place. Uses `httpx.AsyncClient` with configurable timeout and retry.

2. **Transparent file handling** — Tools accept both URLs and local file paths. If a local path is detected, the server auto-uploads via `/v1/files` before calling the prediction endpoint.

3. **Smart sync/async selection** — Image models use `Try-Sync: true` for speed. Video models always use async with polling (1s for images, 3s for video).

4. **Output directory** — Generated files are saved to a configurable directory (`PRUNA_OUTPUT_DIR`, defaults to `./pruna-output`). File names: `{timestamp}_{model}_{id}.{ext}` for traceability.

5. **Model registry as data** — Model metadata (name, category, pricing, rate limits, parameters) is defined as a static registry in `models.py`. No dynamic discovery needed — Pruna's model list is stable and documented.

6. **Native MCP ImageContent return** — Image tools return `[TextContent, ImageContent]` using native MCP types. `TextContent` contains JSON metadata, `ImageContent` contains base64 image data. This enables inline display in compatible MCP clients. Video tools return plain JSON string (too large for base64).

7. **MCP Resources for model discovery** — Model catalog exposed as resources so LLMs can browse models without consuming tool calls.

8. **Prompts as guided workflows** — MCP Prompts encode Pruna's prompting best practices (subject/action/scene/camera/style structure for video, product photography conventions for e-commerce) so the LLM doesn't have to guess.

9. **Separate HTTP client for file uploads** — File uploads use a dedicated `httpx.AsyncClient` without the `Content-Type: application/json` header, allowing httpx to set the correct multipart boundary automatically.

### 7.3 Configuration

| Env Variable | Required | Default | Description |
|-------------|----------|---------|-------------|
| `PRUNA_API_KEY` | ✅ | — | Pruna API key |
| `PRUNA_OUTPUT_DIR` | — | `./pruna-output` | Directory for downloaded files |
| `PRUNA_POLL_INTERVAL` | — | `2` | Seconds between async status polls |
| `PRUNA_TIMEOUT` | — | `120` | HTTP timeout in seconds |
| `PRUNA_MAX_RETRIES` | — | `3` | Max retries on transient errors |

### 7.4 Error Handling

The server uses both MCP error mechanisms per spec:

**Protocol Errors** (JSON-RPC errors):
- Unknown tool name → `-32602` (Invalid params)
- Missing API key at startup → fail fast with actionable message
- Malformed request → `-32602`

**Tool Execution Errors** (`isError: true` in result):
- API errors (4xx/5xx) → clear message with status code and Pruna error body
- Prediction failures (`status: failed`) → Pruna's error message forwarded
- File not found (local paths) → clear error before attempting upload
- Input validation failures → specific message (e.g., "width must be a multiple of 16")

Tool execution errors are designed to be actionable so the LLM can self-correct and retry.

### 7.5 Input Validation

All tool inputs are validated before any API call. Validation rules:

| Parameter | Rules |
|-----------|-------|
| `prompt` | Non-empty string |
| `model` | Must exist in model registry and match the tool's category |
| `aspect_ratio` | Must be one of the allowed enum values per model |
| `width`, `height` | 256-1440, must be multiples of 16, only valid when `aspect_ratio=custom` |
| `seed` | Non-negative integer |
| `images` (edit) | 1-5 items, each must be a valid URL or existing local file path |
| `target` (upscale) | Integer 1-8 |
| `output_format` | One of `webp`, `jpg`, `png` |
| `duration` (video) | Integer 1-20 |
| `resolution` (video) | One of `720p`, `1080p` |
| `fps` (video) | One of `24`, `48` |
| `file_path` (upload) | Must exist, file size ≤ 20MB |

Validation errors are returned as tool execution errors with `isError: true`.

### 7.6 Retry Strategy

The HTTP client implements retry with exponential backoff for transient failures:

- **Retryable status codes:** `429` (rate limit), `502`, `503`, `504` (server errors)
- **Max retries:** configurable via `PRUNA_MAX_RETRIES` (default: 3)
- **Backoff:** exponential with jitter — `min(2^attempt + random(0, 1), 30)` seconds
- **429 handling:** respect `Retry-After` header if present, otherwise use backoff
- **Non-retryable:** `400`, `401`, `403`, `404` → fail immediately with clear error

### 7.7 Progress Notifications

For async operations (video generation, slow edits), the server emits MCP `notifications/progress` during polling:

```json
{
  "jsonrpc": "2.0",
  "method": "notifications/progress",
  "params": {
    "progressToken": "<from original request>",
    "progress": 50,
    "total": 100,
    "message": "Video generation in progress (status: processing)"
  }
}
```

Progress mapping:
- `starting` → progress 10
- `processing` → progress 50
- `succeeded` → progress 100

The `progressToken` is taken from the `_meta.progressToken` field of the incoming `tools/call` request, per MCP spec. If the client does not provide a progress token, no notifications are emitted.

### 7.8 MCP Logging

The server emits `notifications/message` for observability:

- **Level `info`:** Tool invocation start, generation completed, file downloaded
- **Level `warning`:** Retry triggered, sync timeout (falling back to async)
- **Level `error`:** API error, prediction failure, file I/O error

```json
{
  "jsonrpc": "2.0",
  "method": "notifications/message",
  "params": {
    "level": "info",
    "logger": "pruna-mcp-server",
    "data": "generate_image completed: p-image, 1024x576, 823ms"
  }
}
```

## 8. Security

Per [MCP Security Considerations](https://modelcontextprotocol.io/specification/2025-11-25/server/tools#security-considerations), the server MUST validate inputs, implement access controls, and sanitize outputs.

### 8.1 API Key Protection

- The API key is read from `PRUNA_API_KEY` environment variable only — never from arguments, config files, or tool inputs
- The API key is never logged, never included in error messages, never returned in tool results
- MCP logging (`notifications/message`) redacts any header containing `apikey`

### 8.2 Path Traversal Protection

Tools that accept file paths (`upload_file`, `edit_image`, `upscale_image`, `generate_video`) MUST:
- Resolve paths to absolute using `pathlib.Path.resolve()`
- Reject paths containing `..` after resolution
- Reject paths outside the user's home directory or current working directory
- Reject symlinks that resolve outside allowed directories

This prevents a malicious LLM prompt from exfiltrating sensitive files via the upload endpoint.

### 8.3 Output Sanitization

- URLs returned by Pruna API (`generation_url`, `get_url`) are validated as HTTPS URLs pointing to `api.pruna.ai` before being fetched
- Downloaded file content is written to the configured output directory only — never to arbitrary paths
- Base64 image content returned in MCP results is capped at 5MB to prevent memory exhaustion

### 8.4 Resource Limits

- Maximum file upload size: 20MB (validated before upload)
- Maximum base64 image return size: 5MB (larger images return file path only)
- HTTP timeout: configurable, default 120s
- Async polling timeout: 10 minutes max (prevents infinite polling on stuck predictions)
- Output directory is created with `0o755` permissions if it doesn't exist

## 9. Quality Standards

### 9.1 Code

- Python 3.10+
- Full type hints (strict mypy)
- `py.typed` marker (PEP 561) for downstream type checking
- Async throughout (httpx + FastMCP)
- Docstrings on all public functions (tool docstrings serve as MCP descriptions shown to LLMs)
- Ruff for linting + formatting

### 9.2 Testing

#### Unit Tests
- pytest + pytest-asyncio
- Mock HTTP calls with `respx` (no real API calls in CI)
- Coverage for: all tools, sync/async flows, file upload, error cases, input validation, retry logic, progress notifications, prompts, resources
- Target: >90% coverage

#### MCP Protocol Integration Tests (`test_mcp_protocol.py`)
End-to-end tests that instantiate a real MCP server in-process and verify the full JSON-RPC cycle:

1. **Server initialization** — verify capabilities declaration (tools, resources, prompts)
2. **`tools/list`** — verify all 6 tools are listed with correct names, titles, annotations, inputSchema, outputSchema
3. **`tools/call`** — for each tool: call with valid input → verify result contains `TextContent` + `ImageContent` (for image tools) or plain string (for video/list)
4. **`tools/call` error** — call with invalid input → verify `isError: true` with actionable message
5. **`resources/list`** — verify `pruna://models` and `pruna://models/{id}` are listed
6. **`resources/read`** — verify resource content matches expected JSON schema
7. **`prompts/list`** — verify all 7 prompts are listed with correct names and arguments
8. **`prompts/get`** — for each prompt: call with arguments → verify returned messages are well-formed

These tests use respx to mock Pruna API calls but exercise the full MCP protocol stack.

### 9.3 CI/CD

- GitHub Actions:
  - `ci.yml`: lint (ruff) → type check (mypy) → test (pytest --cov) → build
  - `publish.yml`: auto-publish to PyPI on tag push (`v*`)
- Semantic versioning via `python-semantic-release`
- Dependabot for dependency updates

### 9.4 Documentation

- `README.md`: Quick start, installation (uvx/pip/source/Docker), configuration, usage examples, MCP client config snippets (Kiro, Claude Desktop, Cursor), client compatibility matrix
- `CHANGELOG.md`: Keep-a-changelog format, auto-generated by semantic-release
- `CONTRIBUTING.md`: Development setup, testing, PR guidelines, code style
- `CODE_OF_CONDUCT.md`: Contributor Covenant v2.1
- `.env.example`: All env variables with descriptions
- Tool docstrings serve as MCP tool descriptions (shown to LLMs)

## 10. Dependencies

| Package | Purpose |
|---------|---------|
| `mcp` | MCP SDK (FastMCP) |
| `httpx` | Async HTTP client |

Dev dependencies: `pytest`, `pytest-asyncio`, `respx`, `mypy`, `ruff`, `python-semantic-release`

Minimal dependency footprint by design — 2 runtime deps only.

## 11. PyPI Package

- Name: `pruna-mcp-server`
- Entry point: `pruna-mcp` (CLI command)
- Install: `uvx pruna-mcp-server` or `pip install pruna-mcp-server`
- Build backend: `hatchling`
- Python classifiers: `Development Status :: 4 - Beta`, `Framework :: MCP`

### 11.1 MCP Client Config

```json
{
  "pruna": {
    "command": "uvx",
    "args": ["pruna-mcp-server"],
    "env": {
      "PRUNA_API_KEY": "$PRUNA_API_KEY"
    },
    "autoApprove": [
      "generate_image",
      "edit_image",
      "upscale_image",
      "generate_video",
      "list_models",
      "upload_file"
    ]
  }
}
```

### 11.2 Docker

```dockerfile
FROM python:3.12-slim
RUN pip install pruna-mcp-server
ENTRYPOINT ["pruna-mcp"]
```

The Dockerfile enables deployment in constrained environments and signals production readiness. STDIO transport works via Docker with `docker run -i`.

## 12. Client Compatibility Matrix

Tested and supported MCP clients:

| Client | Transport | Status | Notes |
|--------|-----------|--------|-------|
| Kiro CLI | STDIO | ✅ Tested | Requires `tools` whitelist (`@pruna/*`) + `allowedTools` + prompt instruction in agent config |
| Claude Desktop | STDIO | ✅ Tested | Use full path to `uv`; does not render `ImageContent` inline in chat |
| Cursor | STDIO | 🔲 Planned | — |
| Claude Code | STDIO | 🔲 Planned | Plugin marketplace registration |
| Windsurf | STDIO | 🔲 Planned | — |

### 12.1 Known Limitations

- **Claude Desktop**: Does not display `ImageContent` blocks inline. The image is generated and saved locally; Claude references the file path in its response.
- **Kiro CLI**: Agent config requires three separate entries: `mcpServers` (server definition), `tools` (whitelist with `@pruna/*`), and `allowedTools` (individual tool names). Missing any of these causes tools to not appear.
- **macOS PATH**: Claude Desktop and other GUI-launched MCP clients use a minimal PATH. Always use the full path to `uv` (e.g. `/Users/you/.local/bin/uv`) in the command.

## 13. Milestones

### v0.1.0 — MVP ✅ (2026-04-13)
- [x] Project scaffolding (pyproject.toml, src layout, CI, .env.example, py.typed, Dockerfile)
- [x] CONTRIBUTING.md + CODE_OF_CONDUCT.md
- [x] Pruna API client with retry strategy
- [x] `generate_image` tool (sync mode, ImageContent return, annotations)
- [x] `list_models` tool (structured output, annotations)
- [x] MCP resources (`pruna://models`, `pruna://models/{id}`)
- [x] Tool annotations on all tools
- [x] Input validation + path traversal protection
- [x] Security hardening (API key protection, output sanitization)
- [x] Basic tests + MCP protocol integration tests + README

### v0.2.0 — Full Image Suite ✅ (2026-04-13)
- [x] `edit_image` tool (with auto-upload of local files)
- [x] `upscale_image` tool
- [x] `upload_file` tool
- [x] Transparent local file → Pruna URL handling
- [x] MCP Prompts: `product-photo`, `virtual-staging`, `ad-creative`, `image-enhance`

### v0.3.0 — Video + Polish ✅ (2026-04-13)
- [x] `generate_video` tool (async polling)
- [x] MCP Prompts: `social-media-visual`, `game-concept-art`, `video-ad`
- [x] Complete test suite (100 tests, 94% coverage)
- [x] PyPI publish workflow (semantic-release)
- [x] Full README with usage examples + client compatibility matrix
- [x] All 6 tools tested live against Pruna API

### Implemented but deferred from spec
- [ ] MCP logging via `notifications/message` — using Python logging instead (simpler, works with all transports)

### v1.0.0 — Production
- [ ] Battle-tested with broader real usage
- [ ] CHANGELOG auto-generated via semantic-release
- [ ] GitHub release automation
- [ ] Register on MCP Registry / Smithery
- [ ] Docker image published to GHCR
- [ ] MCP progress notifications + logging

### v2.0 — Future
- LoRA training workflows (`p-image-trainer`, `p-image-edit-trainer`)
- HTTP/SSE transport mode
- Cost tracking tool
- Batch generation tool
