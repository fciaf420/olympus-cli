"""Typer-based CLI for Olympus Trading and Polymarket."""

from __future__ import annotations

import json
import sys
from dataclasses import asdict
from typing import Optional

import typer

from olympus_cli.core.config import Config
from olympus_cli.core.data_api import DataApiClient
from olympus_cli.core.models import TradeRequest
from olympus_cli.core.olympus import OlympusClient, OlympusError
from olympus_cli.core.polymarket import ClobClient, PolymarketClient, PolymarketError

app = typer.Typer(
    name="oly",
    help="CLI for Olympus Trading API + Polymarket Gamma API.",
    no_args_is_help=True,
)
config_app = typer.Typer(name="config", help="Manage configuration.")
app.add_typer(config_app)

data_app = typer.Typer(name="data", help="Polymarket Data API: positions, trades, leaderboard.")
app.add_typer(data_app)

events_app = typer.Typer(name="events", help="Browse Polymarket events.")
app.add_typer(events_app)


def _is_pretty(pretty: bool) -> bool:
    if pretty:
        return True
    return sys.stdout.isatty()


def _json_out(data: dict | list) -> None:
    typer.echo(json.dumps(data, indent=2, default=str))


def _error_exit(msg: str) -> None:
    typer.echo(json.dumps({"error": msg}), err=True)
    raise typer.Exit(1)


# --- Config commands ---

@config_app.command("set-key")
def config_set_key(
    api_key: str = typer.Option(
        ..., prompt=True, hide_input=True, help="Olympus API key"
    ),
) -> None:
    """Save your Olympus API key."""
    cfg = Config.load()
    cfg.api_key = api_key
    cfg.save()
    typer.echo(json.dumps({"status": "ok", "message": "API key saved"}))


@config_app.command("show")
def config_show(
    pretty: bool = typer.Option(False, "--pretty", help="Human-readable output"),
) -> None:
    """Display current configuration."""
    cfg = Config.load()
    data = {
        "api_key": cfg.masked_key,
        "olympus_base_url": cfg.olympus_base_url,
        "polymarket_base_url": cfg.polymarket_base_url,
    }
    if _is_pretty(pretty):
        from olympus_cli.formatters import console
        from rich.panel import Panel
        console.print(Panel(
            f"API Key: {cfg.masked_key}\n"
            f"Olympus URL: {cfg.olympus_base_url}\n"
            f"Polymarket URL: {cfg.polymarket_base_url}",
            title="Config", border_style="blue",
        ))
    else:
        _json_out(data)


# --- Portfolio ---

@app.command()
def portfolio(
    pretty: bool = typer.Option(False, "--pretty", help="Human-readable output"),
) -> None:
    """Show portfolio: balance, positions, equity."""
    try:
        client = OlympusClient()
        p = client.get_portfolio()
        client.close()
    except OlympusError as e:
        _error_exit(e.message)

    if _is_pretty(pretty):
        from olympus_cli.formatters import format_portfolio
        format_portfolio(p)
    else:
        _json_out(asdict(p))


# --- Search ---

@app.command()
def search(
    query: str = typer.Argument(..., help="Search text for markets"),
    limit: int = typer.Option(20, "--limit", "-n", help="Max results"),
    pretty: bool = typer.Option(False, "--pretty", help="Human-readable output"),
) -> None:
    """Search Polymarket markets by keyword."""
    try:
        client = PolymarketClient()
        markets = client.search_markets(query, limit=limit)
        client.close()
    except PolymarketError as e:
        _error_exit(e.message)

    if _is_pretty(pretty):
        from olympus_cli.formatters import format_markets
        format_markets(markets)
    else:
        _json_out([asdict(m) for m in markets])


# --- Market detail ---

