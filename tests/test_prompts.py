"""Tests for MCP prompt templates."""

from __future__ import annotations

from pruna_mcp_server.prompts import get_all_prompts, get_prompt, render_prompt


class TestPromptRegistry:
    def test_total_count(self) -> None:
        assert len(get_all_prompts()) == 7

    def test_all_names(self) -> None:
        names = {p.name for p in get_all_prompts()}
        expected = {
            "product-photo", "virtual-staging", "social-media-visual",
            "game-concept-art", "ad-creative", "video-ad", "image-enhance",
        }
        assert names == expected

    def test_get_existing(self) -> None:
        p = get_prompt("product-photo")
        assert p is not None
        assert p.name == "product-photo"

    def test_get_nonexistent(self) -> None:
        assert get_prompt("nonexistent") is None

    def test_all_have_required_fields(self) -> None:
        for p in get_all_prompts():
            assert p.name
            assert p.description
            assert len(p.arguments) > 0
            assert p.template


class TestRenderPrompt:
    def test_product_photo(self) -> None:
        result = render_prompt("product-photo", {"product": "white sneakers"})
        assert result is not None
        assert "white sneakers" in result
        assert "generate_image" in result

    def test_product_photo_defaults(self) -> None:
        result = render_prompt("product-photo", {"product": "mug"})
        assert result is not None
        assert "clean white studio background" in result

    def test_virtual_staging(self) -> None:
        result = render_prompt("virtual-staging", {"room_image": "/tmp/room.jpg"})
        assert result is not None
        assert "edit_image" in result

    def test_social_media_visual(self) -> None:
        result = render_prompt("social-media-visual", {"topic": "summer sale", "platform": "tiktok"})
        assert result is not None
        assert "tiktok→9:16" in result

    def test_social_media_default_platform(self) -> None:
        result = render_prompt("social-media-visual", {"topic": "launch"})
        assert result is not None
        assert "instagram→1:1" in result

    def test_game_concept_art(self) -> None:
        result = render_prompt("game-concept-art", {"subject": "dragon"})
        assert result is not None
        assert "dragon" in result
        assert "Unreal Engine 5" in result

    def test_ad_creative(self) -> None:
        result = render_prompt("ad-creative", {"product": "shoes", "headline": "50% OFF"})
        assert result is not None
        assert "50% OFF" in result

    def test_video_ad(self) -> None:
        result = render_prompt("video-ad", {"product_image": "/tmp/img.jpg", "script": "person waves"})
        assert result is not None
        assert "generate_video" in result

    def test_image_enhance(self) -> None:
        result = render_prompt("image-enhance", {"image": "/tmp/photo.jpg"})
        assert result is not None
        assert "upscale_image" in result

    def test_unknown_prompt(self) -> None:
        assert render_prompt("nonexistent", {}) is None
