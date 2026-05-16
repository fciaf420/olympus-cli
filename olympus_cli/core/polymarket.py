"""Polymarket Gamma and CLOB API clients."""

from __future__ import annotations

from typing import Any

import httpx

from olympus_cli.core.config import Config
from olympus_cli.core.models import ClobMarketInfo, Market, MidpointPrice, OrderBook


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
        """Search markets using the /public-search endpoint.

        Also accepts Polymarket URLs directly for convenience.

        Args:
            query: Search text, slug, or polymarket.com URL.
            limit: Maximum results to return.

        Returns:
            List of matching Market objects.
        """
        # If query is a Polymarket URL, extract the slug
        if "polymarket.com" in query:
            slug = query.rstrip("/").split("/")[-1]
            try:
                return [self.get_market(slug)]
            except PolymarketError:
                pass

        results: list[Market] = []
        seen_slugs: set[str] = set()

        # Use the official /public-search endpoint (proper full-text search)
        try:
            data = self._request(
                "/public-search",
                params={"q": query, "limit_per_type": limit},
            )
            if isinstance(data, dict):
                for ev in data.get("events", []) or []:
                    for m_data in ev.get("markets", []):
                        m = Market.from_gamma(m_data)
                        if m.slug not in seen_slugs:
                            seen_slugs.add(m.slug)
                            results.append(m)
        except PolymarketError:
            pass

        # Fallback: try direct slug lookup if no results
        if not results:
            try:
                data = self._request("/markets", params={"slug": query})
                if isinstance(data, list) and data:
                    results.append(Market.from_gamma(data[0]))
            except PolymarketError:
                pass

        return results[:limit]

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


class ClobClient:
    """Client for the Polymarket CLOB API."""

    def __init__(self, config: Config | None = None):
        self.config = config or Config.load()
        self._client = httpx.Client(
            base_url=self.config.clob_base_url,
            timeout=30.0,
        )

    def _request(self, path: str, params: dict[str, Any] | None = None) -> Any:
        """Make a GET request to the CLOB API."""
        resp = self._client.get(path, params=params)
        if resp.status_code >= 400:
            raise PolymarketError(resp.status_code, resp.text)
        return resp.json()

    def get_market_info(self, condition_id: str) -> ClobMarketInfo:
        """Fetch CLOB market info by condition ID.

        Args:
            condition_id: The market's condition ID.

        Returns:
            ClobMarketInfo with tick size, fees, tokens, etc.
        """
        data = self._request(f"/clob-markets/{condition_id}")
        return ClobMarketInfo.from_clob(data)

    def get_order_book(self, token_id: str) -> OrderBook:
        """Fetch order book for a token.

        Args:
            token_id: The CLOB token ID.

        Returns:
            OrderBook with bids and asks.
        """
        data = self._request("/book", params={"token_id": token_id})
        return OrderBook.from_clob(token_id, data)

    def get_midpoint(self, token_id: str) -> MidpointPrice:
        """Fetch midpoint price for a token.

        Args:
            token_id: The CLOB token ID.

        Returns:
            MidpointPrice with the current midpoint.
        """
        data = self._request("/midpoint", params={"token_id": token_id})
        return MidpointPrice.from_clob(token_id, data)

    def close(self) -> None:
        """Close the HTTP client."""
        self._client.close()
