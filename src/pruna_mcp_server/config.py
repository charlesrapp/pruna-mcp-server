"""Configuration for pruna-mcp-server."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class PrunaConfig:
    """Server configuration loaded from environment variables."""

    api_key: str
    output_dir: Path = field(default_factory=lambda: Path("./pruna-output"))
    poll_interval: float = 2.0
    timeout: float = 120.0
    max_retries: int = 3

    def __post_init__(self) -> None:
        if not self.api_key:
            raise ValueError(
                "PRUNA_API_KEY environment variable is required. "
                "Get your API key from https://pruna.ai"
            )


def load_config() -> PrunaConfig:
    """Load configuration from environment variables (and .env file if present)."""
    from dotenv import load_dotenv

    load_dotenv()
    api_key = os.environ.get("PRUNA_API_KEY", "")
    output_dir = Path(os.environ.get("PRUNA_OUTPUT_DIR", "./pruna-output"))
    poll_interval = float(os.environ.get("PRUNA_POLL_INTERVAL", "2"))
    timeout = float(os.environ.get("PRUNA_TIMEOUT", "120"))
    max_retries = int(os.environ.get("PRUNA_MAX_RETRIES", "3"))
    return PrunaConfig(
        api_key=api_key,
        output_dir=output_dir,
        poll_interval=poll_interval,
        timeout=timeout,
        max_retries=max_retries,
    )
