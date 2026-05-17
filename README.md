# Olympus CLI (`oly`)

A Python CLI tool wrapping the [Olympus Trading API](https://api.olympusx.app) and [Polymarket Gamma API](https://gamma-api.polymarket.com). Designed for both human use (pretty tables) and agent/script use (clean JSON output).

## Quick start (no install needed)

```bash
uvx --from olympus-trade-cli oly portfolio
```

That's it. Run any `oly` command instantly — no install, no venv, no setup.

## Install

If you want `oly` permanently available on your PATH:

```bash
uv tool install olympus-trade-cli   # recommended
pipx install olympus-trade-cli      # alternative
pip install olympus-trade-cli       # if you prefer pip
```

### Don't have uv?

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Then run `uv tool install olympus-trade-cli` or use `uvx` for zero-install execution.

### From source (for development)

```bash
git clone https://github.com/fciaf420/olympus-cli.git
cd olympus-cli
pip install -e .
```

## Configuration

Set your Olympus API key:

```bash
oly config set-key                  # interactive prompt
export OLY_API_KEY="your-key-here"  # or env var
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

## Agent Integration

**If you're an AI agent or building an automated system**, see [AGENT.md](AGENT.md) for the complete integration guide — install commands, JSON schemas for every endpoint, auth setup, error handling, and a step-by-step trading workflow.

Quick version: all commands output clean JSON to stdout when piped. Errors go to stderr. Exit code 1 on failure.

```bash
# Agents can parse output directly
oly portfolio | jq '.balance'
oly search "bitcoin" | jq '.[0].slug'
oly buy will-btc-hit-150k Yes 25 | jq '.trade_id'
```

## Claude Skill (for Cowork / Claude Code)

The repo includes a ready-made **skill** that teaches Claude how to use the `oly` CLI as a Polymarket trading assistant. Once installed, Claude automatically knows every command, the correct workflow, and how to interpret results — no manual prompting needed.

### Install the skill

```bash
oly setup-skill
```

That's it — one command copies the skill into `~/.claude/skills/olympus-cli/`.

Or do it manually if you prefer:

```bash
cp -r skill/ ~/.claude/skills/olympus-cli/
```

After installing, any Claude session (Cowork, Claude Code, etc.) will automatically use the skill when you ask about Polymarket, prediction markets, portfolio balances, or trading.

### What it enables

With the skill installed, you can just say things like:
- "What's my balance?"
- "Find markets about AI"
- "Buy $5 of Yes on that bitcoin market if it's under 40 cents"
- "Sell half my position"

Claude will know exactly which `oly` commands to run, in what order, and will always confirm before executing trades.

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
