"""Polymarket Gamma and CLOB API clients."""

from __future__ import annotations

from typing import Any

import httpx

from olympus_cli.core.config import Config
from olympus_cli.core.models import (
    ClobMarketInfo,
    LastTradePrice,
    Market,
    MidpointPrice,
    OrderBook,
    PriceHistoryPoint,
    SpreadInfo,
)


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

    def get_events(
        self,
        limit: int = 20,
        tag: str | None = None,
        active: bool = True,
        closed: bool | None = None,
    ) -> list[dict]:
        """Fetch events from gamma API.

        Args:
            limit: Maximum events to return.
            tag: Optional tag filter (gamma `tag_slug`, e.g. "nba").
            active: Whether to filter for active events.
            closed: When set, filter for closed/open events. Pass False to
                only get open (still-tradable) events.

        Returns:
            List of event dicts.
        """
        params: dict[str, Any] = {"limit": limit, "active": str(active).lower()}
        if tag:
            params["tag_slug"] = tag
        if closed is not None:
            params["closed"] = str(closed).lower()
        data = self._request("/events", params=params)
        if isinstance(data, list):
            return data
        return []

    def get_event(self, slug_or_id: str) -> dict:
        """Fetch a single event by slug or ID.

        Args:
            slug_or_id: Event slug or numeric ID.

        Returns:
            Event dict.

        Raises:
            PolymarketError: If event not found.
        """
        # Try slug first
        data = self._request("/events", params={"slug": slug_or_id})
        if isinstance(data, list) and data:
            return data[0]
        # Try by ID
        if slug_or_id.isdigit():
            data = self._request(f"/events/{slug_or_id}")
            if data:
                return data
        raise PolymarketError(404, f"Event not found: {slug_or_id}")

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

    def get_spread(self, token_id: str) -> SpreadInfo:
        """Fetch spread info for a token.

        Args:
            token_id: The CLOB token ID.

        Returns:
            SpreadInfo with bid, ask, and spread.
        """
        data = self._request("/spread", params={"token_id": token_id})
        return SpreadInfo.from_clob(token_id, data)

    def get_last_trade(self, token_id: str) -> LastTradePrice:
        """Fetch last trade price for a token.

        Args:
            token_id: The CLOB token ID.

        Returns:
            LastTradePrice with price and timestamp.
        """
        data = self._request("/last-trade-price", params={"token_id": token_id})
        return LastTradePrice.from_clob(token_id, data)

    def get_neg_risk(self, token_id: str) -> bool:
        """Check if a token has neg risk.

        Args:
            token_id: The CLOB token ID.

        Returns:
            True if neg_risk is enabled.
        """
        data = self._request("/neg-risk", params={"token_id": token_id})
        return bool(data.get("neg_risk", False))

    def get_price_history(
        self, token_id: str, interval: str = "1d", fidelity: int = 60
    ) -> list[PriceHistoryPoint]:
        """Fetch price history from the CLOB API.

        Args:
            token_id: The CLOB token ID (asset ID).
            interval: Time interval (max, all, 1m, 1w, 1d, 6h, 1h).
            fidelity: Accuracy in minutes (default 60 = hourly points).

        Returns:
            List of PriceHistoryPoint.
        """
        data = self._request(
            "/prices-history",
            params={"market": token_id, "interval": interval, "fidelity": fidelity},
        )
        points: list[PriceHistoryPoint] = []
        history = data.get("history", []) if isinstance(data, dict) else []
        for point in history:
            points.append(
                PriceHistoryPoint(
                    timestamp=int(point.get("t", 0)),
                    price=float(point.get("p", 0)),
                )
            )
        return points

    def close(self) -> None:
        """Close the HTTP client."""
        self._client.close()
