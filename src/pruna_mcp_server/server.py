"""MCP server for Pruna AI."""

from __future__ import annotations

import asyncio
import json
import logging
import secrets
import time
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import Context, FastMCP
from mcp.types import ImageContent, TextContent, ToolAnnotations

from pruna_mcp_server.client import PrunaAPIError, PrunaClient
from pruna_mcp_server.config import PrunaConfig, load_config
from pruna_mcp_server.models import get_all_models, get_model, validate_model
from pruna_mcp_server.prompts import get_all_prompts, render_prompt

logger = logging.getLogger("pruna-mcp-server")

mcp = FastMCP(
    "pruna-mcp-server",
    instructions="MCP server for Pruna AI — image generation, editing, upscaling, and video generation.",
)

_client: PrunaClient | None = None
_config: PrunaConfig | None = None

_MAX_BASE64_SIZE = 5 * 1024 * 1024  # 5MB
_POLL_TIMEOUT = 600  # 10 minutes max
_MAX_CONCURRENT_PREDICTIONS = 5
_prediction_semaphore = asyncio.Semaphore(_MAX_CONCURRENT_PREDICTIONS)


def _get_client() -> PrunaClient:
    global _client, _config
    if _client is None:
        _config = load_config()
        _client = PrunaClient(_config)
    return _client


def _get_config() -> PrunaConfig:
    if _config is None:
        _get_client()
    assert _config is not None
    return _config


def _output_path(model: str, prediction_id: str, ext: str) -> Path:
    config = _get_config()
    config.output_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    ts = int(time.time())
    return config.output_dir / f"{ts}_{model}_{prediction_id}.{ext}"


def _safe_pred_id(raw: str, length: int = 8) -> str:
    """Sanitize an API-provided id for safe use in a filename.

    Keeps only alphanumerics, '-' and '_' to prevent path traversal via the
    prediction id returned by the API. Falls back to a random token if empty.
    """
    cleaned = "".join(c for c in raw if c.isalnum() or c in "-_")[:length]
    return cleaned or secrets.token_urlsafe(6)


async def _fetch_output(client: PrunaClient, gen_url: str, out_path: Path) -> Path:
    """Download generated content, raising PrunaAPIError on missing/invalid URL.

    Converts the ValueError raised by URL validation into a handled
    PrunaAPIError so callers can return a clean error instead of leaking a
    raw traceback.
    """
    if not gen_url:
        raise PrunaAPIError(502, "Pruna API returned no generation URL")
    try:
        return await client.download(gen_url, out_path)
    except ValueError as e:
        raise PrunaAPIError(502, f"Invalid delivery URL: {e}") from e


def _image_result(out_path: Path, metadata: dict[str, Any]) -> list[TextContent | ImageContent]:
    """Build a tool result with JSON metadata + inline image if small enough."""
    import base64

    result: list[TextContent | ImageContent] = [
        TextContent(type="text", text=json.dumps(metadata, indent=2))
    ]
    if out_path.stat().st_size <= _MAX_BASE64_SIZE:
        data = base64.b64encode(out_path.read_bytes()).decode()
        suffix = out_path.suffix.lower()
        mime = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp"}.get(suffix, "image/jpeg")
        result.append(ImageContent(type="image", data=data, mimeType=mime))
    return result


async def _resolve_image_url(client: PrunaClient, img: str) -> str:
    """Resolve an image argument to a Pruna-usable URL, uploading local files.

    Raises ValueError for disallowed http:// URLs.
    """
    if img.startswith(("https://", "/v1/")):
        return img
    if img.startswith("http://"):
        raise ValueError("http:// URLs are not allowed — use https://")
    upload_result = await client.upload_file(Path(img))
    return upload_result["urls"]["get"]  # type: ignore[no-any-return]


