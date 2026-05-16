"""Data models for Olympus CLI."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class SpreadInfo:
    """Spread information for a token."""

    token_id: str
    spread: float
    bid: float
    ask: float

    @classmethod
    def from_clob(cls, token_id: str, data: dict[str, Any]) -> "SpreadInfo":
        return cls(
            token_id=token_id,
            spread=float(data.get("spread", 0)),
            bid=float(data.get("bid", 0)),
            ask=float(data.get("ask", 0)),
        )


@dataclass
class LastTradePrice:
    """Last trade price for a token."""

    token_id: str
    price: float
    timestamp: str

    @classmethod
    def from_clob(cls, token_id: str, data: dict[str, Any]) -> "LastTradePrice":
        return cls(
            token_id=token_id,
            price=float(data.get("price", 0)),
            timestamp=data.get("timestamp", ""),
        )


@dataclass
class PriceHistoryPoint:
    """A single point in price history."""

    timestamp: int
    price: float


@dataclass
class WalletPosition:
    """Position from the Data API."""

    market_slug: str
    title: str
    outcome: str
    size: float
    avg_price: float
    cur_price: float
    pnl: float
    cash_pnl: float


@dataclass
class TradeRecord:
    """A trade record from the Data API."""

    id: str
    market: str
    side: str
    outcome: str
    size: float
    price: float
    timestamp: str


@dataclass
class LeaderboardEntry:
    """An entry on the leaderboard."""

    rank: int
    address: str
    name: str
    pnl: float
    volume: float
    positions: int


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
    current_value: float = 0.0
    condition_id: str = ""
    token_id: str = ""
    market_id: str = ""
    redeemable: bool = False

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> "Position":
        return cls(
            slug=data.get("slug", ""),
            outcome=data.get("title", ""),
            shares=float(data.get("size", 0)),
            avg_price=float(data.get("avgPrice", 0)),
            current_price=float(data.get("curPrice", 0)),
            pnl=float(data.get("cashPnl", 0)),
            pnl_percent=float(data.get("percentPnl", 0)),
            current_value=float(data.get("currentValue", 0)),
            condition_id=data.get("conditionId", ""),
            token_id=data.get("asset", ""),
            market_id=data.get("marketId", ""),
            redeemable=data.get("redeemable", False),
        )


@dataclass
class Portfolio:
    """Portfolio summary with positions."""

    balance: float
    equity: float
    positions_value: float
    position_count: int
    wallet_address: str = ""
    positions: list[Position] = field(default_factory=list)
    calculated_at: str = ""

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> "Portfolio":
        positions = [Position.from_api(p) for p in data.get("positions", [])]
        return cls(
            balance=float(data.get("pusdBalance", 0)),
            equity=float(data.get("equityUsd", 0)),
            positions_value=float(data.get("positionsValueUsd", 0)),
            position_count=int(data.get("positionCount", 0)),
            wallet_address=data.get("walletAddress", ""),
            positions=positions,
            calculated_at=data.get("calculatedAt", ""),
        )



@dataclass
class TradeRequest:
    """A trade request to send to Olympus."""

    side: str  # "BUY" or "SELL"
    token_id: str
    condition_id: str
    market_title: str
    outcome_label: str = ""
    market_id: str | None = None
    market_slug: str | None = None
    # Buy fields
    amount_usd: float | None = None
    max_price: float | None = None
    stop_loss_percent: float | None = None
    take_profit_percent: float | None = None
    # Sell fields
    sell_spec: dict[str, Any] | None = None
    min_price: float | None = None

    def to_payload(self) -> dict[str, Any]:
        """Build the API request payload."""
        payload: dict[str, Any] = {
            "side": self.side.upper(),
            "tokenId": self.token_id,
            "conditionId": self.condition_id,
            "marketTitle": self.market_title,
        }
        if self.market_id:
            payload["marketId"] = self.market_id
        if self.market_slug:
            payload["marketSlug"] = self.market_slug

        if self.side.upper() == "BUY":
            payload["outcomeLabel"] = self.outcome_label
            if self.amount_usd is not None:
                payload["amountUsd"] = self.amount_usd
            if self.max_price is not None:
                payload["maxPrice"] = self.max_price
            if self.stop_loss_percent is not None:
                payload["stopLossPercent"] = self.stop_loss_percent
            if self.take_profit_percent is not None:
                payload["takeProfitPercent"] = self.take_profit_percent
        else:
            # SELL
            if self.sell_spec:
                payload["sellSpec"] = self.sell_spec
            if self.min_price is not None:
                payload["minPrice"] = self.min_price

        return payload


@dataclass
class TradeResponse:
    """Response from a trade submission."""

    trade_id: str
    status: str
    success: bool = True

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> "TradeResponse":
        return cls(
            trade_id=data.get("tradeId", ""),
            status=data.get("status", ""),
            success=data.get("success", True),
        )


@dataclass
class TradeStatus:
    """Status of a submitted trade."""

    trade_id: str
    status: str  # QUEUED, PROCESSING, SUCCEEDED, FAILED
    side: str = ""
    market_title: str = ""
    outcome_label: str = ""
    requested_amount_usd: float | None = None
    filled_shares: float | None = None
    filled_price: float | None = None
    spent_usd: float | None = None
    order_hash: str | None = None
    transaction_hash: str | None = None
    error_code: str | None = None
    error_message: str | None = None
    created_at: str = ""
    completed_at: str = ""

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> "TradeStatus":
        return cls(
            trade_id=data.get("tradeId", ""),
            status=data.get("status", ""),
            side=data.get("side", ""),
            market_title=data.get("marketTitle", ""),
            outcome_label=data.get("outcomeLabel", ""),
            requested_amount_usd=data.get("requestedAmountUsd"),
            filled_shares=data.get("filledSharesNormalized"),
            filled_price=data.get("filledPrice"),
            spent_usd=data.get("spentUsd"),
            order_hash=data.get("orderHash"),
            transaction_hash=data.get("transactionHash"),
            error_code=data.get("errorCode"),
            error_message=data.get("errorMessage"),
            created_at=data.get("createdAt", ""),
            completed_at=data.get("completedAt", ""),
        )

    @property
    def is_terminal(self) -> bool:
        """Whether the trade has reached a final state."""
        return self.status in ("SUCCEEDED", "FAILED")


@dataclass
class ClobToken:
    """A token in CLOB market info."""

    token_id: str
    outcome: str


@dataclass
class ClobMarketInfo:
    """CLOB API market metadata (tick size, fees, etc.)."""

    min_order_size: float = 0.0
    min_tick_size: float = 0.0
    maker_fee_bps: float = 0.0
    taker_fee_bps: float = 0.0
    rfq_enabled: bool = False
    fee_rate: float = 0.0
    min_order_age_seconds: float = 0.0
    tokens: list[ClobToken] = field(default_factory=list)

    @classmethod
    def from_clob(cls, data: dict[str, Any]) -> "ClobMarketInfo":
        """Parse from CLOB API response."""
        tokens = []
        for t in data.get("t", []):
            tokens.append(ClobToken(token_id=t.get("t", ""), outcome=t.get("o", "")))

        fee_details = data.get("fd", {})
        fee_rate = float(fee_details.get("r", 0)) if fee_details else 0.0

        return cls(
            min_order_size=float(data.get("mos", 0)),
            min_tick_size=float(data.get("mts", 0)),
            maker_fee_bps=float(data.get("mbf", 0)),
            taker_fee_bps=float(data.get("tbf", 0)),
            rfq_enabled=bool(data.get("rfqe", False)),
            fee_rate=fee_rate,
            min_order_age_seconds=float(data.get("oas", 0)),
            tokens=tokens,
        )


@dataclass
class OrderBookLevel:
    """A single price level in the order book."""

    price: float
    size: float


@dataclass
class OrderBook:
    """Order book for a token."""

    token_id: str
    bids: list[OrderBookLevel] = field(default_factory=list)
    asks: list[OrderBookLevel] = field(default_factory=list)

    @classmethod
    def from_clob(cls, token_id: str, data: dict[str, Any]) -> "OrderBook":
        """Parse from CLOB book endpoint response."""
        bids = [
            OrderBookLevel(
                price=float(b.get("price", b.get("p", 0))),
                size=float(b.get("size", b.get("s", 0))),
            )
            for b in data.get("bids", [])
        ]
        asks = [
            OrderBookLevel(
                price=float(a.get("price", a.get("p", 0))),
                size=float(a.get("size", a.get("s", 0))),
            )
            for a in data.get("asks", [])
        ]
        return cls(token_id=token_id, bids=bids, asks=asks)


@dataclass
class MidpointPrice:
    """Midpoint price for a token."""

    token_id: str
    midpoint: float = 0.0

    @classmethod
    def from_clob(cls, token_id: str, data: dict[str, Any]) -> "MidpointPrice":
        """Parse from CLOB midpoint endpoint response."""
        return cls(
            token_id=token_id,
            midpoint=float(data.get("mid", data.get("midpoint", 0))),
        )


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
    market_id: str = ""
    outcomes: list[MarketOutcome] = field(default_factory=list)
    volume: float = 0.0
    liquidity: float = 0.0
    end_date: str = ""
    active: bool = True
    closed: bool = False
    enable_order_book: bool = False
    accepting_orders: bool = False

    @classmethod
    def from_gamma(cls, data: dict[str, Any]) -> "Market":
        """Parse from Polymarket gamma API response."""
        outcomes: list[MarketOutcome] = []
        outcome_names = data.get("outcomes", "")
        if isinstance(outcome_names, str):
            import json as _json
            try:
                outcome_names = _json.loads(outcome_names)
            except Exception:
                outcome_names = [s.strip() for s in outcome_names.split(",") if s.strip()]
        elif not isinstance(outcome_names, list):
            outcome_names = []

        outcome_prices_str = data.get("outcomePrices", "")
        if isinstance(outcome_prices_str, str):
            try:
                import json as _json
                outcome_prices = [float(p) for p in _json.loads(outcome_prices_str)]
            except Exception:
                outcome_prices = [float(p) for p in outcome_prices_str.split(",") if p.strip()]
        elif isinstance(outcome_prices_str, list):
            outcome_prices = [float(p) for p in outcome_prices_str]
        else:
            outcome_prices = []

        clobTokenIds = data.get("clobTokenIds", "")
        if isinstance(clobTokenIds, str):
            try:
                import json as _json
                token_ids = _json.loads(clobTokenIds)
            except Exception:
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
            market_id=str(data.get("id", "")),
            outcomes=outcomes,
            volume=float(data.get("volume", 0)),
            liquidity=float(data.get("liquidity", 0)),
            end_date=data.get("endDate", ""),
            active=data.get("active", True),
            closed=data.get("closed", False),
            enable_order_book=data.get("enableOrderBook", False),
            accepting_orders=data.get("acceptingOrders", False),
        )
