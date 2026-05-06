"""Tests for model registry."""

from __future__ import annotations

import pytest

from pruna_mcp_server.models import get_all_models, get_model, validate_model


class TestModelRegistry:
    def test_total_model_count(self) -> None:
        assert len(get_all_models()) == 18

    def test_category_counts(self) -> None:
        assert len(get_all_models("text-to-image")) == 10
        assert len(get_all_models("editing")) == 3
        assert len(get_all_models("upscale")) == 1
        assert len(get_all_models("video")) == 4

    def test_get_model_exists(self) -> None:
        model = get_model("p-image")
        assert model is not None
        assert model.name == "p-image"
        assert model.category == "text-to-image"
        assert model.supports_sync is True

    def test_get_model_not_found(self) -> None:
        assert get_model("nonexistent") is None

    def test_video_models_no_sync(self) -> None:
        for m in get_all_models("video"):
            assert m.supports_sync is False

    def test_validate_model_ok(self) -> None:
        model = validate_model("p-image", "text-to-image")
        assert model.name == "p-image"

    def test_validate_model_wrong_category(self) -> None:
        with pytest.raises(ValueError, match="not text-to-image"):
            validate_model("p-video", "text-to-image")

    def test_validate_model_not_found(self) -> None:
        with pytest.raises(ValueError, match="Unknown model"):
            validate_model("fake-model", "text-to-image")

    def test_all_models_have_required_fields(self) -> None:
        for m in get_all_models():
            assert m.name
            assert m.category
            assert m.description
            assert m.pricing
            assert m.rate_limit
            assert len(m.parameters) > 0
