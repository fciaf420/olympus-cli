"""Polymarket Data API client."""

from __future__ import annotations

from typing import Any

import httpx

from olympus_cli.core.config import Config
from olympus_cli.core.polymarket import PolymarketError


class DataApiClient:
    """Client for the Polymarket Data API (public, no auth)."""

    def __init__(self, config: Config | None = None):
        self.config = config or Config.load()
        self._client = httpx.Client(
            base_url=self.config.data_base_url,
            timeout=30.0,
        )

    def _request(self, path: str, params: dict[str, Any] | None = None) -> Any:
        """Make a GET request to the Data API."""
        resp = self._client.get(path, params=params)
        if resp.status_code >= 400:
            raise PolymarketError(resp.status_code, resp.text)
        return resp.json()

    def get_positions(self, wallet_address: str) -> Any:
        """Fetch open positions for a wallet.

        Args:
            wallet_address: The wallet address.

        Returns:
            Raw JSON response (list of positions).
        """
        return self._request("/positions", params={"user": wallet_address})

    def get_closed_positions(self, wallet_address: str) -> Any:
        """Fetch closed positions for a wallet.

        Args:
            wallet_address: The wallet address.

        Returns:
            Raw JSON response (list of closed positions).
        """
        return self._request("/closed-positions", params={"user": wallet_address})

    def get_portfolio_value(self, wallet_address: str) -> Any:
        """Fetch portfolio value for a wallet.

        Args:
            wallet_address: The wallet address.

        Returns:
            Raw JSON response with value info.
        """
        return self._request("/value", params={"user": wallet_address})

    def get_trades(self, wallet_address: str, limit: int = 50) -> Any:
        """Fetch trade history for a wallet.

        Args:
            wallet_address: The wallet address.
            limit: Maximum number of trades to return.

        Returns:
            Raw JSON response (list of trades).
        """
        return self._request(
            "/trades", params={"user": wallet_address, "limit": limit}
        )

    def get_activity(self, wallet_address: str) -> Any:
        """Fetch activity feed for a wallet.

        Args:
            wallet_address: The wallet address.

        Returns:
            Raw JSON response (activity feed).
        """
        return self._request("/activity", params={"user": wallet_address})

    def get_top_holders(self, condition_id: str) -> Any:
        """Fetch top holders for a market.

        Args:
            condition_id: The market condition ID.

        Returns:
            Raw JSON response (list of top holders).
        """
        return self._request("/holders", params={"market": condition_id})

    def get_open_interest(self, condition_id: str) -> Any:
        """Fetch open interest for a market.

        Args:
            condition_id: The market condition ID.

        Returns:
            Raw JSON response with open interest data.
        """
        return self._request("/oi", params={"market": condition_id})

    def get_leaderboard(
        self,
        period: str = "MONTH",
        order_by: str = "PNL",
        limit: int = 20,
        category: str = "OVERALL",
    ) -> Any:
        """Fetch the leaderboard.

        Args:
            period: Time period (DAY, WEEK, MONTH, ALL).
            order_by: Sort field (PNL, VOL).
            limit: Maximum entries to return (max 50).
            category: Market category (OVERALL, POLITICS, SPORTS, CRYPTO, etc.).

        Returns:
            Raw JSON response (list of leaderboard entries).
        """
        return self._request(
            "/v1/leaderboard",
            params={
                "timePeriod": period.upper(),
                "orderBy": order_by.upper(),
                "limit": min(limit, 50),
                "category": category.upper(),
            },
        )

    def close(self) -> None:
        """Close the HTTP client."""
        self._client.close()
