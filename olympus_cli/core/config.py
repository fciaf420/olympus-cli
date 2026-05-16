"""Configuration management for Olympus CLI."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path


CONFIG_DIR = Path.home() / ".oly"
CONFIG_FILE = CONFIG_DIR / "config.json"


@dataclass
class Config:
    """Application configuration."""

    api_key: str = ""
    olympus_base_url: str = "https://api.olympusx.app"
    polymarket_base_url: str = "https://gamma-api.polymarket.com"

    @classmethod
    def load(cls) -> "Config":
        """Load config from file and environment.

        Priority: env var > config file > defaults.
        """
        config = cls()

        # Load from file
        if CONFIG_FILE.exists():
            try:
                data = json.loads(CONFIG_FILE.read_text())
                config.api_key = data.get("api_key", "")
                config.olympus_base_url = data.get(
                    "olympus_base_url", config.olympus_base_url
                )
                config.polymarket_base_url = data.get(
                    "polymarket_base_url", config.polymarket_base_url
                )
            except (json.JSONDecodeError, OSError):
                pass

        # Env var overrides file
        env_key = os.environ.get("OLY_API_KEY")
        if env_key:
            config.api_key = env_key

        return config

    def save(self) -> None:
        """Persist config to disk."""
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        data = {
            "api_key": self.api_key,
            "olympus_base_url": self.olympus_base_url,
            "polymarket_base_url": self.polymarket_base_url,
        }
        CONFIG_FILE.write_text(json.dumps(data, indent=2))

    @property
    def masked_key(self) -> str:
        """Return masked API key for display."""
        if not self.api_key:
            return "(not set)"
        if len(self.api_key) <= 8:
            return "****"
        return self.api_key[:4] + "…" + self.api_key[-4:]
