"""Data models for Olympus CLI."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Position:
    """A single portfolio position."""

    slug: str
    outcome: str
    shares: float
    avg_price: float
    current_price: float
    pnl: float
    pnl_percent: float
    condition_id: str = ""
    token_id: str = ""

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> "Position":
        return cls(
            slug=data.get("slug", ""),
            outcome=data.get("outcome", ""),
            shares=float(data.get("shares", 0)),
            avg_price=float(data.get("avgPrice", 0)),
            current_price=float(data.get("currentPrice", 0)),
            pnl=float(data.get("pnl", 0)),
            pnl_percent=float(data.get("pnlPercent", 0)),
            condition_id=data.get("conditionId", ""),
            token_id=data.get("tokenId", ""),
        )


@dataclass
class Portfolio:
    """Portfolio summary with positions."""

    balance: float
    equity: float
    pnl: float
    pnl_percent: float
    positions: list[Position] = field(default_factory=list)

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> "Portfolio":
        positions = [Position.from_api(p) for p in data.get("positions", [])]
        return cls(
            balance=float(data.get("balance", 0)),
            equity=float(data.get("equity", 0)),
            pnl=float(data.get("pnl", 0)),
            pnl_percent=float(data.get("pnlPercent", 0)),
            positions=positions,
        )


@dataclass
class TradeRequest:
    """A trade request to send to Olympus."""

    slug: str
    outcome: str
    side: str  # "buy" or "sell"
    amount_usd: float | None = None
    shares: float | None = None
    percent: float | None = None
    max_price: float | None = None
    min_price: float | None = None
    stop_loss: float | None = None
    take_profit: float | None = None
    condition_id: str = ""
    token_id: str = ""


@dataclass
class TradeResponse:
    """Response from a trade submission."""

    trade_id: str
    status: str
    message: str = ""

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> "TradeResponse":
        return cls(
            trade_id=data.get("tradeId", ""),
            status=data.get("status", ""),
            message=data.get("message", ""),
        )


@dataclass
class TradeStatus:
    """Status of a submitted trade."""

    trade_id: str
    status: str  # QUEUED, PROCESSING, SUCCEEDED, FAILED
    filled_price: float | None = None
    filled_shares: float | None = None
    error: str | None = None

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> "TradeStatus":
        return cls(
            trade_id=data.get("tradeId", ""),
            status=data.get("status", ""),
            filled_price=data.get("filledPrice"),
            filled_shares=data.get("filledShares"),
            error=data.get("error"),
        )

    @property
    def is_terminal(self) -> bool:
        """Whether the trade has reached a final state."""
        return self.status in ("SUCCEEDED", "FAILED")


@dataclass
class MarketOutcome:
    """A single outcome in a market."""

    name: str
    token_id: str
    price: float


@dataclass
class Market:
    """A Polymarket market."""

    slug: str
    question: str
    condition_id: str
    outcomes: list[MarketOutcome] = field(default_factory=list)
    volume: float = 0.0
    liquidity: float = 0.0
    end_date: str = ""
    active: bool = True
    closed: bool = False

    @classmethod
    def from_gamma(cls, data: dict[str, Any]) -> "Market":
        """Parse from Polymarket gamma API response."""
        outcomes: list[MarketOutcome] = []
        outcome_names = data.get("outcomes", "")
        if isinstance(outcome_names, str):
            outcome_names = [s.strip() for s in outcome_names.split(",") if s.strip()]

        outcome_prices_str = data.get("outcomePrices", "")
        if isinstance(outcome_prices_str, str):
            outcome_prices = [
                float(p) for p in outcome_prices_str.split(",") if p.strip()
            ]
        elif isinstance(outcome_prices_str, list):
            outcome_prices = [float(p) for p in outcome_prices_str]
        else:
            outcome_prices = []

        clobTokenIds = data.get("clobTokenIds", "")
        if isinstance(clobTokenIds, str):
            token_ids = [t.strip() for t in clobTokenIds.split(",") if t.strip()]
        elif isinstance(clobTokenIds, list):
            token_ids = [str(t) for t in clobTokenIds]
        else:
            token_ids = []

        for i, name in enumerate(outcome_names):
            price = outcome_prices[i] if i < len(outcome_prices) else 0.0
            token_id = token_ids[i] if i < len(token_ids) else ""
            outcomes.append(MarketOutcome(name=name, token_id=token_id, price=price))

        return cls(
            slug=data.get("slug", ""),
            question=data.get("question", ""),
            condition_id=data.get("conditionId", ""),
            outcomes=outcomes,
            volume=float(data.get("volume", 0)),
            liquidity=float(data.get("liquidity", 0)),
            end_date=data.get("endDate", ""),
            active=data.get("active", True),
            closed=data.get("closed", False),
        )
