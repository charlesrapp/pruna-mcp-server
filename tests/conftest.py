"""Shared test fixtures."""

from __future__ import annotations

import pytest

from pruna_mcp_server.config import PrunaConfig


@pytest.fixture()
def config() -> PrunaConfig:
    return PrunaConfig(api_key="test-key", max_retries=2, timeout=5.0)
