"""Pruna AI model registry — static metadata for all available models."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ModelInfo:
    """Metadata for a Pruna AI model."""

    name: str
    category: str
    description: str
    pricing: str
    rate_limit: str
    supports_sync: bool = True
    parameters: list[str] = field(default_factory=list)


_MODELS: list[ModelInfo] = [
    # Text-to-Image (10)
    ModelInfo("p-image", "text-to-image", "Ultra-fast text-to-image generation by Pruna", "$0.005/image", "500/min", True, ["prompt", "aspect_ratio", "width", "height", "seed"]),
    ModelInfo("p-image-lora", "text-to-image", "p-image with custom LoRA support", "$0.005/image", "500/min", True, ["prompt", "aspect_ratio", "seed", "lora_weights", "lora_scale"]),
    ModelInfo("flux-dev", "text-to-image", "High-quality image generation with Flux.1 Dev", "$0.005/image", "150/min", True, ["prompt", "aspect_ratio", "seed", "num_inference_steps", "guidance"]),
    ModelInfo("flux-dev-lora", "text-to-image", "Flux.1 Dev with LoRA support for custom styles", "$0.01/image", "150/min", True, ["prompt", "aspect_ratio", "seed", "lora_weights"]),
    ModelInfo("flux-2-klein-4b", "text-to-image", "Fast and cheap image generation", "$0.0001/image", "150/min", True, ["prompt", "aspect_ratio", "seed"]),
    ModelInfo("wan-image-small", "text-to-image", "Fast, efficient image generation", "$0.005/image", "150/min", True, ["prompt", "aspect_ratio", "seed"]),
    ModelInfo("qwen-image", "text-to-image", "Advanced image generation by Qwen", "$0.025/image", "150/min", True, ["prompt", "aspect_ratio", "seed"]),
    ModelInfo("qwen-image-fast", "text-to-image", "Faster generation with Qwen", "$0.005/image", "150/min", True, ["prompt", "aspect_ratio", "seed"]),
    ModelInfo("z-image-turbo", "text-to-image", "Fast generation with z-image", "$0.005/image", "150/min", True, ["prompt", "aspect_ratio", "seed"]),
    ModelInfo("z-image-turbo-lora", "text-to-image", "z-image augmented with LoRAs", "$0.008/image", "150/min", True, ["prompt", "aspect_ratio", "seed", "lora_weights"]),
    # Image Editing (3)
    ModelInfo("p-image-edit", "editing", "Premium image editing with fine control", "$0.010/image", "500/min", True, ["prompt", "images", "aspect_ratio", "seed"]),
    ModelInfo("p-image-edit-lora", "editing", "p-image-edit with custom LoRA support", "$0.010/image", "500/min", True, ["prompt", "images", "aspect_ratio", "seed", "lora_weights"]),
    ModelInfo("qwen-image-edit-plus", "editing", "Advanced image editing and manipulation", "$0.03/image", "150/min", True, ["prompt", "images", "aspect_ratio", "seed"]),
    # Image Upscaling (1)
    ModelInfo("p-image-upscale", "upscale", "AI-powered image upscaling with detail enhancement", "$0.005-0.01/image", "500/min", True, ["image", "target", "output_format", "enhance_details", "enhance_realism"]),
    # Video Generation (4)
    ModelInfo("p-video", "video", "Premium high-quality video generation", "$0.02-0.04/s", "250/min", False, ["prompt", "image", "audio", "duration", "resolution", "aspect_ratio", "fps", "seed"]),
    ModelInfo("wan-t2v", "video", "Generate videos from text descriptions", "variable", "30/min", False, ["prompt", "duration", "resolution", "aspect_ratio", "seed"]),
    ModelInfo("wan-i2v", "video", "Transform static images into dynamic videos", "variable", "30/min", False, ["prompt", "image", "duration", "resolution", "seed"]),
    ModelInfo("vace", "video", "AI-powered video generation with character consistency", "variable", "30/min", False, ["prompt", "image", "duration", "resolution", "seed"]),
]

_MODEL_INDEX: dict[str, ModelInfo] = {m.name: m for m in _MODELS}


def get_model(name: str) -> ModelInfo | None:
    """Get model info by name. Returns None if not found."""
    return _MODEL_INDEX.get(name)


def get_all_models(category: str | None = None) -> list[ModelInfo]:
    """List all models, optionally filtered by category."""
    if category is None:
        return list(_MODELS)
    return [m for m in _MODELS if m.category == category]


def validate_model(name: str, expected_category: str) -> ModelInfo:
    """Validate that a model exists and matches the expected category.

    Raises ValueError if the model is not found or has the wrong category.
    """
    model = get_model(name)
    if model is None:
        available = [m.name for m in _MODELS if m.category == expected_category]
        raise ValueError(
            f"Unknown model '{name}'. Available {expected_category} models: {', '.join(available)}"
        )
    if model.category != expected_category:
        raise ValueError(
            f"Model '{name}' is a {model.category} model, not {expected_category}. "
            f"Use a {expected_category} model instead."
        )
    return model
