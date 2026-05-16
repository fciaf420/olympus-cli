"""Typer-based CLI for Olympus Trading and Polymarket."""

from __future__ import annotations

import json
import sys
from dataclasses import asdict
from typing import Optional

import typer

from olympus_cli.core.config import Config
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


if __name__ == "__main__":
    app()