async def _predict_with_fallback(
    client: PrunaClient, model: str, input_data: dict[str, Any]
) -> dict[str, Any]:
    """Try sync prediction, fall back to async polling on timeout.

    Models that don't support sync go directly to async polling.
    """
    model_info = get_model(model)
    if model_info and not model_info.supports_sync:
        return await _predict_async_poll(client, model, input_data)
    try:
        return await client.predict_sync(model, input_data)
    except PrunaAPIError as e:
        if e.status_code == 408 or "timeout" in str(e).lower():
            logger.warning("Sync timeout for %s, falling back to async", model)
            return await _predict_async_poll(client, model, input_data)
        raise


async def _predict_async_poll(
    client: PrunaClient, model: str, input_data: dict[str, Any],
    ctx: Context | None = None,  # type: ignore[type-arg]
) -> dict[str, Any]:
    """Submit async prediction and poll until complete, with optional progress."""
    async with _prediction_semaphore:
        pred = await client.predict_async(model, input_data)
        prediction_id = pred["id"]
        config = _get_config()
        start = time.time()
        progress_map = {"starting": 10, "processing": 50}

        while (time.time() - start) < _POLL_TIMEOUT:
            status_data = await client.poll_status(prediction_id)
            status = status_data.get("status", "")

            if status == "succeeded":
                if ctx:
                    await ctx.report_progress(100, 100)
                return status_data
            if status == "failed":
                raise PrunaAPIError(
                    500,
                    status_data.get("error", status_data.get("message", "unknown error")),
                )
            if ctx:
                await ctx.report_progress(progress_map.get(status, 30), 100)
            await asyncio.sleep(config.poll_interval)

        raise PrunaAPIError(408, f"Prediction timed out after {_POLL_TIMEOUT}s")


@mcp.resource("pruna://models")
def resource_models() -> str:
    """Complete Pruna AI model catalog with pricing and capabilities."""
    models = get_all_models()
    data = {
        "models": [
            {
                "name": m.name,
                "category": m.category,
                "description": m.description,
                "pricing": m.pricing,
                "rate_limit": m.rate_limit,
                "supports_sync": m.supports_sync,
                "parameters": m.parameters,
            }
            for m in models
        ]
    }
    return json.dumps(data, indent=2)


@mcp.resource("pruna://models/{model_id}")
def resource_model_detail(model_id: str) -> str:
    """Detailed info for a specific Pruna AI model."""
    m = get_model(model_id)
    if m is None:
        return json.dumps({"error": f"Model '{model_id}' not found"})
    data = {
        "name": m.name,
        "category": m.category,
        "description": m.description,
        "pricing": m.pricing,
        "rate_limit": m.rate_limit,
        "supports_sync": m.supports_sync,
        "parameters": m.parameters,
    }
    return json.dumps(data, indent=2)


# --- Tools ---


@mcp.tool(
    annotations=ToolAnnotations(
        title="List Pruna AI Models",
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=False,
    ),
)
def list_models(category: str | None = None) -> str:
    """List available Pruna AI models with capabilities and pricing.

    Args:
        category: Filter by category: image, editing, try-on, upscale, video, video-edit
    """
    category_map: dict[str, str] = {
        "image": "text-to-image",
        "editing": "editing",
        "try-on": "try-on",
        "upscale": "upscale",
        "video": "video",
        "video-edit": "video-edit",
    }
    internal_cat = None
    if category:
        if category not in category_map:
            return _error_result(
                f"Invalid category '{category}'. Must be one of: image, editing, try-on, upscale, video, video-edit"
            )
        internal_cat = category_map[category]

    models = get_all_models(internal_cat)
    result: dict[str, Any] = {
        "models": [
            {
                "name": m.name,
                "category": m.category,
                "description": m.description,
                "pricing": m.pricing,
                "rate_limit": m.rate_limit,
            }
            for m in models
        ],
        "count": len(models),
    }
    return json.dumps(result, indent=2)


def _error_result(message: str) -> str:
    """Return a JSON error string for tool execution errors."""
    return json.dumps({"error": message})