@app.command()
def market(
    slug: str = typer.Argument(..., help="Market slug"),
    pretty: bool = typer.Option(False, "--pretty", help="Human-readable output"),
) -> None:
    """Get full market details (outcomes, prices, volume, CLOB info)."""
    try:
        client = PolymarketClient()
        m = client.get_market(slug)
        client.close()
    except PolymarketError as e:
        _error_exit(e.message)

    # Fetch CLOB info if condition_id is available
    clob_info = None
    if m.condition_id:
        try:
            clob = ClobClient()
            clob_info = clob.get_market_info(m.condition_id)
            clob.close()
        except PolymarketError:
            pass  # CLOB info is supplementary; don't fail if unavailable

    if _is_pretty(pretty):
        from olympus_cli.formatters import format_market_detail
        format_market_detail(m, clob_info=clob_info)
    else:
        out = asdict(m)
        if clob_info:
            out["clob_info"] = asdict(clob_info)
        _json_out(out)


# --- Order Book ---

@app.command()
def orderbook(
    slug: str = typer.Argument(..., help="Market slug"),
    outcome: str = typer.Argument(..., help="Outcome name (e.g. Yes, No)"),
    pretty: bool = typer.Option(False, "--pretty", help="Human-readable output"),
) -> None:
    """Fetch and display order book from CLOB API."""
    try:
        poly = PolymarketClient()
        m = poly.get_market(slug)
        poly.close()
    except PolymarketError as e:
        _error_exit(e.message)

    matched = None
    for o in m.outcomes:
        if o.name.lower() == outcome.lower():
            matched = o
            break
    if not matched:
        available = ", ".join(o.name for o in m.outcomes)
        _error_exit(f"Outcome '{outcome}' not found. Available: {available}")

    try:
        clob = ClobClient()
        book = clob.get_order_book(matched.token_id)
        clob.close()
    except PolymarketError as e:
        _error_exit(e.message)

    if _is_pretty(pretty):
        from olympus_cli.formatters import format_order_book
        format_order_book(book, market_question=m.question, outcome_name=matched.name)
    else:
        _json_out(asdict(book))


# --- Price ---

@app.command()
def price(
    slug: str = typer.Argument(..., help="Market slug"),
    pretty: bool = typer.Option(False, "--pretty", help="Human-readable output"),
) -> None:
    """Fetch midpoint prices for all outcomes from CLOB API."""
    try:
        poly = PolymarketClient()
        m = poly.get_market(slug)
        poly.close()
    except PolymarketError as e:
        _error_exit(e.message)

    prices = []
    clob = ClobClient()
    for o in m.outcomes:
        if not o.token_id:
            continue
        try:
            mp = clob.get_midpoint(o.token_id)
            prices.append((o.name, mp))
        except PolymarketError:
            pass
    clob.close()

    if _is_pretty(pretty):
        from olympus_cli.formatters import format_midpoint_prices
        format_midpoint_prices(prices, market_question=m.question)
    else:
        _json_out([
            {"outcome": name, "token_id": mp.token_id, "midpoint": mp.midpoint}
            for name, mp in prices
        ])


# --- Buy ---

@app.command()
def buy(
    slug: str = typer.Argument(..., help="Market slug"),
    outcome: str = typer.Argument(..., help="Outcome to buy (Yes/No/Up/Down)"),
    usd: float = typer.Argument(..., help="Amount in USD to spend"),
    max_price: Optional[float] = typer.Option(None, "--max-price", help="Max price per share (0-1)"),
    stop_loss: Optional[float] = typer.Option(None, "--stop-loss", help="Stop-loss percent"),
    take_profit: Optional[float] = typer.Option(None, "--take-profit", help="Take-profit percent"),
    pretty: bool = typer.Option(False, "--pretty", help="Human-readable output"),
) -> None:
    """Buy a market position."""
    try:
        poly = PolymarketClient()
        m = poly.get_market(slug)
        poly.close()

        if not m.enable_order_book:
            _error_exit(f"Market '{slug}' does not have order book enabled")

        matched = None
        for o in m.outcomes:
            if o.name.lower() == outcome.lower():
                matched = o
                break
        if not matched:
            available = ", ".join(o.name for o in m.outcomes)
            _error_exit(f"Outcome '{outcome}' not found. Available: {available}")

        trade = TradeRequest(
            side="BUY",
            token_id=matched.token_id,
            condition_id=m.condition_id,
            market_title=m.question,
            outcome_label=matched.name,
            market_id=m.market_id or None,
            market_slug=m.slug or None,
            amount_usd=usd,
            max_price=max_price,
            stop_loss_percent=stop_loss,
            take_profit_percent=take_profit,
        )

        oly = OlympusClient()
        resp = oly.submit_trade(trade)
        oly.close()
    except (OlympusError, PolymarketError) as e:
        _error_exit(str(e))

    if _is_pretty(pretty):
        from olympus_cli.formatters import format_trade_response
        format_trade_response(resp)
    else:
        _json_out(asdict(resp))


