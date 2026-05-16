# Olympus CLI (`oly`)

A Python CLI tool wrapping the [Olympus Trading API](https://api.olympusx.app) and [Polymarket Gamma API](https://gamma-api.polymarket.com). Designed for both human use (pretty tables) and agent/script use (clean JSON output).

## Install

### One-liner (recommended)

```bash
pipx install olympus-trade-cli
```

Or with [uv](https://docs.astral.sh/uv/) (faster):

```bash
uv tool install olympus-trade-cli
```

Or plain pip:

```bash
pip install olympus-trade-cli
```

### Run without installing

```bash
# With uvx (uv's equivalent of npx)
uvx --from olympus-trade-cli oly portfolio

# With pipx
pipx run --spec olympus-trade-cli oly portfolio
```

### From source (for development)

```bash
git clone https://github.com/fciaf420/olympus-cli.git
cd olympus-cli
pip install -e .
```

## Configuration

Set your Olympus API key:

```bash
# Interactive prompt (recommended)
oly config set-key

# Or via environment variable
export OLY_API_KEY="your-key-here"
```

Config is stored at `~/.oly/config.json`.

## Usage

### Portfolio

```bash
oly portfolio              # JSON output (default)
oly portfolio --pretty     # Rich formatted tables
```

### Search Markets

```bash
oly search "solana"
oly search "election" --limit 5
```

### Market Details

```bash
oly market will-solana-reach-200
```

### Buy

```bash
oly buy will-solana-reach-200 Yes 50
oly buy will-solana-reach-200 Yes 50 --max-price 0.60 --stop-loss 20 --take-profit 50
```

### Sell

```bash
oly sell will-solana-reach-200 Yes              # Sell 100%
oly sell will-solana-reach-200 Yes --percent 50  # Sell 50%
oly sell will-solana-reach-200 Yes --shares 25   # Sell 25 shares
oly sell will-solana-reach-200 Yes --min-price 0.55
```

### Trade Status

```bash
oly status abc123-trade-id
oly watch abc123-trade-id           # Polls until SUCCEEDED/FAILED
oly watch abc123-trade-id --interval 5 --timeout 300
```

### Config

```bash
oly config show
oly config set-key
```

## Agent Usage

The CLI outputs clean JSON by default (when stdout is not a TTY), making it ideal for use with Claude Code, LangChain agents, or any scripting workflow.

```python
import subprocess, json

# Get portfolio
result = subprocess.run(["oly", "portfolio"], capture_output=True, text=True)
portfolio = json.loads(result.stdout)
print(f"Balance: ${portfolio['balance']}")

# Search markets
result = subprocess.run(["oly", "search", "bitcoin"], capture_output=True, text=True)
markets = json.loads(result.stdout)

# Buy and watch
result = subprocess.run(
    ["oly", "buy", "will-btc-hit-100k", "Yes", "25"],
    capture_output=True, text=True,
)
trade = json.loads(result.stdout)
trade_id = trade["trade_id"]

# Poll until done
result = subprocess.run(["oly", "watch", trade_id], capture_output=True, text=True)
final = json.loads(result.stdout)
print(f"Trade {final['status']}: filled at ${final['filled_price']}")
```

### Claude Code / MCP Integration

```bash
# In a Claude Code session or MCP tool:
oly portfolio | jq '.positions[] | select(.pnl < 0)'
oly search "crypto" | jq '.[0].slug'
```

## Architecture

```
olympus_cli/
├── cli.py              # Typer CLI entry point
├── core/
│   ├── olympus.py      # Olympus API client
│   ├── polymarket.py   # Polymarket gamma API client
│   ├── models.py       # Dataclasses (Portfolio, Position, Trade, Market)
│   └── config.py       # Config management
└── formatters.py       # Rich terminal formatters
```

**Core library** (`olympus_cli.core`) is importable for scripting — pure functions, no print statements, returns structured dataclasses.

## Publishing

```bash
make build      # Build sdist + wheel
make check      # Validate package
make publish    # Upload to PyPI
```

## Requirements

- Python 3.10+
- typer
- httpx
- rich

## License

MIT