@mcp.tool(
    annotations=ToolAnnotations(
        title="Image Generation (Pruna AI)",
        readOnlyHint=False,
        destructiveHint=False,
        idempotentHint=False,
        openWorldHint=True,
    ),
)
async def generate_image(
    prompt: str,
    model: str = "p-image",
    aspect_ratio: str = "16:9",
    width: int | None = None,
    height: int | None = None,
    seed: int | None = None,
) -> Any:
    """Generate an image from a text prompt using Pruna AI.

    Args:
        prompt: Text description of the image to generate
        model: Model to use (default: p-image)
        aspect_ratio: Output aspect ratio (1:1, 16:9, 9:16, 4:3, 3:4, 3:2, 2:3, custom)
        width: Custom width 256-1440, multiple of 16. Only when aspect_ratio=custom
        height: Custom height 256-1440, multiple of 16. Only when aspect_ratio=custom
        seed: Random seed for reproducible generation
    """
    if not prompt.strip():
        return _error_result("prompt must not be empty")
    try:
        validate_model(model, "text-to-image")
    except ValueError as e:
        return _error_result(str(e))

    valid_ratios = {"1:1", "16:9", "9:16", "4:3", "3:4", "3:2", "2:3", "custom"}
    if aspect_ratio not in valid_ratios:
        return _error_result(f"Invalid aspect_ratio '{aspect_ratio}'. Must be one of: {', '.join(sorted(valid_ratios))}")

    if aspect_ratio == "custom":
        if width is None or height is None:
            return _error_result("width and height are required when aspect_ratio=custom")
        if not (256 <= width <= 1440 and width % 16 == 0):
            return _error_result("width must be 256-1440 and a multiple of 16")
        if not (256 <= height <= 1440 and height % 16 == 0):
            return _error_result("height must be 256-1440 and a multiple of 16")

    if seed is not None and seed < 0:
        return _error_result("seed must be non-negative")

    input_data: dict[str, Any] = {"prompt": prompt, "aspect_ratio": aspect_ratio}
    if aspect_ratio == "custom":
        input_data["width"] = width
        input_data["height"] = height
    if seed is not None:
        input_data["seed"] = seed

    client = _get_client()
    logger.info("generate_image: model=%s, aspect_ratio=%s", model, aspect_ratio)
    start = time.time()
    result = await _predict_with_fallback(client, model, input_data)
    elapsed_ms = int((time.time() - start) * 1000)

    gen_url = result.get("generation_url", "")
    pred_id = secrets.token_urlsafe(6)
    out_path = _output_path(model, pred_id, "jpg")
    try:
        await _fetch_output(client, gen_url, out_path)
    except PrunaAPIError as e:
        return _error_result(str(e))

    metadata: dict[str, Any] = {
        "file_path": str(out_path),
        "model": model,
        "generation_time_ms": elapsed_ms,
    }
    if seed is not None:
        metadata["seed"] = seed
    logger.info("generate_image completed: %s, %dms", model, elapsed_ms)
    return _image_result(out_path, metadata)


@mcp.tool(
    annotations=ToolAnnotations(
        title="Image Editing (Pruna AI)",
        readOnlyHint=False,
        destructiveHint=False,
        idempotentHint=False,
        openWorldHint=True,
    ),
)
async def edit_image(
    prompt: str,
    images: list[str],
    model: str = "p-image-edit",
    aspect_ratio: str = "match_input_image",
    seed: int | None = None,
) -> Any:
    """Edit one or more images with text instructions using Pruna AI.

    Args:
        prompt: Edit instruction describing the desired changes
        images: 1-5 image URLs or local file paths
        model: Model to use (default: p-image-edit)
        aspect_ratio: Output aspect ratio
        seed: Random seed for reproducible generation
    """
    if not prompt.strip():
        return _error_result("prompt must not be empty")
    try:
        validate_model(model, "editing")
    except ValueError as e:
        return _error_result(str(e))
    if not images or len(images) > 5:
        return _error_result("images must contain 1-5 items")
    if seed is not None and seed < 0:
        return _error_result("seed must be non-negative")

    client = _get_client()

    resolved_urls: list[str] = []
    for img in images:
        if img.startswith(("https://", "/v1/")):
            resolved_urls.append(img)
        elif img.startswith("http://"):
            return _error_result("http:// URLs are not allowed — use https://")
        else:
            upload_result = await client.upload_file(Path(img))
            resolved_urls.append(upload_result["urls"]["get"])

    input_data: dict[str, Any] = {
        "prompt": prompt,
        "images": resolved_urls,
        "aspect_ratio": aspect_ratio,
    }
    if seed is not None:
        input_data["seed"] = seed

    logger.info("edit_image: model=%s, images=%d", model, len(images))
    start = time.time()
    result = await _predict_with_fallback(client, model, input_data)
    elapsed_ms = int((time.time() - start) * 1000)

    gen_url = result.get("generation_url", "")
    pred_id = secrets.token_urlsafe(6)
    out_path = _output_path(model, pred_id, "jpg")
    try:
        await _fetch_output(client, gen_url, out_path)
    except PrunaAPIError as e:
        return _error_result(str(e))

    metadata: dict[str, Any] = {
        "file_path": str(out_path),
        "model": model,
        "source_images": len(images),
        "generation_time_ms": elapsed_ms,
    }
    return _image_result(out_path, metadata)


