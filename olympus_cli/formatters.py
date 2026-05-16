"""Pretty-print formatters for terminal output using Rich."""

from __future__ import annotations

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text

from olympus_cli.core.models import Market, Portfolio, TradeResponse, TradeStatus

console = Console()


def format_portfolio(portfolio: Portfolio) -> None:
    """Print portfolio as a rich table."""
    summary = Text()
    summary.append(f"Wallet:    ", style="bold")
    summary.append(f"{portfolio.wallet_address}\n", style="dim")
    summary.append(f"Balance:   ", style="bold")
    summary.append(f"${portfolio.balance:.2f}\n")
    summary.append(f"Positions: ", style="bold")
    summary.append(f"${portfolio.positions_value:.2f}\n")
    summary.append(f"Equity:    ", style="bold")
    summary.append(f"${portfolio.equity:.2f}")
    console.print(Panel(summary, title="Portfolio", border_style="blue"))

    if portfolio.positions:
        table = Table(title=f"Positions ({portfolio.position_count})")
        table.add_column("Market", style="cyan")
        table.add_column("Side", style="magenta")
        table.add_column("Shares", justify="right")
        table.add_column("Avg Price", justify="right")
        table.add_column("Current", justify="right")
        table.add_column("Value", justify="right")
        table.add_column("PnL", justify="right")

        for pos in portfolio.positions:
            pnl_style = "green" if pos.pnl >= 0 else "red"
            table.add_row(
                pos.slug,
                pos.outcome,
                f"{pos.shares:.2f}",
                f"${pos.avg_price:.3f}",
                f"${pos.current_price:.3f}",
                f"${pos.current_value:.2f}",
                Text(f"${pos.pnl:+.2f} ({pos.pnl_percent:+.1f}%)", style=pnl_style),
            )
        console.print(table)
    else:
        console.print("[dim]No open positions[/dim]")


def format_markets(markets: list[Market]) -> None:
    """Print a list of markets as a table."""
    table = Table(title="Markets")
    table.add_column("Slug", style="cyan")
    table.add_column("Question", max_width=50)
    table.add_column("Outcomes", style="magenta")
    table.add_column("Volume", justify="right")

    for m in markets:
        outcomes_str = " / ".join(
            f"{o.name} @{o.price:.2f}" for o in m.outcomes
        )
        table.add_row(m.slug, m.question[:50], outcomes_str, f"${m.volume:,.0f}")
    console.print(table)


def format_market_detail(market: Market) -> None:
    """Print detailed market info."""
    order_book = "[green]Yes[/green]" if market.enable_order_book else "[red]No[/red]"
    accepting = "[green]Yes[/green]" if market.accepting_orders else "[red]No[/red]"
    console.print(Panel(
        f"[bold]{market.question}[/bold]\n\n"
        f"Slug: [cyan]{market.slug}[/cyan]\n"
        f"Market ID: {market.market_id}\n"
        f"Condition ID: [dim]{market.condition_id}[/dim]\n"
        f"Volume: ${market.volume:,.0f}  |  Liquidity: ${market.liquidity:,.0f}\n"
        f"Order Book: {order_book}  |  Accepting: {accepting}\n"
        f"End Date: {market.end_date}",
        title="Market Detail", border_style="blue",
    ))

    table = Table(title="Outcomes")
    table.add_column("Outcome", style="magenta")
    table.add_column("Price", justify="right", style="green")
    table.add_column("Token ID", style="dim")
    for o in market.outcomes:
        tid = o.token_id[:20] + "..." if len(o.token_id) > 20 else o.token_id
        table.add_row(o.name, f"${o.price:.4f}", tid)
    console.print(table)


def format_trade_response(resp: TradeResponse) -> None:
    """Print trade submission result."""
    console.print(Panel(
        f"Trade ID: [bold cyan]{resp.trade_id}[/bold cyan]\n"
        f"Status: [yellow]{resp.status}[/yellow]",
        title="Trade Submitted", border_style="green",
    ))


def format_trade_status(status: TradeStatus) -> None:
    """Print trade status."""
    status_color = {
        "QUEUED": "yellow",
        "PROCESSING": "yellow",
        "SUCCEEDED": "green",
        "FAILED": "red",
    }.get(status.status, "white")

    lines = [
        f"Trade ID: [bold cyan]{status.trade_id}[/bold cyan]",
        f"Status: [{status_color}]{status.status}[/{status_color}]",
        f"Side: {status.side}",
    ]
    if status.market_title:
        lines.append(f"Market: {status.market_title}")
    if status.outcome_label:
        lines.append(f"Outcome: {status.outcome_label}")
    if status.filled_price is not None:
        lines.append(f"Filled Price: ${status.filled_price:.4f}")
    if status.filled_shares is not None:
        lines.append(f"Filled Shares: {status.filled_shares:.2f}")
    if status.spent_usd is not None:
        lines.append(f"Spent: ${status.spent_usd:.2f}")
    if status.transaction_hash:
        lines.append(f"Tx: {status.transaction_hash}")
    if status.error_message:
        lines.append(f"Error: [red]{status.error_message}[/red]")

    console.print(Panel("\n".join(lines), title="Trade Status", border_style="blue"))