# --- Sell ---

@app.command()
def sell(
    slug: str = typer.Argument(..., help="Market slug"),
    outcome: str = typer.Argument(..., help="Outcome to sell (Yes/No/Up/Down)"),
    percent: Optional[float] = typer.Option(None, "--percent", help="Sell by percent (1-100)"),
    shares: Optional[float] = typer.Option(None, "--shares", help="Sell exact number of shares"),
    min_price: Optional[float] = typer.Option(None, "--min-price", help="Min price per share (0-1)"),
    pretty: bool = typer.Option(False, "--pretty", help="Human-readable output"),
) -> None:
    """Sell a position."""
    try:
        oly = OlympusClient()
        p = oly.get_portfolio()

        matched_pos = None
        for pos in p.positions:
            if pos.slug == slug and pos.outcome.lower() == outcome.lower():
                matched_pos = pos
                break
        if not matched_pos:
            _error_exit(f"No open position found for {slug} / {outcome}")

        # Build sell spec per API docs
        if shares is not None:
            sell_spec = {"type": "shares", "sharesNormalized": shares}
        else:
            sell_spec = {"type": "percent", "sharePercent": percent or 100}

        trade = TradeRequest(
            side="SELL",
            token_id=matched_pos.token_id,  # positions[].asset
            condition_id=matched_pos.condition_id,
            market_title=slug,  # best we have
            market_id=matched_pos.market_id or None,
            market_slug=matched_pos.slug or None,
            sell_spec=sell_spec,
            min_price=min_price,
        )

        resp = oly.submit_trade(trade)
        oly.close()
    except OlympusError as e:
        _error_exit(e.message)

    if _is_pretty(pretty):
        from olympus_cli.formatters import format_trade_response
        format_trade_response(resp)
    else:
        _json_out(asdict(resp))


# --- Status ---

@app.command()
def status(
    trade_id: str = typer.Argument(..., help="Trade ID to check"),
    pretty: bool = typer.Option(False, "--pretty", help="Human-readable output"),
) -> None:
    """Check trade status."""
    try:
        client = OlympusClient()
        s = client.get_trade_status(trade_id)
        client.close()
    except OlympusError as e:
        _error_exit(e.message)

    if _is_pretty(pretty):
        from olympus_cli.formatters import format_trade_status
        format_trade_status(s)
    else:
        _json_out(asdict(s))


# --- Watch ---

@app.command()
def watch(
    trade_id: str = typer.Argument(..., help="Trade ID to watch"),
    interval: float = typer.Option(2.0, "--interval", help="Poll interval in seconds"),
    timeout: float = typer.Option(120.0, "--timeout", help="Max wait time in seconds"),
    pretty: bool = typer.Option(False, "--pretty", help="Human-readable output"),
) -> None:
    """Poll trade until completion."""
    try:
        client = OlympusClient()
        s = client.watch_trade(trade_id, poll_interval=interval, max_wait=timeout)
        client.close()
    except TimeoutError as e:
        _error_exit(str(e))
    except OlympusError as e:
        _error_exit(e.message)

    if _is_pretty(pretty):
        from olympus_cli.formatters import format_trade_status
        format_trade_status(s)
    else:
        _json_out(asdict(s))