@mcp.tool(
    annotations=ToolAnnotations(
        title="Virtual Try-On (Pruna AI)",
        readOnlyHint=False,
        destructiveHint=False,
        idempotentHint=False,
        openWorldHint=True,
    ),
)
async def try_on_image(
    person_image: str,
    garment_images: list[str],
    model: str = "p-image-try-on",
    prompt: str = "",
    turbo: bool = False,
    reference_pose: str | None = None,
    seed: int | None = None,
    output_format: str = "jpg",
    output_quality: int = 95,
    preserve_input_size: bool = True,
) -> Any:
    """Virtually fit one or more garments onto a person's photo using Pruna AI.

    Args:
        person_image: Image URL or local file path of the person
        garment_images: 1-11 garment reference images (URLs or local file paths).
            Up to 6 recommended for best quality.
        model: Model to use (default: p-image-try-on)
        prompt: Experimental guidance for non-flatlay garment images
            (e.g. which garment from which image to use)
        turbo: Faster generation. Not recommended for more than 4 garments
        reference_pose: Experimental. Image URL/path to repose the person before try-on
        seed: Random seed for reproducible generation
        output_format: Output format (webp, jpg, png)
        output_quality: Quality for jpg/webp outputs (0-100)
        preserve_input_size: Resize the result back to the person image size
    """
    try:
        validate_model(model, "try-on")
    except ValueError as e:
        return _error_result(str(e))
    if not garment_images or len(garment_images) > 11:
        return _error_result("garment_images must contain 1-11 items")
    if output_format not in {"webp", "jpg", "png"}:
        return _error_result("output_format must be webp, jpg, or png")
    if not (0 <= output_quality <= 100):
        return _error_result("output_quality must be 0-100")
    if seed is not None and seed < 0:
        return _error_result("seed must be non-negative")

    client = _get_client()

    try:
        person_url = await _resolve_image_url(client, person_image)
        garment_urls = [await _resolve_image_url(client, g) for g in garment_images]
        pose_url = (
            await _resolve_image_url(client, reference_pose) if reference_pose else None
        )
    except ValueError as e:
        return _error_result(str(e))

    input_data: dict[str, Any] = {
        "person_image": person_url,
        "garment_images": garment_urls,
        "turbo": turbo,
        "output_format": output_format,
        "output_quality": output_quality,
        "preserve_input_size": preserve_input_size,
    }
    if prompt:
        input_data["prompt"] = prompt
    if pose_url is not None:
        input_data["reference_pose"] = pose_url
    if seed is not None:
        input_data["seed"] = seed

    logger.info(
        "try_on_image: model=%s, garments=%d, turbo=%s",
        model,
        len(garment_images),
        turbo,
    )
    start = time.time()
    result = await _predict_with_fallback(client, model, input_data)
    elapsed_ms = int((time.time() - start) * 1000)

    gen_url = result.get("generation_url", "")
    pred_id = secrets.token_urlsafe(6)
    out_path = _output_path(model, pred_id, output_format)
    try:
        await _fetch_output(client, gen_url, out_path)
    except PrunaAPIError as e:
        return _error_result(str(e))

    metadata: dict[str, Any] = {
        "file_path": str(out_path),
        "model": model,
        "garments": len(garment_images),
        "turbo": turbo,
        "output_format": output_format,
        "generation_time_ms": elapsed_ms,
    }
    if seed is not None:
        metadata["seed"] = seed
    return _image_result(out_path, metadata)


