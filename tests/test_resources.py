"""Tests for MCP resources."""

from __future__ import annotations

import json

from pruna_mcp_server.server import resource_model_detail, resource_models


class TestResourceModels:
    def test_returns_all_models(self) -> None:
        data = json.loads(resource_models())
        assert len(data["models"]) == 18

    def test_model_has_fields(self) -> None:
        data = json.loads(resource_models())
        m = data["models"][0]
        for field in ("name", "category", "description", "pricing", "rate_limit", "supports_sync", "parameters"):
            assert field in m


class TestResourceModelDetail:
    def test_existing_model(self) -> None:
        data = json.loads(resource_model_detail("p-image"))
        assert data["name"] == "p-image"
        assert data["category"] == "text-to-image"

    def test_unknown_model(self) -> None:
        data = json.loads(resource_model_detail("nonexistent"))
        assert "error" in data
