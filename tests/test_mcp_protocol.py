"""End-to-end MCP protocol integration tests.

These tests instantiate the FastMCP server in-process and verify
the full tool/resource/prompt registration and invocation cycle.
"""

from __future__ import annotations

import json

from pruna_mcp_server.server import mcp


class TestMCPToolsRegistration:
    def test_all_tools_registered(self) -> None:
        tools = mcp._tool_manager._tools  # type: ignore[attr-defined]
        expected = {"list_models", "generate_image", "edit_image", "upscale_image", "generate_video", "upload_file"}
        assert expected.issubset(set(tools.keys())), f"Missing tools: {expected - set(tools.keys())}"

    def test_tool_count(self) -> None:
        tools = mcp._tool_manager._tools  # type: ignore[attr-defined]
        assert len(tools) >= 6

    def test_generate_image_has_annotations(self) -> None:
        tool = mcp._tool_manager._tools["generate_image"]  # type: ignore[attr-defined]
        assert tool.annotations is not None
        assert tool.annotations.title == "Image Generation (Pruna AI)"
        assert tool.annotations.openWorldHint is True

    def test_list_models_is_readonly(self) -> None:
        tool = mcp._tool_manager._tools["list_models"]  # type: ignore[attr-defined]
        assert tool.annotations is not None
        assert tool.annotations.readOnlyHint is True
        assert tool.annotations.openWorldHint is False

    def test_all_tools_have_annotations(self) -> None:
        tools = mcp._tool_manager._tools  # type: ignore[attr-defined]
        for name in ("list_models", "generate_image", "edit_image", "upscale_image", "generate_video", "upload_file"):
            assert tools[name].annotations is not None, f"{name} missing annotations"
            assert tools[name].annotations.title, f"{name} missing title"


class TestMCPResourcesRegistration:
    def test_models_resource_registered(self) -> None:
        # Verify the resource functions are callable and return valid JSON
        from pruna_mcp_server.server import resource_models

        data = json.loads(resource_models())
        assert "models" in data
        assert len(data["models"]) == 18

    def test_model_detail_resource(self) -> None:
        from pruna_mcp_server.server import resource_model_detail

        data = json.loads(resource_model_detail("p-image"))
        assert data["name"] == "p-image"

    def test_model_detail_unknown(self) -> None:
        from pruna_mcp_server.server import resource_model_detail

        data = json.loads(resource_model_detail("nonexistent"))
        assert "error" in data


class TestMCPPromptsRegistration:
    def test_prompts_registered(self) -> None:
        from pruna_mcp_server.prompts import get_all_prompts

        prompts = get_all_prompts()
        assert len(prompts) == 7

    def test_prompt_names(self) -> None:
        from pruna_mcp_server.prompts import get_all_prompts

        names = {p.name for p in get_all_prompts()}
        expected = {"product-photo", "virtual-staging", "social-media-visual", "game-concept-art", "ad-creative", "video-ad", "image-enhance"}
        assert names == expected

    def test_each_prompt_renders(self) -> None:
        from pruna_mcp_server.prompts import get_all_prompts, render_prompt

        # Minimal required args per prompt
        test_args: dict[str, dict[str, str]] = {
            "product-photo": {"product": "sneakers"},
            "virtual-staging": {"room_image": "/tmp/room.jpg"},
            "social-media-visual": {"topic": "summer sale"},
            "game-concept-art": {"subject": "dragon"},
            "ad-creative": {"product": "shoes", "headline": "50% OFF"},
            "video-ad": {"product_image": "/tmp/img.jpg", "script": "person waves"},
            "image-enhance": {"image": "/tmp/photo.jpg"},
        }
        for p in get_all_prompts():
            args = test_args[p.name]
            result = render_prompt(p.name, args)
            assert result is not None, f"Prompt {p.name} returned None"
            assert len(result) > 50, f"Prompt {p.name} rendered too short"
            # Verify all provided args appear in the output
            for val in args.values():
                assert val in result, f"Arg value '{val}' not found in rendered prompt {p.name}"


class TestMCPToolInputSchemas:
    """Verify tools have proper input schemas for MCP clients."""

    def test_generate_image_params(self) -> None:
        tool = mcp._tool_manager._tools["generate_image"]  # type: ignore[attr-defined]
        assert tool.fn is not None

    def test_list_models_params(self) -> None:
        tool = mcp._tool_manager._tools["list_models"]  # type: ignore[attr-defined]
        assert tool.fn is not None
