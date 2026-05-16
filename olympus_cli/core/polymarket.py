"""Polymarket Gamma API client."""

from __future__ import annotations

from typing import Any

import httpx

from olympus_cli.core.config import Config
from olympus_cli.core.models import Market


class PolymarketError(Exception):
    """Raised when the Polymarket API returns an error."""

    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        self.message = message
        super().__init__(f"Polymarket API error {status_code}: {message}")


class PolymarketClient:
    """Client for the Polymarket Gamma API (no auth required)."""

    def __init__(self, config: Config | None = None):
        self.config = config or Config.load()
        self._client = httpx.Client(
            base_url=self.config.polymarket_base_url,
            timeout=30.0,
        )

    def _request(self, path: str, params: dict[str, Any] | None = None) -> Any:
        """Make a GET request to the gamma API."""
        resp = self._client.get(path, params=params)
        if resp.status_code >= 400:
            raise PolymarketError(resp.status_code, resp.text)
        return resp.json()

    def get_market(self, slug: str) -> Market:
        """Fetch a market by its slug.

        Args:
            slug: The market slug (URL identifier).

        Returns:
            Market object with outcomes, prices, and metadata.

        Raises:
            PolymarketError: If market not found or API error.
        """
        data = self._request("/markets", params={"slug": slug})
        # API returns a list; take first match
        if isinstance(data, list):
            if not data:
                raise PolymarketError(404, f"Market not found: {slug}")
            return Market.from_gamma(data[0])
        return Market.from_gamma(data)

    def search_markets(self, query: str, limit: int = 20) -> list[Market]:
        """Search active markets by text query.

        Args:
            query: Search text (e.g. "solana", "election").
            limit: Maximum results to return.

        Returns:
            List of matching Market objects.
        """
        data = self._request(
            "/markets",
            params={
                "active": "true",
                "closed": "false",
                "_q": query,
                "limit": limit,
            },
        )
        if isinstance(data, list):
            return [Market.from_gamma(m) for m in data]
        return []

    def list_active_markets(self, limit: int = 20) -> list[Market]:
        """List active markets with order books.

        Args:
            limit: Maximum results to return.

        Returns:
            List of active Market objects.
        """
        data = self._request(
            "/markets",
            params={
                "active": "true",
                "closed": "false",
                "enableOrderBook": "true",
                "limit": limit,
            },
        )
        if isinstance(data, list):
            return [Market.from_gamma(m) for m in data]
        return []

    def close(self) -> None:
        """Close the HTTP client."""
        self._client.close()
