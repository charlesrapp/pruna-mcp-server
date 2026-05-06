"""MCP prompt templates for common Pruna AI workflows."""

from __future__ import annotations

from dataclasses import dataclass

_PLATFORM_RATIOS: dict[str, str] = {
    "instagram": "1:1",
    "story": "9:16",
    "reels": "9:16",
    "tiktok": "9:16",
    "youtube": "16:9",
    "linkedin": "16:9",
    "twitter": "16:9",
    "facebook": "1:1",
}


@dataclass(frozen=True)
class PromptTemplate:
    """An MCP prompt template."""

    name: str
    description: str
    arguments: list[dict[str, str | bool]]
    template: str


PROMPTS: list[PromptTemplate] = [
    PromptTemplate(
        name="product-photo",
        description="Generate an e-commerce product photo on a clean background",
        arguments=[
            {"name": "product", "description": "Product description", "required": True},
            {"name": "background", "description": "Background description", "required": False},
            {"name": "style", "description": "Photography style", "required": False},
        ],
        template=(
            "Generate a product photo using Pruna AI.\n\n"
            "Product: {product}\n"
            "Background: {background}\n"
            "Style: {style}\n\n"
            "Use the generate_image tool with model p-image, aspect_ratio 1:1. "
            "Compose the prompt as: '{product}, {background}, {style}, high resolution, "
            "commercial photography, centered composition'."
        ),
    ),
    PromptTemplate(
        name="virtual-staging",
        description="Stage an empty room with furniture and decor",
        arguments=[
            {"name": "room_image", "description": "Path or URL to the empty room photo", "required": True},
            {"name": "style", "description": "Interior design style", "required": False},
            {"name": "room_type", "description": "Room type", "required": False},
        ],
        template=(
            "Stage this empty room using Pruna AI.\n\n"
            "Room image: {room_image}\nStyle: {style}\nRoom type: {room_type}\n\n"
            "Use the edit_image tool with model p-image-edit. "
            "Prompt: 'Furnish this empty {room_type} in {style} style. "
            "Add appropriate furniture, decor, rugs, and lighting. "
            "Keep the room architecture, windows, and flooring unchanged.'"
        ),
    ),
    PromptTemplate(
        name="social-media-visual",
        description="Create a visual optimized for a specific social platform",
        arguments=[
            {"name": "topic", "description": "Visual subject or campaign topic", "required": True},
            {"name": "platform", "description": "Target platform (instagram, story, tiktok, youtube, linkedin)", "required": False},
            {"name": "tone", "description": "Visual tone", "required": False},
        ],
        template=(
            "Create a social media visual using Pruna AI.\n\n"
            "Topic: {topic}\nPlatform: {platform}\nTone: {tone}\n\n"
            "Use the generate_image tool with model p-image. "
            "Set aspect_ratio based on platform ({platform_ratios}). "
            "Compose the prompt as: '{topic}, {tone}, social media visual, "
            "bold colors, clean composition, trending aesthetic'."
        ),
    ),
    PromptTemplate(
        name="game-concept-art",
        description="Generate game concept art (characters, environments, items)",
        arguments=[
            {"name": "subject", "description": "What to generate (character, environment, weapon, etc.)", "required": True},
            {"name": "game_genre", "description": "Game genre", "required": False},
            {"name": "art_style", "description": "Art style", "required": False},
        ],
        template=(
            "Generate game concept art using Pruna AI.\n\n"
            "Subject: {subject}\nGenre: {game_genre}\nArt style: {art_style}\n\n"
            "Use the generate_image tool with model p-image, aspect_ratio 16:9. "
            "Compose the prompt as: '{subject}, {game_genre} game, {art_style}, "
            "highly detailed, dramatic lighting, cinematic composition, Unreal Engine 5 quality'."
        ),
    ),
    PromptTemplate(
        name="ad-creative",
        description="Create a digital advertising visual with text overlay",
        arguments=[
            {"name": "product", "description": "Product or brand to advertise", "required": True},
            {"name": "headline", "description": "Ad headline text to render on the image", "required": True},
            {"name": "target_audience", "description": "Target audience", "required": False},
        ],
        template=(
            "Create a digital ad creative using Pruna AI.\n\n"
            'Product: {product}\nHeadline: "{headline}"\nAudience: {target_audience}\n\n'
            "Use the generate_image tool with model p-image, aspect_ratio 1:1. "
            'Compose the prompt as: \'Professional advertisement for {product}, bold text reading "{headline}", '
            "appealing to {target_audience}, clean modern design, vibrant colors, commercial quality'."
        ),
    ),
    PromptTemplate(
        name="video-ad",
        description="Generate a short video ad from a product image",
        arguments=[
            {"name": "product_image", "description": "Path or URL to the product/person image", "required": True},
            {"name": "script", "description": "What happens in the video (action, speech, camera movement)", "required": True},
            {"name": "duration", "description": "Video duration in seconds", "required": False},
        ],
        template=(
            "Create a video ad using Pruna AI.\n\n"
            "Product image: {product_image}\nScript: {script}\nDuration: {duration}s\n\n"
            "Use the generate_video tool with model p-video, the provided image, and duration. "
            "Compose the prompt following Pruna's video prompting structure:\n"
            "- [Subject]: describe the subject from the image\n"
            "- [Action]: {script}\n"
            "- [Camera]: appropriate camera movement\n"
            "- [Style]: commercial quality, professional lighting\n"
            "- [Audio]: include speech if the script contains dialogue"
        ),
    ),
    PromptTemplate(
        name="image-enhance",
        description="Multi-step workflow: upscale + enhance an AI-generated image",
        arguments=[
            {"name": "image", "description": "Path or URL to the image to enhance", "required": True},
            {"name": "target_mp", "description": "Target megapixels", "required": False},
        ],
        template=(
            "Enhance this image using Pruna AI.\n\n"
            "Image: {image}\nTarget: {target_mp} megapixels\n\n"
            "Use the upscale_image tool with model p-image-upscale, target={target_mp}, "
            "enhance_details=true, enhance_realism=true, output_format=png."
        ),
    ),
]

