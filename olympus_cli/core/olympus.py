"""Olympus Trading API client."""

from __future__ import annotations

import time
from dataclasses import asdict
from typing import Any

import httpx

from olympus_cli.core.config import Config
from olympus_cli.core.models import (
    Portfolio,
    TradeRequest,
    TradeResponse,
    TradeStatus,
)


class OlympusError(Exception):
    """Raised when the Olympus API returns an error."""

    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        self.message = message
        super().__init__(f"Olympus API error {status_code}: {message}")


class OlympusClient:
    """Client for the Olympus Trading API."""

    def __init__(self, config: Config | None = None):
        self.config = config or Config.load()
        if not self.config.api_key:
            raise OlympusError(401, "API key not configured. Run: oly config set-key")
        self._client = httpx.Client(
            base_url=self.config.olympus_base_url,
            headers={"Authorization": f"Bearer {self.config.api_key}"},
            timeout=30.0,
        )

    def _request(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        """Make an API request and handle errors."""
        resp = self._client.request(method, path, **kwargs)
        if resp.status_code >= 400:
            try:
                body = resp.json()
                msg = body.get("error", body.get("message", resp.text))
            except Exception:
                msg = resp.text
            raise OlympusError(resp.status_code, msg)
        return resp.json()

    def get_portfolio(self) -> Portfolio:
        """Fetch current portfolio (balance, positions, PnL).

        Returns:
            Portfolio object with positions and summary stats.
        """
        data = self._request("GET", "/v1/portfolio")
        return Portfolio.from_api(data)

    def submit_trade(self, trade: TradeRequest) -> TradeResponse:
        """Submit a buy or sell trade.

        Args:
            trade: TradeRequest with all trade parameters.

        Returns:
            TradeResponse with the trade ID and initial status.
        """
        payload: dict[str, Any] = {
            "slug": trade.slug,
            "outcome": trade.outcome,
            "side": trade.side,
            "conditionId": trade.condition_id,
            "tokenId": trade.token_id,
        }
        if trade.side == "buy":
            payload["amountUsd"] = trade.amount_usd
            if trade.max_price is not None:
                payload["maxPrice"] = trade.max_price
            if trade.stop_loss is not None:
                payload["stopLoss"] = trade.stop_loss
            if trade.take_profit is not None:
                payload["takeProfit"] = trade.take_profit
        else:
            # Sell
            if trade.shares is not None:
                payload["sellSpec"] = {"type": "shares", "value": trade.shares}
            else:
                payload["sellSpec"] = {"type": "percent", "value": trade.percent or 100}
            if trade.min_price is not None:
                payload["minPrice"] = trade.min_price

        data = self._request("POST", "/v1/trade", json=payload)
        return TradeResponse.from_api(data)

    def get_trade_status(self, trade_id: str) -> TradeStatus:
        """Check the status of a submitted trade.

        Args:
            trade_id: The trade ID returned from submit_trade.

        Returns:
            TradeStatus with current state and fill info.
        """
        data = self._request("GET", f"/v1/trades/{trade_id}")
        return TradeStatus.from_api(data)

    def watch_trade(
        self, trade_id: str, poll_interval: float = 2.0, max_wait: float = 120.0
    ) -> TradeStatus:
        """Poll a trade until it reaches a terminal state.

        Args:
            trade_id: The trade ID to watch.
            poll_interval: Seconds between polls.
            max_wait: Maximum seconds to wait before giving up.

        Returns:
            Final TradeStatus (SUCCEEDED or FAILED).

        Raises:
            TimeoutError: If max_wait is exceeded.
        """
        start = time.time()
        while True:
            status = self.get_trade_status(trade_id)
            if status.is_terminal:
                return status
            elapsed = time.time() - start
            if elapsed >= max_wait:
                raise TimeoutError(
                    f"Trade {trade_id} still {status.status} after {max_wait}s"
                )
            time.sleep(poll_interval)

    def close(self) -> None:
        """Close the HTTP client."""
        self._client.close()