# --- Spread ---

@app.command()
def spread(
    slug: str = typer.Argument(..., help="Market slug"),
    outcome: str = typer.Argument(..., help="Outcome name (e.g. Yes, No)"),
    pretty: bool = typer.Option(False, "--pretty", help="Human-readable output"),
) -> None:
    """Show bid/ask spread for an outcome."""
    try:
        poly = PolymarketClient()
        m = poly.get_market(slug)
        poly.close()
    except PolymarketError as e:
        _error_exit(e.message)

    matched = None
    for o in m.outcomes:
        if o.name.lower() == outcome.lower():
            matched = o
            break
    if not matched:
        available = ", ".join(o.name for o in m.outcomes)
        _error_exit(f"Outcome '{outcome}' not found. Available: {available}")

    try:
        clob = ClobClient()
        spread_info = clob.get_spread(matched.token_id)
        clob.close()
    except PolymarketError as e:
        _error_exit(e.message)

    if _is_pretty(pretty):
        from olympus_cli.formatters import format_spread
        format_spread(spread_info, market_question=m.question, outcome_name=matched.name)
    else:
        _json_out({
            "token_id": spread_info.token_id,
            "bid": spread_info.bid,
            "ask": spread_info.ask,
            "spread": spread_info.spread,
        })


# --- Last Trade ---

@app.command("last-trade")
def last_trade(
    slug: str = typer.Argument(..., help="Market slug"),
    outcome: str = typer.Argument(..., help="Outcome name (e.g. Yes, No)"),
    pretty: bool = typer.Option(False, "--pretty", help="Human-readable output"),
) -> None:
    """Show last trade price for an outcome."""
    try:
        poly = PolymarketClient()
        m = poly.get_market(slug)
        poly.close()
    except PolymarketError as e:
        _error_exit(e.message)

    matched = None
    for o in m.outcomes:
        if o.name.lower() == outcome.lower():
            matched = o
            break
    if not matched:
        available = ", ".join(o.name for o in m.outcomes)
        _error_exit(f"Outcome '{outcome}' not found. Available: {available}")

    try:
        clob = ClobClient()
        lt = clob.get_last_trade(matched.token_id)
        clob.close()
    except PolymarketError as e:
        _error_exit(e.message)

    if _is_pretty(pretty):
        from olympus_cli.formatters import format_last_trade
        format_last_trade(lt, market_question=m.question, outcome_name=matched.name)
    else:
        _json_out({
            "token_id": lt.token_id,
            "price": lt.price,
            "timestamp": lt.timestamp,
        })


# --- Price History ---

@app.command()
def history(
    slug: str = typer.Argument(..., help="Market slug"),
    outcome: str = typer.Argument(..., help="Outcome name (e.g. Yes, No)"),
    interval: str = typer.Option("1d", "--interval", "-i", help="Time interval (1d, 1w, 1m)"),
    fidelity: int = typer.Option(30, "--fidelity", "-f", help="Number of data points"),
    pretty: bool = typer.Option(False, "--pretty", help="Human-readable output"),
) -> None:
    """Show price history for an outcome."""
    try:
        poly = PolymarketClient()
        m = poly.get_market(slug)
    except PolymarketError as e:
        _error_exit(e.message)

    matched = None
    for o in m.outcomes:
        if o.name.lower() == outcome.lower():
            matched = o
            break
    if not matched:
        available = ", ".join(o.name for o in m.outcomes)
        _error_exit(f"Outcome '{outcome}' not found. Available: {available}")

    try:
        from olympus_cli.core.polymarket import ClobClient
        clob = ClobClient()
        points = clob.get_price_history(matched.token_id, interval=interval, fidelity=fidelity)
        clob.close()
        poly.close()
    except PolymarketError as e:
        _error_exit(e.message)

    if _is_pretty(pretty):
        from olympus_cli.formatters import format_price_history
        format_price_history(points, market_question=m.question, outcome_name=matched.name)
    else:
        _json_out([{"timestamp": p.timestamp, "price": p.price} for p in points])


