"""Olympus Trading API client."""

from __future__ import annotations

import time
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
        if resp.status_code == 429:
            retry_after = resp.headers.get("Retry-After", "?")
            raise OlympusError(429, f"Rate limit exceeded. Retry after {retry_after}s")
        if resp.status_code >= 400:
            try:
                body = resp.json()
                msg = body.get("message", body.get("error", resp.text))
            except Exception:
                msg = resp.text
            raise OlympusError(resp.status_code, msg)
        return resp.json()

    def get_portfolio(self) -> Portfolio:
        """Fetch current portfolio (balance, positions, PnL)."""
        data = self._request("GET", "/v1/portfolio")
        return Portfolio.from_api(data)

    def submit_trade(self, trade: TradeRequest) -> TradeResponse:
        """Submit a buy or sell trade."""
        payload = trade.to_payload()
        data = self._request("POST", "/v1/trade", json=payload)
        return TradeResponse.from_api(data)

    def get_trade_status(self, trade_id: str) -> TradeStatus:
        """Check the status of a submitted trade."""
        data = self._request("GET", f"/v1/trades/{trade_id}")
        return TradeStatus.from_api(data)

    def watch_trade(
        self, trade_id: str, poll_interval: float = 2.0, max_wait: float = 120.0
    ) -> TradeStatus:
        """Poll a trade until it reaches a terminal state."""
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