_PROMPT_INDEX: dict[str, PromptTemplate] = {p.name: p for p in PROMPTS}

_DEFAULTS: dict[str, dict[str, str]] = {
    "product-photo": {"background": "clean white studio background", "style": "professional product photography, soft studio lighting"},
    "virtual-staging": {"style": "modern minimalist", "room_type": "living room"},
    "social-media-visual": {"platform": "instagram", "tone": "vibrant and eye-catching"},
    "game-concept-art": {"game_genre": "fantasy RPG", "art_style": "concept art, digital painting"},
    "ad-creative": {"target_audience": "general consumer"},
    "video-ad": {"duration": "5"},
    "image-enhance": {"target_mp": "4"},
}


def get_prompt(name: str) -> PromptTemplate | None:
    """Get a prompt template by name."""
    return _PROMPT_INDEX.get(name)


def get_all_prompts() -> list[PromptTemplate]:
    """Get all prompt templates."""
    return list(PROMPTS)


def render_prompt(name: str, arguments: dict[str, str]) -> str | None:
    """Render a prompt template with the given arguments.

    Returns the rendered message text, or None if the prompt is not found.
    """
    prompt = get_prompt(name)
    if prompt is None:
        return None

    # Apply defaults
    defaults = _DEFAULTS.get(name, {})
    merged = {**defaults, **arguments}

    # Special handling for social-media-visual platform ratios
    if name == "social-media-visual":
        platform = merged.get("platform", "instagram")
        ratio = _PLATFORM_RATIOS.get(platform, "1:1")
        merged["platform_ratios"] = f"{platform}→{ratio}"

    return prompt.template.format_map(_SafeDict(merged))


class _SafeDict(dict):  # type: ignore[type-arg]
    """Dict that returns {key} for missing keys instead of raising KeyError."""

    def __missing__(self, key: str) -> str:
        return f"{{{key}}}"