# --- Data API: Positions ---

@data_app.command("positions")
def data_positions(
    wallet: str = typer.Argument(..., help="Wallet address"),
    pretty: bool = typer.Option(False, "--pretty", help="Human-readable output"),
) -> None:
    """Show open positions for a wallet."""
    try:
        client = DataApiClient()
        data = client.get_positions(wallet)
        client.close()
    except PolymarketError as e:
        _error_exit(e.message)

    if _is_pretty(pretty):
        from olympus_cli.formatters import format_positions
        format_positions(data)
    else:
        _json_out(data)


# --- Data API: Closed Positions ---

@data_app.command("closed")
def data_closed(
    wallet: str = typer.Argument(..., help="Wallet address"),
    pretty: bool = typer.Option(False, "--pretty", help="Human-readable output"),
) -> None:
    """Show closed positions for a wallet."""
    try:
        client = DataApiClient()
        data = client.get_closed_positions(wallet)
        client.close()
    except PolymarketError as e:
        _error_exit(e.message)

    if _is_pretty(pretty):
        from olympus_cli.formatters import format_positions
        format_positions(data)
    else:
        _json_out(data)


# --- Data API: Portfolio Value ---

@data_app.command("value")
def data_value(
    wallet: str = typer.Argument(..., help="Wallet address"),
    pretty: bool = typer.Option(False, "--pretty", help="Human-readable output"),
) -> None:
    """Show portfolio value for a wallet."""
    try:
        client = DataApiClient()
        data = client.get_portfolio_value(wallet)
        client.close()
    except PolymarketError as e:
        _error_exit(e.message)

    if _is_pretty(pretty):
        from rich.panel import Panel
        from olympus_cli.formatters import console
        if isinstance(data, dict):
            console.print(Panel(
                f"Value: [bold green]${float(data.get('value', 0)):,.2f}[/bold green]",
                title="Portfolio Value", border_style="blue",
            ))
        else:
            console.print(data)
    else:
        _json_out(data)


# --- Data API: Trades ---

@data_app.command("trades")
def data_trades(
    wallet: str = typer.Argument(..., help="Wallet address"),
    limit: int = typer.Option(50, "--limit", "-n", help="Max trades to return"),
    pretty: bool = typer.Option(False, "--pretty", help="Human-readable output"),
) -> None:
    """Show trade history for a wallet."""
    try:
        client = DataApiClient()
        data = client.get_trades(wallet, limit=limit)
        client.close()
    except PolymarketError as e:
        _error_exit(e.message)

    if _is_pretty(pretty):
        from olympus_cli.formatters import format_trades
        format_trades(data)
    else:
        _json_out(data)


# --- Data API: Activity ---

@data_app.command("activity")
def data_activity(
    wallet: str = typer.Argument(..., help="Wallet address"),
    pretty: bool = typer.Option(False, "--pretty", help="Human-readable output"),
) -> None:
    """Show activity feed for a wallet."""
    try:
        client = DataApiClient()
        data = client.get_activity(wallet)
        client.close()
    except PolymarketError as e:
        _error_exit(e.message)

    if _is_pretty(pretty):
        from olympus_cli.formatters import format_trades
        format_trades(data)
    else:
        _json_out(data)


# --- Data API: Top Holders ---

