"""Tests for Pruna API client."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import httpx
import pytest
import respx

from pruna_mcp_server.client import PrunaAPIError, PrunaClient, validate_file_path
from pruna_mcp_server.config import PrunaConfig

BASE = "https://api.pruna.ai"


@pytest.fixture()
def client(config: PrunaConfig) -> PrunaClient:
    return PrunaClient(config)


class TestPredictSync:
    @respx.mock
    async def test_success(self, client: PrunaClient) -> None:
        respx.post(f"{BASE}/v1/predictions").mock(
            return_value=httpx.Response(200, json={"status": "succeeded", "generation_url": "/v1/predictions/delivery/abc"})
        )
        result = await client.predict_sync("p-image", {"prompt": "test"})
        assert result["status"] == "succeeded"

    @respx.mock
    async def test_api_error(self, client: PrunaClient) -> None:
        respx.post(f"{BASE}/v1/predictions").mock(
            return_value=httpx.Response(401, text="Unauthorized")
        )
        with pytest.raises(PrunaAPIError, match="401"):
            await client.predict_sync("p-image", {"prompt": "test"})


class TestPredictAsync:
    @respx.mock
    async def test_success(self, client: PrunaClient) -> None:
        respx.post(f"{BASE}/v1/predictions").mock(
            return_value=httpx.Response(200, json={"id": "pred-123", "get_url": "/v1/predictions/status/pred-123"})
        )
        result = await client.predict_async("p-video", {"prompt": "test"})
        assert result["id"] == "pred-123"


class TestPollStatus:
    @respx.mock
    async def test_success(self, client: PrunaClient) -> None:
        respx.get(f"{BASE}/v1/predictions/status/pred-123").mock(
            return_value=httpx.Response(200, json={"status": "succeeded", "generation_url": "/v1/delivery/abc"})
        )
        result = await client.poll_status("pred-123")
        assert result["status"] == "succeeded"


class TestDownload:
    @respx.mock
    async def test_success(self, client: PrunaClient, tmp_path: Path) -> None:
        respx.get(f"{BASE}/v1/predictions/delivery/abc").mock(
            return_value=httpx.Response(200, content=b"fake-image-data")
        )
        out = tmp_path / "output.jpg"
        result = await client.download("/v1/predictions/delivery/abc", out)
        assert result == out
        assert out.read_bytes() == b"fake-image-data"

    async def test_rejects_non_pruna_url(self, client: PrunaClient, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="does not point to api.pruna.ai"):
            await client.download("https://evil.com/file.jpg", tmp_path / "out.jpg")


class TestUploadFile:
    @respx.mock
    async def test_success(self, client: PrunaClient, tmp_path: Path) -> None:
        test_file = tmp_path / "photo.jpg"
        test_file.write_bytes(b"fake-jpg-content")
        respx.post(f"{BASE}/v1/files").mock(
            return_value=httpx.Response(200, json={"id": "file-abc", "urls": {"get": f"{BASE}/v1/files/file-abc"}})
        )
        result = await client.upload_file(test_file, allowed_dirs=[tmp_path])
        assert result["id"] == "file-abc"


class TestRetry:
    @respx.mock
    async def test_retries_on_429(self, client: PrunaClient) -> None:
        route = respx.post(f"{BASE}/v1/predictions")
        route.side_effect = [
            httpx.Response(429, text="Rate limited"),
            httpx.Response(200, json={"status": "succeeded"}),
        ]
        with patch("pruna_mcp_server.client._async_sleep"):
            result = await client.predict_sync("p-image", {"prompt": "test"})
        assert result["status"] == "succeeded"

    @respx.mock
    async def test_retries_on_503(self, client: PrunaClient) -> None:
        route = respx.post(f"{BASE}/v1/predictions")
        route.side_effect = [
            httpx.Response(503, text="Service unavailable"),
            httpx.Response(503, text="Service unavailable"),
            httpx.Response(200, json={"status": "succeeded"}),
        ]
        with patch("pruna_mcp_server.client._async_sleep"):
            result = await client.predict_sync("p-image", {"prompt": "test"})
        assert result["status"] == "succeeded"

    @respx.mock
    async def test_exhausts_retries(self, client: PrunaClient) -> None:
        respx.post(f"{BASE}/v1/predictions").mock(
            return_value=httpx.Response(503, text="down")
        )
        with patch("pruna_mcp_server.client._async_sleep"):
            with pytest.raises(PrunaAPIError, match="503"):
                await client.predict_sync("p-image", {"prompt": "test"})


class TestValidateFilePath:
    def test_nonexistent_file(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="File not found"):
            validate_file_path(tmp_path / "nope.jpg", allowed_dirs=[tmp_path])

    def test_file_too_large(self, tmp_path: Path) -> None:
        big = tmp_path / "big.bin"
        big.write_bytes(b"x" * (21 * 1024 * 1024))
        with pytest.raises(ValueError, match="too large"):
            validate_file_path(big, allowed_dirs=[tmp_path])

    def test_valid_file(self, tmp_path: Path) -> None:
        f = tmp_path / "ok.jpg"
        f.write_bytes(b"data")
        validate_file_path(f, allowed_dirs=[tmp_path])  # Should not raise

    def test_rejects_outside_allowed_dirs(self, tmp_path: Path) -> None:
        f = tmp_path / "secret.txt"
        f.write_bytes(b"data")
        # Without tmp_path in allowed_dirs, it should fail (unless under home/cwd)
        fake_allowed = [Path("/nonexistent/dir")]
        with pytest.raises(ValueError, match="outside allowed directories"):
            validate_file_path(f, allowed_dirs=fake_allowed)


class TestValidatePrunaUrl:
    def test_valid_relative_url(self) -> None:
        from pruna_mcp_server.client import _validate_pruna_url

        _validate_pruna_url("/v1/predictions/delivery/abc")  # Should not raise

    def test_rejects_path_traversal(self) -> None:
        from pruna_mcp_server.client import _validate_pruna_url

        with pytest.raises(ValueError):
            _validate_pruna_url("/v1/../../etc/passwd")

    def test_valid_absolute_url(self) -> None:
        from pruna_mcp_server.client import _validate_pruna_url

        _validate_pruna_url("https://api.pruna.ai/v1/delivery/abc")  # Should not raise

    def test_rejects_non_pruna_host(self) -> None:
        from pruna_mcp_server.client import _validate_pruna_url

        with pytest.raises(ValueError, match="does not point to api.pruna.ai"):
            _validate_pruna_url("https://evil.com/v1/file")


    def test_rejects_url_encoded_traversal(self) -> None:
        from pruna_mcp_server.client import _validate_pruna_url

        with pytest.raises(ValueError):
            _validate_pruna_url("/v1/%2e%2e/admin/keys")


class TestSymlinkProtection:
    def test_rejects_symlink(self, tmp_path: Path) -> None:
        target = tmp_path / "real.txt"
        target.write_bytes(b"data")
        link = tmp_path / "link.txt"
        link.symlink_to(target)
        with pytest.raises(ValueError, match="Symlinks are not allowed"):
            validate_file_path(link, allowed_dirs=[tmp_path])


class TestSensitiveDirDenylist:
    def test_rejects_ssh_dir(self, tmp_path: Path) -> None:
        ssh_dir = tmp_path / ".ssh"
        ssh_dir.mkdir()
        key_file = ssh_dir / "id_rsa"
        key_file.write_bytes(b"fake-key")
        with pytest.raises(ValueError, match="sensitive directories"):
            validate_file_path(key_file, allowed_dirs=[tmp_path])

    def test_rejects_aws_dir(self, tmp_path: Path) -> None:
        aws_dir = tmp_path / ".aws"
        aws_dir.mkdir()
        creds = aws_dir / "credentials"
        creds.write_bytes(b"fake-creds")
        with pytest.raises(ValueError, match="sensitive directories"):
            validate_file_path(creds, allowed_dirs=[tmp_path])


class TestRetryAfterHeader:
    @respx.mock
    async def test_respects_retry_after_header(self, client: PrunaClient) -> None:
        route = respx.post(f"{BASE}/v1/predictions")
        route.side_effect = [
            httpx.Response(429, text="Rate limited", headers={"Retry-After": "0.01"}),
            httpx.Response(200, json={"status": "succeeded"}),
        ]
        with patch("pruna_mcp_server.client._async_sleep") as mock_sleep:
            result = await client.predict_sync("p-image", {"prompt": "test"})
        assert result["status"] == "succeeded"
        mock_sleep.assert_called_once_with(0.01)