@mcp.tool(
    annotations=ToolAnnotations(
        title="Image Upscaling (Pruna AI)",
        readOnlyHint=False,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=True,
    ),
)
async def upscale_image(
    image: str,
    target: int = 4,
    output_format: str = "jpg",
    enhance_details: bool = False,
    enhance_realism: bool = False,
) -> Any:
    """Upscale an image using Pruna AI.

    Args:
        image: Image URL or local file path to upscale
        target: Target resolution in megapixels (1-128, capped at 128 MP)
        output_format: Output format (webp, jpg, png)
        enhance_details: Enhance fine textures
        enhance_realism: Improve realism (recommended for AI-generated images)
    """
    if not (1 <= target <= 128):
        return _error_result("target must be 1-128 megapixels")
    if output_format not in {"webp", "jpg", "png"}:
        return _error_result("output_format must be webp, jpg, or png")

    client = _get_client()

    if image.startswith(("https://", "/v1/")):
        image_url = image
    elif image.startswith("http://"):
        return _error_result("http:// URLs are not allowed — use https://")
    else:
        upload_result = await client.upload_file(Path(image))
        image_url = upload_result["urls"]["get"]

    input_data: dict[str, Any] = {
        "image": image_url,
        "target": target,
        "output_format": output_format,
        "enhance_details": enhance_details,
        "enhance_realism": enhance_realism,
    }

    logger.info("upscale_image: target=%dMP, format=%s", target, output_format)
    start = time.time()
    result = await _predict_with_fallback(client, "p-image-upscale", input_data)
    elapsed_ms = int((time.time() - start) * 1000)

    gen_url = result.get("generation_url", "")
    pred_id = secrets.token_urlsafe(6)
    out_path = _output_path("p-image-upscale", pred_id, output_format)
    try:
        await _fetch_output(client, gen_url, out_path)
    except PrunaAPIError as e:
        return _error_result(str(e))

    metadata: dict[str, Any] = {
        "file_path": str(out_path),
        "target_mp": target,
        "output_format": output_format,
        "generation_time_ms": elapsed_ms,
    }
    return _image_result(out_path, metadata)


@mcp.tool(
    annotations=ToolAnnotations(
        title="Upload File to Pruna AI",
        readOnlyHint=False,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=True,
    ),
)
async def upload_file(file_path: str) -> str:
    """Upload a local file to Pruna AI for use in editing/video workflows.

    Args:
        file_path: Local file path to upload (max 20MB)
    """
    client = _get_client()
    try:
        result = await client.upload_file(Path(file_path))
    except ValueError as e:
        return _error_result(str(e))

    response: dict[str, Any] = {
        "url": result.get("urls", {}).get("get", ""),
        "file_id": result.get("id", ""),
        "content_type": result.get("content_type", ""),
        "size_bytes": result.get("size", 0),
        "expires_at": result.get("expires_at", ""),
    }
    return json.dumps(response, indent=2)


