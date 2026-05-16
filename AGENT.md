# Agent Integration Guide

> **For AI agents, LLMs, and automated systems.**
> If you are an AI agent reading this, everything below tells you how to install, authenticate, and use this CLI as a tool.

## Install (one command)

```bash
uv tool install git+https://github.com/fciaf420/olympus-cli.git --force
```

The binary is installed to `~/.local/bin/oly`. If not on PATH, use the full path.

Requires: Python 3.10+, [uv](https://docs.astral.sh/uv/) (`curl -LsSf https://astral.sh/uv/install.sh | sh`)

## Authentication

Before using Olympus commands (portfolio, buy, sell, status, watch), set the API key:

```bash
mkdir -p ~/.oly
echo '{"api_key": "YOUR_OLYMPUS_API_KEY"}' > ~/.oly/config.json
```

Polymarket commands (search, market, orderbook, price) require NO authentication.

## Output Format

All commands output **JSON to stdout** when not a TTY (i.e., when called from scripts/agents). Errors go to stderr as `{"error": "message"}`. Exit code 1 on failure.

## Command Reference

### Read-only commands (no auth needed)

| Command | Args | Description |
|---------|------|-------------|
| `oly search <query>` | `--limit N` | Search markets. Returns `[{slug, question, condition_id, market_id, outcomes, volume, enable_order_book, accepting_orders}]` |
| `oly market <slug>` | | Full market detail + CLOB info (tick size, fees). Returns `{slug, question, condition_id, outcomes, clob_info}` |
| `oly orderbook <slug> <outcome>` | | Order book. Returns `{bids: [{price, size}], asks: [{price, size}]}` |
| `oly price <slug>` | | Midpoint prices for all outcomes. Returns `[{outcome, token_id, midpoint}]` |

### Account commands (auth required)

| Command | Args | Description |
|---------|------|-------------|
| `oly portfolio` | | Balance + positions. Returns `{balance, equity, positions_value, position_count, wallet_address, positions}` |
| `oly buy <slug> <outcome> <usd>` | `--max-price 0.6 --stop-loss 20 --take-profit 50` | Buy position. Returns `{trade_id, status, success}` |
| `oly sell <slug> <outcome>` | `--percent 100 --shares N --min-price 0.5` | Sell position. Returns `{trade_id, status, success}` |
| `oly status <trade_id>` | | Check trade. Returns `{trade_id, status, side, filled_shares, filled_price, spent_usd}` |
| `oly watch <trade_id>` | `--interval 2 --timeout 120` | Poll until SUCCEEDED/FAILED. Returns same as status. |

### Typical agent workflow

```bash
# 1. Check balance
oly portfolio

# 2. Find a market
oly search "bitcoin"

# 3. Check price and order book
oly price will-bitcoin-hit-150k
oly orderbook will-bitcoin-hit-150k Yes

# 4. Buy
oly buy will-bitcoin-hit-150k Yes 10 --max-price 0.60

# 5. Watch the trade
oly watch <trade_id_from_step_4>

# 6. Check updated portfolio
oly portfolio

# 7. Sell when ready
oly sell will-bitcoin-hit-150k Yes --percent 100
```

### Key fields for trading

When buying, you need the **slug** and **outcome name** (Yes/No/Up/Down). The CLI resolves tokenId and conditionId automatically from Polymarket.

When selling, the CLI reads your portfolio to find the matching position and uses its asset/conditionId.

### Error handling

- Exit code 0 = success, 1 = failure
- Errors: `{"error": "message"}` on stderr
- Rate limits: Olympus returns 429 if exceeded (30 req/min portfolio, 60 req/min trade, 100 req/min status)
- Network errors surface as OlympusError or PolymarketError with status codes

### Portfolio JSON shape

```json
{
  "balance": 8.98,
  "equity": 8.98,
  "positions_value": 0.0,
  "position_count": 0,
  "wallet_address": "0x...",
  "positions": [
    {
      "slug": "market-slug",
      "outcome": "Yes",
      "shares": 128.75,
      "avg_price": 0.56,
      "current_price": 0.58,
      "pnl": 2.58,
      "pnl_percent": 3.58,
      "current_value": 74.25,
      "condition_id": "0x...",
      "token_id": "98022...",
      "market_id": "540817",
      "redeemable": false
    }
  ],
  "calculated_at": "2026-05-16T00:00:00.000Z"
}
```

### Search result JSON shape

```json
[
  {
    "slug": "will-bitcoin-hit-150k",
    "question": "Will Bitcoin hit $150k?",
    "condition_id": "0x...",
    "market_id": "573652",
    "outcomes": [
      {"name": "Yes", "token_id": "45438...", "price": 0.62},
      {"name": "No", "token_id": "37069...", "price": 0.38}
    ],
    "volume": 778900.33,
    "enable_order_book": true,
    "accepting_orders": true
  }
]
```

### Trade response JSON shape

```json
{
  "trade_id": "tr_1234abcd",
  "status": "QUEUED",
  "success": true
}
```

### Trade status JSON shape (after watch/status)

```json
{
  "trade_id": "tr_1234abcd",
  "status": "SUCCEEDED",
  "side": "BUY",
  "market_title": "Will Bitcoin hit $150k?",
  "outcome_label": "Yes",
  "requested_amount_usd": 25.0,
  "filled_shares": 43.1,
  "filled_price": 0.58,
  "spent_usd": 25.0,
  "transaction_hash": "0x...",
  "error_code": null,
  "error_message": null
}
```
