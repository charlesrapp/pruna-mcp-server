"""Tests for MCP server tools."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from pruna_mcp_server.server import (
    edit_image,
    generate_image,
    generate_video,
    list_models,
    upload_file,
    upscale_image,
)


def _parse(result: list | str) -> dict:  # type: ignore[type-arg]
    """Parse tool result — handles both list[TextContent|ImageContent] and plain str."""
    if isinstance(result, str):
        return json.loads(result)
    first = result[0]
    # TextContent has a .text attribute
    text = first.text if hasattr(first, "text") else str(first)
    return json.loads(text)


class TestListModels:
    def test_all_models(self) -> None:
        result = json.loads(list_models())
        assert result["count"] == 18
        assert len(result["models"]) == 18

    def test_filter_image(self) -> None:
        result = json.loads(list_models(category="image"))
        assert result["count"] == 10
        assert all(m["category"] == "text-to-image" for m in result["models"])

    def test_filter_video(self) -> None:
        result = json.loads(list_models(category="video"))
        assert result["count"] == 4

    def test_filter_editing(self) -> None:
        result = json.loads(list_models(category="editing"))
        assert result["count"] == 3

    def test_filter_upscale(self) -> None:
        result = json.loads(list_models(category="upscale"))
        assert result["count"] == 1

    def test_invalid_category(self) -> None:
        result = json.loads(list_models(category="invalid"))
        assert "error" in result

    def test_model_fields(self) -> None:
        result = json.loads(list_models())
        m = result["models"][0]
        assert "name" in m
        assert "category" in m
        assert "pricing" in m
        assert "rate_limit" in m
        assert "description" in m


def _mock_client(tmp_path: Path) -> AsyncMock:
    """Create a mock PrunaClient that writes a fake image."""
    client = AsyncMock()
    client.predict_sync.return_value = {
        "status": "succeeded",
        "generation_url": "/v1/predictions/delivery/xezq/abc12345/output.jpg",
    }

    async def fake_download(url: str, path: Path) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"\xff\xd8\xff\xe0" + b"\x00" * 100)  # fake JPEG
        return path

    client.download.side_effect = fake_download
    return client


class TestGenerateImage:
    async def test_success(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        mock = _mock_client(tmp_path)
        monkeypatch.setenv("PRUNA_API_KEY", "test")
        with patch("pruna_mcp_server.server._get_client", return_value=mock), \
             patch("pruna_mcp_server.server._get_config") as mock_cfg:
            from pruna_mcp_server.config import PrunaConfig
            mock_cfg.return_value = PrunaConfig(api_key="test", output_dir=tmp_path)
            raw = await generate_image("a sunset")
            result = _parse(raw)
        assert "file_path" in result
        assert result["model"] == "p-image"
        assert isinstance(raw, list) and len(raw) == 2  # JSON + Image

    async def test_empty_prompt(self) -> None:
        result = json.loads(await generate_image(""))
        assert "error" in result

    async def test_invalid_model(self) -> None:
        result = json.loads(await generate_image("test", model="fake"))
        assert "error" in result

    async def test_invalid_aspect_ratio(self) -> None:
        result = json.loads(await generate_image("test", aspect_ratio="5:3"))
        assert "error" in result

    async def test_custom_needs_dimensions(self) -> None:
        result = json.loads(await generate_image("test", aspect_ratio="custom"))
        assert "error" in result

    async def test_width_not_multiple_of_16(self) -> None:
        result = json.loads(await generate_image("test", aspect_ratio="custom", width=300, height=512))
        assert "error" in result
        assert "multiple of 16" in result["error"]

    async def test_negative_seed(self) -> None:
        result = json.loads(await generate_image("test", seed=-1))
        assert "error" in result


class TestEditImage:
    async def test_success_with_urls(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        mock = _mock_client(tmp_path)
        monkeypatch.setenv("PRUNA_API_KEY", "test")
        with patch("pruna_mcp_server.server._get_client", return_value=mock), \
             patch("pruna_mcp_server.server._get_config") as mock_cfg:
            from pruna_mcp_server.config import PrunaConfig
            mock_cfg.return_value = PrunaConfig(api_key="test", output_dir=tmp_path)
            result = _parse(await edit_image("make it blue", ["https://example.com/img.jpg"]))
        assert "file_path" in result
        assert result["source_images"] == 1

    async def test_empty_prompt(self) -> None:
        result = json.loads(await edit_image("", ["https://example.com/img.jpg"]))
        assert "error" in result

    async def test_too_many_images(self) -> None:
        imgs = [f"https://example.com/{i}.jpg" for i in range(6)]
        result = json.loads(await edit_image("test", imgs))
        assert "error" in result

    async def test_no_images(self) -> None:
        result = json.loads(await edit_image("test", []))
        assert "error" in result

    async def test_invalid_model(self) -> None:
        result = json.loads(await edit_image("test", ["https://example.com/img.jpg"], model="p-image"))
        assert "error" in result


class TestUpscaleImage:
    async def test_success(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        mock = _mock_client(tmp_path)
        monkeypatch.setenv("PRUNA_API_KEY", "test")
        with patch("pruna_mcp_server.server._get_client", return_value=mock), \
             patch("pruna_mcp_server.server._get_config") as mock_cfg:
            from pruna_mcp_server.config import PrunaConfig
            mock_cfg.return_value = PrunaConfig(api_key="test", output_dir=tmp_path)
            result = _parse(await upscale_image("https://example.com/img.jpg"))
        assert result["target_mp"] == 4
        assert result["output_format"] == "jpg"

    async def test_invalid_target(self) -> None:
        result = json.loads(await upscale_image("https://example.com/img.jpg", target=10))
        assert "error" in result

    async def test_invalid_format(self) -> None:
        result = json.loads(await upscale_image("https://example.com/img.jpg", output_format="bmp"))
        assert "error" in result


class TestUploadFile:
    async def test_success(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        test_file = tmp_path / "photo.jpg"
        test_file.write_bytes(b"fake-jpg")
        mock = AsyncMock()
        mock.upload_file.return_value = {
            "id": "file-abc",
            "content_type": "image/jpeg",
            "size": 8,
            "expires_at": "2026-04-13T00:00:00Z",
            "urls": {"get": "https://api.pruna.ai/v1/files/file-abc"},
        }
        monkeypatch.setenv("PRUNA_API_KEY", "test")
        with patch("pruna_mcp_server.server._get_client", return_value=mock):
            result = json.loads(await upload_file(str(test_file)))
        assert result["file_id"] == "file-abc"
        assert result["url"] == "https://api.pruna.ai/v1/files/file-abc"

    async def test_nonexistent_file(self, monkeypatch: pytest.MonkeyPatch) -> None:
        mock = AsyncMock()
        mock.upload_file.side_effect = ValueError("File not found: /nope.jpg")
        monkeypatch.setenv("PRUNA_API_KEY", "test")
        with patch("pruna_mcp_server.server._get_client", return_value=mock):
            result = json.loads(await upload_file("/nope.jpg"))
        assert "error" in result


def _mock_video_client(tmp_path: Path) -> AsyncMock:
    """Create a mock PrunaClient for video (async flow)."""
    client = AsyncMock()
    client.predict_async.return_value = {
        "id": "vid-12345678",
        "get_url": "/v1/predictions/status/vid-12345678",
    }
    # First poll: processing, second: succeeded
    client.poll_status.side_effect = [
        {"status": "processing"},
        {"status": "succeeded", "generation_url": "/v1/predictions/delivery/xezq/vid123/output.mp4"},
    ]

    async def fake_download(url: str, path: Path) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"\x00" * 200)
        return path

    client.download.side_effect = fake_download
    return client


class TestGenerateVideo:
    async def test_success(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        mock = _mock_video_client(tmp_path)
        monkeypatch.setenv("PRUNA_API_KEY", "test")
        with patch("pruna_mcp_server.server._get_client", return_value=mock), \
             patch("pruna_mcp_server.server._get_config") as mock_cfg:
            from pruna_mcp_server.config import PrunaConfig
            mock_cfg.return_value = PrunaConfig(api_key="test", output_dir=tmp_path, poll_interval=0.01)
            result = json.loads(await generate_video("a car driving"))
        assert "file_path" in result
        assert result["model"] == "p-video"
        assert result["duration"] == 5
        assert isinstance(result, dict)  # video returns plain str, not list

    async def test_empty_prompt(self) -> None:
        result = json.loads(await generate_video(""))
        assert "error" in result

    async def test_invalid_model(self) -> None:
        result = json.loads(await generate_video("test", model="p-image"))
        assert "error" in result

    async def test_invalid_duration(self) -> None:
        result = json.loads(await generate_video("test", duration=25))
        assert "error" in result

    async def test_invalid_resolution(self) -> None:
        result = json.loads(await generate_video("test", resolution="4k"))
        assert "error" in result

    async def test_invalid_fps(self) -> None:
        result = json.loads(await generate_video("test", fps=30))
        assert "error" in result

    async def test_failed_prediction(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        mock = AsyncMock()
        mock.predict_async.return_value = {"id": "vid-fail"}
        mock.poll_status.return_value = {"status": "failed", "error": "GPU OOM"}
        monkeypatch.setenv("PRUNA_API_KEY", "test")
        with patch("pruna_mcp_server.server._get_client", return_value=mock), \
             patch("pruna_mcp_server.server._get_config") as mock_cfg:
            from pruna_mcp_server.config import PrunaConfig
            mock_cfg.return_value = PrunaConfig(api_key="test", output_dir=tmp_path, poll_interval=0.01)
            result = json.loads(await generate_video("test"))
        assert "error" in result
        assert "GPU OOM" in result["error"]


class TestEditImageLocalUpload:
    async def test_auto_uploads_local_files(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        mock = _mock_client(tmp_path)
        mock.upload_file.return_value = {"urls": {"get": "https://api.pruna.ai/v1/files/file-up1"}}
        monkeypatch.setenv("PRUNA_API_KEY", "test")
        with patch("pruna_mcp_server.server._get_client", return_value=mock), \
             patch("pruna_mcp_server.server._get_config") as mock_cfg:
            from pruna_mcp_server.config import PrunaConfig
            mock_cfg.return_value = PrunaConfig(api_key="test", output_dir=tmp_path)
            result = _parse(await edit_image("make blue", ["/tmp/local.jpg"]))
        assert "file_path" in result
        mock.upload_file.assert_called_once()


class TestUpscaleImageLocalUpload:
    async def test_auto_uploads_local_file(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        mock = _mock_client(tmp_path)
        mock.upload_file.return_value = {"urls": {"get": "https://api.pruna.ai/v1/files/file-up2"}}
        monkeypatch.setenv("PRUNA_API_KEY", "test")
        with patch("pruna_mcp_server.server._get_client", return_value=mock), \
             patch("pruna_mcp_server.server._get_config") as mock_cfg:
            from pruna_mcp_server.config import PrunaConfig
            mock_cfg.return_value = PrunaConfig(api_key="test", output_dir=tmp_path)
            result = _parse(await upscale_image("/tmp/local.jpg", target=2, output_format="png"))
        assert result["target_mp"] == 2
        assert result["output_format"] == "png"
        mock.upload_file.assert_called_once()


class TestGenerateVideoWithImage:
    async def test_with_image_url(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        mock = _mock_video_client(tmp_path)
        monkeypatch.setenv("PRUNA_API_KEY", "test")
        with patch("pruna_mcp_server.server._get_client", return_value=mock), \
             patch("pruna_mcp_server.server._get_config") as mock_cfg:
            from pruna_mcp_server.config import PrunaConfig
            mock_cfg.return_value = PrunaConfig(api_key="test", output_dir=tmp_path, poll_interval=0.01)
            result = json.loads(await generate_video("animate this", image="https://example.com/img.jpg"))
        assert "file_path" in result

    async def test_with_local_image(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        mock = _mock_video_client(tmp_path)
        mock.upload_file.return_value = {"urls": {"get": "https://api.pruna.ai/v1/files/file-img"}}
        monkeypatch.setenv("PRUNA_API_KEY", "test")
        with patch("pruna_mcp_server.server._get_client", return_value=mock), \
             patch("pruna_mcp_server.server._get_config") as mock_cfg:
            from pruna_mcp_server.config import PrunaConfig
            mock_cfg.return_value = PrunaConfig(api_key="test", output_dir=tmp_path, poll_interval=0.01)
            result = json.loads(await generate_video("animate", image="/tmp/photo.jpg"))
        assert "file_path" in result
        mock.upload_file.assert_called_once()

    async def test_with_audio(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        mock = _mock_video_client(tmp_path)
        monkeypatch.setenv("PRUNA_API_KEY", "test")
        with patch("pruna_mcp_server.server._get_client", return_value=mock), \
             patch("pruna_mcp_server.server._get_config") as mock_cfg:
            from pruna_mcp_server.config import PrunaConfig
            mock_cfg.return_value = PrunaConfig(api_key="test", output_dir=tmp_path, poll_interval=0.01)
            result = json.loads(await generate_video("music video", audio="https://example.com/song.mp3"))
        assert "file_path" in result

    async def test_with_seed(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        mock = _mock_video_client(tmp_path)
        monkeypatch.setenv("PRUNA_API_KEY", "test")
        with patch("pruna_mcp_server.server._get_client", return_value=mock), \
             patch("pruna_mcp_server.server._get_config") as mock_cfg:
            from pruna_mcp_server.config import PrunaConfig
            mock_cfg.return_value = PrunaConfig(api_key="test", output_dir=tmp_path, poll_interval=0.01)
            result = json.loads(await generate_video("test", seed=42))
        assert "file_path" in result

    async def test_negative_seed(self) -> None:
        result = json.loads(await generate_video("test", seed=-1))
        assert "error" in result


class TestGenerateImageWithSeed:
    async def test_with_seed(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        mock = _mock_client(tmp_path)
        monkeypatch.setenv("PRUNA_API_KEY", "test")
        with patch("pruna_mcp_server.server._get_client", return_value=mock), \
             patch("pruna_mcp_server.server._get_config") as mock_cfg:
            from pruna_mcp_server.config import PrunaConfig
            mock_cfg.return_value = PrunaConfig(api_key="test", output_dir=tmp_path)
            result = _parse(await generate_image("test", seed=42))
        assert result["seed"] == 42

    async def test_custom_dimensions(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        mock = _mock_client(tmp_path)
        monkeypatch.setenv("PRUNA_API_KEY", "test")
        with patch("pruna_mcp_server.server._get_client", return_value=mock), \
             patch("pruna_mcp_server.server._get_config") as mock_cfg:
            from pruna_mcp_server.config import PrunaConfig
            mock_cfg.return_value = PrunaConfig(api_key="test", output_dir=tmp_path)
            result = _parse(await generate_image("test", aspect_ratio="custom", width=512, height=768))
        assert "file_path" in result


class TestPollTimeout:
    async def test_poll_times_out(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        mock = AsyncMock()
        mock.predict_async.return_value = {"id": "vid-timeout"}
        mock.poll_status.return_value = {"status": "processing"}
        monkeypatch.setenv("PRUNA_API_KEY", "test")
        with patch("pruna_mcp_server.server._get_client", return_value=mock), \
             patch("pruna_mcp_server.server._get_config") as mock_cfg, \
             patch("pruna_mcp_server.server._POLL_TIMEOUT", 0.01):
            from pruna_mcp_server.config import PrunaConfig
            mock_cfg.return_value = PrunaConfig(api_key="test", output_dir=tmp_path, poll_interval=0.005)
            result = json.loads(await generate_video("test"))
        assert "error" in result
        assert "timed out" in result["error"]


class TestHttpUrlRejection:
    async def test_edit_image_rejects_http(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("PRUNA_API_KEY", "test")
        result = json.loads(await edit_image("test", ["http://example.com/img.jpg"]))
        assert "error" in result
        assert "http://" in result["error"]

    async def test_upscale_rejects_http(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("PRUNA_API_KEY", "test")
        result = json.loads(await upscale_image("http://example.com/img.jpg"))
        assert "error" in result
        assert "http://" in result["error"]

    async def test_video_rejects_http_image(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("PRUNA_API_KEY", "test")
        result = json.loads(await generate_video("test", image="http://example.com/img.jpg"))
        assert "error" in result
        assert "http://" in result["error"]

    async def test_video_rejects_http_audio(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("PRUNA_API_KEY", "test")
        result = json.loads(await generate_video("test", audio="http://example.com/audio.mp3"))
        assert "error" in result
        assert "http://" in result["error"]


class TestPredictWithFallback:
    """Test _predict_with_fallback branches."""

    async def test_async_only_model_skips_sync(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Models with supports_sync=False should go directly to async polling."""
        mock = AsyncMock()
        mock.predict_async.return_value = {"id": "vid-direct"}
        mock.poll_status.return_value = {
            "status": "succeeded",
            "generation_url": "/v1/predictions/delivery/x/vid123/output.mp4",
        }

        async def fake_download(url: str, path: Path) -> Path:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b"\x00" * 100)
            return path

        mock.download.side_effect = fake_download
        monkeypatch.setenv("PRUNA_API_KEY", "test")
        with patch("pruna_mcp_server.server._get_client", return_value=mock), \
             patch("pruna_mcp_server.server._get_config") as mock_cfg:
            from pruna_mcp_server.config import PrunaConfig
            mock_cfg.return_value = PrunaConfig(api_key="test", output_dir=tmp_path, poll_interval=0.005)
            result = json.loads(await generate_video("a car driving"))
        assert "file_path" in result
        # predict_sync should NOT have been called (async-only model)
        mock.predict_sync.assert_not_called()
        mock.predict_async.assert_called_once()

    async def test_sync_timeout_falls_back_to_async(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Sync 408 should fall back to async polling."""
        from pruna_mcp_server.client import PrunaAPIError

        mock = _mock_client(tmp_path)
        mock.predict_sync.side_effect = PrunaAPIError(408, "timeout")
        mock.predict_async.return_value = {"id": "fallback-123"}
        mock.poll_status.return_value = {
            "status": "succeeded",
            "generation_url": "/v1/predictions/delivery/x/fb123/output.jpg",
        }
        monkeypatch.setenv("PRUNA_API_KEY", "test")
        with patch("pruna_mcp_server.server._get_client", return_value=mock), \
             patch("pruna_mcp_server.server._get_config") as mock_cfg:
            from pruna_mcp_server.config import PrunaConfig
            mock_cfg.return_value = PrunaConfig(api_key="test", output_dir=tmp_path, poll_interval=0.005)
            result = _parse(await generate_image("test"))
        assert "file_path" in result
        mock.predict_sync.assert_called_once()
        mock.predict_async.assert_called_once()


class TestEditImageSeed:
    async def test_with_seed(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        mock = _mock_client(tmp_path)
        monkeypatch.setenv("PRUNA_API_KEY", "test")
        with patch("pruna_mcp_server.server._get_client", return_value=mock), \
             patch("pruna_mcp_server.server._get_config") as mock_cfg:
            from pruna_mcp_server.config import PrunaConfig
            mock_cfg.return_value = PrunaConfig(api_key="test", output_dir=tmp_path)
            result = _parse(await edit_image("make blue", ["https://example.com/img.jpg"], seed=42))
        assert "file_path" in result

    async def test_negative_seed(self) -> None:
        result = json.loads(await edit_image("test", ["https://example.com/img.jpg"], seed=-1))
        assert "error" in result


class TestGenerateImageHeightValidation:
    async def test_height_not_multiple_of_16(self) -> None:
        result = json.loads(await generate_image("test", aspect_ratio="custom", width=512, height=300))
        assert "error" in result
        assert "multiple of 16" in result["error"]
