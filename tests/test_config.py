"""Tests for configuration loading."""

from __future__ import annotations

from pathlib import Path

import pytest

from pruna_mcp_server.config import PrunaConfig, load_config


class TestPrunaConfig:
    def test_valid_config(self) -> None:
        config = PrunaConfig(api_key="test-key")
        assert config.api_key == "test-key"
        assert config.output_dir == Path("./pruna-output")
        assert config.poll_interval == 2.0
        assert config.timeout == 120.0
        assert config.max_retries == 3

    def test_missing_api_key_raises(self) -> None:
        with pytest.raises(ValueError, match="PRUNA_API_KEY"):
            PrunaConfig(api_key="")

    def test_custom_values(self) -> None:
        config = PrunaConfig(
            api_key="key",
            output_dir=Path("/tmp/out"),
            poll_interval=5.0,
            timeout=60.0,
            max_retries=1,
        )
        assert config.output_dir == Path("/tmp/out")
        assert config.poll_interval == 5.0
        assert config.timeout == 60.0
        assert config.max_retries == 1


class TestLoadConfig:
    def test_load_from_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("PRUNA_API_KEY", "env-key")
        monkeypatch.setenv("PRUNA_OUTPUT_DIR", "/tmp/test")
        monkeypatch.setenv("PRUNA_POLL_INTERVAL", "5")
        monkeypatch.setenv("PRUNA_TIMEOUT", "60")
        monkeypatch.setenv("PRUNA_MAX_RETRIES", "1")
        config = load_config()
        assert config.api_key == "env-key"
        assert config.output_dir == Path("/tmp/test")
        assert config.poll_interval == 5.0
        assert config.timeout == 60.0
        assert config.max_retries == 1

    def test_load_fails_without_key(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("PRUNA_API_KEY", raising=False)
        with pytest.raises(ValueError, match="PRUNA_API_KEY"):
            load_config()