@data_app.command("holders")
def data_holders(
    slug: str = typer.Argument(..., help="Market slug"),
    pretty: bool = typer.Option(False, "--pretty", help="Human-readable output"),
) -> None:
    """Show top holders for a market."""
    try:
        poly = PolymarketClient()
        m = poly.get_market(slug)
        poly.close()
    except PolymarketError as e:
        _error_exit(e.message)

    try:
        client = DataApiClient()
        data = client.get_top_holders(m.condition_id)
        client.close()
    except PolymarketError as e:
        _error_exit(e.message)

    if _is_pretty(pretty):
        from olympus_cli.formatters import format_leaderboard
        format_leaderboard(data)
    else:
        _json_out(data)


# --- Data API: Open Interest ---

@data_app.command("open-interest")
def data_open_interest(
    slug: str = typer.Argument(..., help="Market slug"),
    pretty: bool = typer.Option(False, "--pretty", help="Human-readable output"),
) -> None:
    """Show open interest for a market."""
    try:
        poly = PolymarketClient()
        m = poly.get_market(slug)
        poly.close()
    except PolymarketError as e:
        _error_exit(e.message)

    try:
        client = DataApiClient()
        data = client.get_open_interest(m.condition_id)
        client.close()
    except PolymarketError as e:
        _error_exit(e.message)

    if _is_pretty(pretty):
        from rich.panel import Panel
        from olympus_cli.formatters import console
        if isinstance(data, dict):
            console.print(Panel(
                f"Open Interest: [bold green]${float(data.get('openInterest', data.get('value', 0))):,.2f}[/bold green]",
                title=f"Open Interest: {slug}", border_style="blue",
            ))
        else:
            console.print(data)
    else:
        _json_out(data)


# --- Data API: Leaderboard ---

@data_app.command("leaderboard")
def data_leaderboard(
    period: str = typer.Option("MONTH", "--period", "-p", help="Time period (DAY, WEEK, MONTH, ALL)"),
    order_by: str = typer.Option("PNL", "--order-by", "-o", help="Sort field (PNL, VOL)"),
    category: str = typer.Option("OVERALL", "--category", "-c", help="Category (OVERALL, POLITICS, SPORTS, CRYPTO, etc.)"),
    limit: int = typer.Option(20, "--limit", "-n", help="Max entries (max 50)"),
    pretty: bool = typer.Option(False, "--pretty", help="Human-readable output"),
) -> None:
    """Show the Polymarket leaderboard."""
    try:
        client = DataApiClient()
        data = client.get_leaderboard(period=period, order_by=order_by, limit=limit, category=category)
        client.close()
    except PolymarketError as e:
        _error_exit(e.message)

    if _is_pretty(pretty):
        from olympus_cli.formatters import format_leaderboard
        format_leaderboard(data)
    else:
        _json_out(data)


# --- Events: List ---

@events_app.command("list")
def events_list(
    limit: int = typer.Option(20, "--limit", "-n", help="Max events"),
    tag: Optional[str] = typer.Option(None, "--tag", "-t", help="Filter by tag"),
    pretty: bool = typer.Option(False, "--pretty", help="Human-readable output"),
) -> None:
    """List Polymarket events."""
    try:
        poly = PolymarketClient()
        data = poly.get_events(limit=limit, tag=tag)
        poly.close()
    except PolymarketError as e:
        _error_exit(e.message)

    if _is_pretty(pretty):
        from olympus_cli.formatters import format_events
        format_events(data)
    else:
        _json_out(data)


# --- Events: Get ---

@events_app.command("get")
def events_get(
    slug_or_id: str = typer.Argument(..., help="Event slug or ID"),
    pretty: bool = typer.Option(False, "--pretty", help="Human-readable output"),
) -> None:
    """Get event details."""
    try:
        poly = PolymarketClient()
        data = poly.get_event(slug_or_id)
        poly.close()
    except PolymarketError as e:
        _error_exit(e.message)

    if _is_pretty(pretty):
        from olympus_cli.formatters import format_event_detail
        format_event_detail(data)
    else:
        _json_out(data)


# --- Events: Upcoming ---