@mcp.tool(
    annotations=ToolAnnotations(
        title="Video Generation (Pruna AI)",
        readOnlyHint=False,
        destructiveHint=False,
        idempotentHint=False,
        openWorldHint=True,
    ),
)
async def generate_video(
    prompt: str,
    model: str = "p-video",
    image: str | None = None,
    audio: str | None = None,
    duration: int = 5,
    resolution: str = "720p",
    aspect_ratio: str = "16:9",
    fps: int = 24,
    seed: int | None = None,
) -> str:
    """Generate a video from text, image, or audio using Pruna AI.

    Args:
        prompt: Text prompt for video generation
        model: Model to use (p-video, wan-t2v, wan-i2v, vace)
        image: Input image URL/path for image-to-video
        audio: Input audio URL/path for audio-conditioned video
        duration: Duration in seconds (1-20)
        resolution: Video resolution (720p or 1080p)
        aspect_ratio: Aspect ratio (ignored when image is provided)
        fps: Frames per second (24 or 48)
        seed: Random seed for reproducible generation
    """
    if not prompt.strip():
        return _error_result("prompt must not be empty")
    try:
        validate_model(model, "video")
    except ValueError as e:
        return _error_result(str(e))
    if not (1 <= duration <= 20):
        return _error_result("duration must be 1-20 seconds")
    if resolution not in {"720p", "1080p"}:
        return _error_result("resolution must be 720p or 1080p")
    if fps not in {24, 48}:
        return _error_result("fps must be 24 or 48")
    if seed is not None and seed < 0:
        return _error_result("seed must be non-negative")

    client = _get_client()

    image_url = None
    if image:
        if image.startswith(("https://", "/v1/")):
            image_url = image
        elif image.startswith("http://"):
            return _error_result("http:// URLs are not allowed — use https://")
        else:
            upload_result = await client.upload_file(Path(image))
            image_url = upload_result["urls"]["get"]

    audio_url = None
    if audio:
        if audio.startswith(("https://", "/v1/")):
            audio_url = audio
        elif audio.startswith("http://"):
            return _error_result("http:// URLs are not allowed — use https://")
        else:
            upload_result = await client.upload_file(Path(audio))
            audio_url = upload_result["urls"]["get"]

    input_data: dict[str, Any] = {
        "prompt": prompt,
        "duration": duration,
        "resolution": resolution,
        "aspect_ratio": aspect_ratio,
        "fps": fps,
    }
    if image_url:
        input_data["image"] = image_url
    if audio_url:
        input_data["audio"] = audio_url
    if seed is not None:
        input_data["seed"] = seed

    logger.info("generate_video: model=%s, duration=%ds", model, duration)
    start = time.time()
    try:
        status_data = await _predict_async_poll(client, model, input_data)
    except PrunaAPIError as e:
        return _error_result(f"Video generation failed: {e}")
    elapsed_ms = int((time.time() - start) * 1000)

    gen_url = status_data.get("generation_url", "")
    pred_id = _safe_pred_id(status_data.get("id", ""))
    out_path = _output_path(model, pred_id, "mp4")
    try:
        await _fetch_output(client, gen_url, out_path)
    except PrunaAPIError as e:
        return _error_result(str(e))

    response: dict[str, Any] = {
        "file_path": str(out_path),
        "model": model,
        "duration": duration,
        "resolution": resolution,
        "generation_time_ms": elapsed_ms,
    }
    logger.info("generate_video completed: %s, %ds, %dms", model, duration, elapsed_ms)
    return json.dumps(response, indent=2)


