"""Pruna AI API client with retry and security hardening."""

from __future__ import annotations

import random
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse

import httpx

from pruna_mcp_server.config import PrunaConfig

_RETRYABLE_CODES = {429, 502, 503, 504}
_BASE_URL = "https://api.pruna.ai"


class PrunaAPIError(Exception):
    """Error from the Pruna API."""

    def __init__(self, status_code: int, message: str) -> None:
        self.status_code = status_code
        super().__init__(f"Pruna API error {status_code}: {message}")


class PrunaClient:
    """Async client for the Pruna AI API."""

    def __init__(self, config: PrunaConfig) -> None:
        self._config = config
        self._headers = {
            "apikey": config.api_key,
            "Content-Type": "application/json",
        }

    def _client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            base_url=_BASE_URL,
            headers=self._headers,
            timeout=self._config.timeout,
            verify=True,
        )

    async def _request_with_retry(
        self,
        method: str,
        url: str,
        **kwargs: Any,
    ) -> httpx.Response:
        """Execute an HTTP request with exponential backoff retry."""
        last_exc: Exception | None = None
        for attempt in range(self._config.max_retries + 1):
            async with self._client() as client:
                resp = await client.request(method, url, **kwargs)
            if resp.status_code not in _RETRYABLE_CODES:
                return resp
            last_exc = PrunaAPIError(resp.status_code, resp.text)
            if attempt < self._config.max_retries:
                retry_after = resp.headers.get("Retry-After")
                if retry_after:
                    delay = float(retry_after)
                else:
                    delay = min(2**attempt + random.random(), 30.0)
                await _async_sleep(delay)
        raise last_exc  # type: ignore[misc]

    async def predict_sync(
        self, model: str, input_data: dict[str, Any]
    ) -> dict[str, Any]:
        """Submit a sync prediction (Try-Sync: true). Returns result directly."""
        headers = {"Model": model, "Try-Sync": "true"}
        resp = await self._request_with_retry(
            "POST", "/v1/predictions", json={"input": input_data}, headers=headers
        )
        _check_response(resp)
        return resp.json()  # type: ignore[no-any-return]

    async def predict_async(
        self, model: str, input_data: dict[str, Any]
    ) -> dict[str, Any]:
        """Submit an async prediction. Returns prediction metadata with get_url."""
        headers = {"Model": model}
        resp = await self._request_with_retry(
            "POST", "/v1/predictions", json={"input": input_data}, headers=headers
        )
        _check_response(resp)
        return resp.json()  # type: ignore[no-any-return]

    async def poll_status(self, prediction_id: str) -> dict[str, Any]:
        """Check prediction status."""
        resp = await self._request_with_retry(
            "GET", f"/v1/predictions/status/{prediction_id}"
        )
        _check_response(resp)
        return resp.json()  # type: ignore[no-any-return]

    async def download(self, delivery_url: str, output_path: Path) -> Path:
        """Download generated content to a local file.

        Validates the URL points to api.pruna.ai before fetching.
        Uses a separate client without auth headers to avoid leaking the API key.
        """
        _validate_pruna_url(delivery_url)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        async with httpx.AsyncClient(
            base_url=_BASE_URL, timeout=self._config.timeout
        ) as client:
            resp = await client.get(delivery_url)
        _check_response(resp)
        output_path.write_bytes(resp.content)
        return output_path

    async def upload_file(
        self, file_path: Path, allowed_dirs: list[Path] | None = None
    ) -> dict[str, Any]:
        """Upload a local file to Pruna.

        Validates path security before uploading.
        """
        validate_file_path(file_path, allowed_dirs=allowed_dirs)
        content = file_path.read_bytes()
        async with httpx.AsyncClient(
            base_url=_BASE_URL,
            headers={"apikey": self._config.api_key},
            timeout=self._config.timeout,
        ) as client:
            resp = await client.post(
                "/v1/files",
                files={"content": (file_path.name, content)},
            )
        _check_response(resp)
        return resp.json()  # type: ignore[no-any-return]


def validate_file_path(
    file_path: Path, allowed_dirs: list[Path] | None = None
) -> None:
    """Validate a file path for security (path traversal protection).

    Raises ValueError if the path is unsafe.
    """
    if file_path.is_symlink():
        raise ValueError(f"Symlinks are not allowed: {file_path}")
    resolved = file_path.resolve()
    if not resolved.exists():
        raise ValueError(f"File not found: {file_path}")
    _sensitive = {".ssh", ".gnupg", ".aws", ".env", ".git"}
    if any(part in _sensitive for part in resolved.parts):
        raise ValueError("Access to sensitive directories is denied")
    dirs = [Path.home().resolve(), Path.cwd().resolve()]
    if allowed_dirs:
        dirs.extend(d.resolve() for d in allowed_dirs)
    resolved_str = str(resolved)
    if not any(resolved_str.startswith(str(d)) for d in dirs):
        raise ValueError(
            f"Path '{file_path}' resolves outside allowed directories. "
            "Files must be within your home directory or current working directory."
        )
    max_size = 20 * 1024 * 1024  # 20MB
    if resolved.stat().st_size > max_size:
        raise ValueError(
            f"File too large: {resolved.stat().st_size} bytes (max 20MB)"
        )


def _validate_pruna_url(url: str) -> None:
    """Validate that a URL points to the Pruna API."""
    parsed = urlparse(url)
    if parsed.scheme != "https" or not parsed.hostname:
        # Allow relative URLs (delivery paths from Pruna)
        decoded = unquote(url)
        if decoded.startswith("/v1/") and ".." not in decoded:
            return
        raise ValueError(f"Invalid URL scheme: {url}")
    if parsed.hostname != "api.pruna.ai":
        raise ValueError(
            f"URL does not point to api.pruna.ai: {url}"
        )


def _check_response(resp: httpx.Response) -> None:
    """Raise PrunaAPIError for non-2xx responses."""
    if resp.status_code >= 400:
        safe_msg = resp.text[:200] if resp.text else "Unknown error"
        raise PrunaAPIError(resp.status_code, safe_msg)


async def _async_sleep(seconds: float) -> None:
    """Async sleep — extracted for testability."""
    import asyncio
    await asyncio.sleep(seconds)