@events_app.command("upcoming")
def events_upcoming(
    within_hours: int = typer.Option(36, "--within-hours", "-h", help="Window in hours"),
    tag: Optional[str] = typer.Option(None, "--tag", "-t", help="Filter by tag (e.g. nba, nfl)"),
    limit: int = typer.Option(200, "--limit", "-n", help="Max events to scan from API"),
    stale_hours: int = typer.Option(
        24, "--stale-hours",
        help="Also include events whose endDate is up to N hours in the past "
             "but are still trading (active+!closed). Polymarket frequently "
             "lists game-of-day markets with stale endDates.",
    ),
    pretty: bool = typer.Option(False, "--pretty", help="Human-readable output"),
) -> None:
    """List open events ending within the next N hours (default 36).

    Useful for finding tonight's games — e.g. `oly events upcoming -t nba`.

    Events whose endDate is in the past but that are still flagged
    active/!closed (Polymarket leaves the market open during a game
    even when endDate has already passed) are included up to
    `--stale-hours` ago.
    """
    from datetime import datetime, timezone, timedelta

    try:
        poly = PolymarketClient()
        data = poly.get_events(limit=limit, tag=tag, active=True, closed=False)
        poly.close()
    except PolymarketError as e:
        _error_exit(e.message)

    now = datetime.now(timezone.utc)
    upper = now + timedelta(hours=within_hours)
    lower = now - timedelta(hours=stale_hours)
    upcoming = []
    for e in data:
        # Authoritative "still trading" signal: API flags. Date filtering
        # is best-effort because Polymarket's endDate is unreliable.
        if e.get("closed") is True or e.get("active") is False:
            continue
        end_raw = e.get("endDate") or e.get("end_date") or ""
        if not end_raw:
            # No date info but still trading — include it.
            upcoming.append(e)
            continue
        try:
            end_dt = datetime.fromisoformat(end_raw.replace("Z", "+00:00"))
        except ValueError:
            upcoming.append(e)
            continue
        if lower < end_dt < upper:
            upcoming.append(e)
    upcoming.sort(
        key=lambda e: e.get("endDate") or e.get("end_date") or ""
    )

    if _is_pretty(pretty):
        from olympus_cli.formatters import format_events
        format_events(upcoming)
    else:
        _json_out(upcoming)


# --- Events: Tags ---

@events_app.command("tags")
def events_tags(
    slug_or_id: str = typer.Argument(..., help="Event slug or ID"),
    pretty: bool = typer.Option(False, "--pretty", help="Human-readable output"),
) -> None:
    """Get tags for an event."""
    try:
        poly = PolymarketClient()
        data = poly.get_event(slug_or_id)
        poly.close()
    except PolymarketError as e:
        _error_exit(e.message)

    tags = data.get("tags", []) if isinstance(data, dict) else []

    if _is_pretty(pretty):
        from olympus_cli.formatters import console
        if tags:
            console.print(f"[bold]Tags:[/bold] {', '.join(str(t) for t in tags)}")
        else:
            console.print("[dim]No tags[/dim]")
    else:
        _json_out({"tags": tags})


# --- Setup Skill ---

@app.command("setup-skill")
def setup_skill() -> None:
    """Install the Claude skill for Polymarket trading assistant."""
    import shutil
    from pathlib import Path

    # Find the skill source bundled with this package
    source = Path(__file__).parent / "skill" / "SKILL.md"

    if not source.exists():
        # Fallback: repo root (development mode)
        source = Path(__file__).parent.parent / "skill" / "SKILL.md"

    if not source.exists():
        _error_exit("SKILL.md not found in package. Try reinstalling: uv tool install git+https://github.com/fciaf420/olympus-cli.git --force")

    dest_dir = Path.home() / ".claude" / "skills" / "olympus-cli"
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / "SKILL.md"

    shutil.copy2(source, dest)
    typer.echo(json.dumps({
        "status": "ok",
        "message": f"Skill installed to {dest}",
        "path": str(dest),
    }))


if __name__ == "__main__":
    app()