@mcp.tool(
    annotations=ToolAnnotations(
        title="Video-to-Video Transform (Pruna AI)",
        readOnlyHint=False,
        destructiveHint=False,
        idempotentHint=False,
        openWorldHint=True,
    ),
)
async def transform_video(
    video: str,
    references: list[str],
    model: str = "p-video-animate",
    resolution: str = "720p",
    target_fps: str = "original",
    instruction_prompt: str = "",
    turbo: bool = False,
    save_audio: bool = True,
    ignore_audio: bool = False,
    seed: int | None = None,
) -> str:
    """Transform a source video using reference images (video-to-video).

    Two models are available:
    - p-video-animate: animate a single subject reference image using the motion
      from the source video (provide exactly 1 reference).
    - p-video-replace: replace the character(s) in the source video using 1-3
      identity reference images.

    Motion, timing, camera movement, and scene structure are preserved.

    Args:
        video: Source video URL or local file path (.mp4)
        references: Reference images (URLs or local file paths).
            Exactly 1 for p-video-animate, 1-3 for p-video-replace.
        model: Model to use (p-video-animate or p-video-replace)
        resolution: Output resolution (720p or 1080p)
        target_fps: Working FPS (original, 24, or 48)
        instruction_prompt: Optional guidance on how to apply the transform
        turbo: Faster generation for slightly lower quality
        save_audio: Save the output video with audio
        ignore_audio: Ignore source audio during generation
        seed: Random seed for reproducible generation
    """
    try:
        validate_model(model, "video-edit")
    except ValueError as e:
        return _error_result(str(e))
    if not references:
        return _error_result("references must contain at least 1 image")
    if model == "p-video-animate" and len(references) != 1:
        return _error_result("p-video-animate requires exactly 1 reference image")
    if model == "p-video-replace" and len(references) > 3:
        return _error_result("p-video-replace supports 1-3 reference images")
    if resolution not in {"720p", "1080p"}:
        return _error_result("resolution must be 720p or 1080p")
    if target_fps not in {"original", "24", "48"}:
        return _error_result("target_fps must be original, 24, or 48")
    if seed is not None and seed < 0:
        return _error_result("seed must be non-negative")

    client = _get_client()

    try:
        video_url = await _resolve_image_url(client, video)
        reference_urls = [await _resolve_image_url(client, r) for r in references]
    except ValueError as e:
        return _error_result(str(e))

    input_data: dict[str, Any] = {
        "video": video_url,
        "resolution": resolution,
        "target_fps": target_fps,
        "turbo": turbo,
        "save_audio": save_audio,
        "ignore_audio": ignore_audio,
    }
    if model == "p-video-animate":
        input_data["image"] = reference_urls[0]
    else:
        input_data["images"] = reference_urls
    if instruction_prompt:
        input_data["instruction_prompt"] = instruction_prompt
    if seed is not None:
        input_data["seed"] = seed

    logger.info(
        "transform_video: model=%s, references=%d, resolution=%s",
        model,
        len(references),
        resolution,
    )
    start = time.time()
    try:
        status_data = await _predict_async_poll(client, model, input_data)
    except PrunaAPIError as e:
        return _error_result(f"Video transform failed: {e}")
    elapsed_ms = int((time.time() - start) * 1000)

    gen_url = status_data.get("generation_url", "")
    pred_id = _safe_pred_id(status_data.get("id", ""))
    out_path = _output_path(model, pred_id, "mp4")
    try:
        await _fetch_output(client, gen_url, out_path)
    except PrunaAPIError as e:
        return _error_result(str(e))

    response: dict[str, Any] = {
        "file_path": str(out_path),
        "model": model,
        "references": len(references),
        "resolution": resolution,
        "generation_time_ms": elapsed_ms,
    }
    logger.info("transform_video completed: %s, %dms", model, elapsed_ms)
    return json.dumps(response, indent=2)


# --- MCP Prompts ---

for _pt in get_all_prompts():
    def _make_prompt_fn(pt_name: str, pt_args: list[dict[str, str | bool]]) -> None:
        # Build parameter names for the function signature
        _required = [a["name"] for a in pt_args if a.get("required")]
        _optional = [a["name"] for a in pt_args if not a.get("required")]

        # Create a function with explicit parameters so FastMCP can inspect them
        _param_str = ", ".join(
            [f"{n}: str" for n in _required]
            + [f"{n}: str = ''" for n in _optional]
        )
        _fn_code = f"def _prompt_fn({_param_str}) -> str:\n"
        _fn_code += "    import inspect\n"
        _fn_code += "    frame = inspect.currentframe()\n"
        _fn_code += "    args = {k: v for k, v in frame.f_locals.items() if k != 'frame' and v}\n"
        _fn_code += f"    result = _render('{pt_name}', args)\n"
        _fn_code += f"    return result or 'Unknown prompt: {pt_name}'\n"

        _ns: dict[str, Any] = {"_render": render_prompt}
        exec(_fn_code, _ns)  # noqa: S102
        mcp.prompt(name=pt_name)(_ns["_prompt_fn"])

    _make_prompt_fn(_pt.name, _pt.arguments)


def main() -> None:
    """Entry point for the pruna-mcp CLI command."""
    from pruna_mcp_server.config import load_config

    load_config()  # Fail fast if API key missing
    mcp.run()
