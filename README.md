# Polymarket API client for Python

A small, typed Python toolkit for the [Polymarket](https://polymarket.com) API. Read markets from the **Gamma** API, snapshot and **stream the CLOB order book**, generate idempotent client order ids, and place orders through Polymarket's official client.

It wraps Polymarket's **public** CLOB and Gamma APIs. The read / stream / analytics surface needs only `httpx` and `websockets` and **no API key**. Order placement is opt-in.

[![Python](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/) [![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)

```bash
pip install polymarket-api-python
```

## 30-second quickstart

Read the most-active market right now and check its order book — no credentials required:

```python
from polymarket_api import GammaClient, fetch_order_book

with GammaClient() as gamma:
    # Markets sorted by 24h volume; grab the busiest one.
    market = next(iter(gamma.iter_markets(max_markets=1)))

print(market.question)

book = fetch_order_book(market.yes_token_id)
print(f"YES  bid={book.best_bid}  ask={book.best_ask}  spread={book.spread_bps:.0f} bps")
print(f"depth within 5% of mid:  bid={book.bid_depth_5pct}  ask={book.ask_depth_5pct}")
```

```
Will <…> happen by <…>?
YES  bid=0.62  ask=0.63  spread=160 bps
depth within 5% of mid:  bid=4210.0  ask=3880.0
```

## What it does

| Module | What it gives you | Needs |
| --- | --- | --- |
| `polymarket_api.gamma` | Typed market reader: pagination that handles the silent `limit=100` clamp, and auto-decoding of the JSON-string fields (`outcomes`, `outcomePrices`, `clobTokenIds`) | `httpx` |
| `polymarket_api.orderbook` | `OrderBookSnapshot` with computed spread, spread (bps), mid, depth-within-5%, and total resting liquidity — not just the raw ladder | `httpx` |
| `polymarket_api.ws` | A resilient CLOB WebSocket subscriber: auto-reconnect, PING/PONG keepalive, a stale-feed watchdog, and typed events | `websockets` |
| `polymarket_api.client_order_id` | Deterministic client order ids for idempotent, retry-safe submission | stdlib |
| `polymarket_api.orders` | Thin, optional wrapper over Polymarket's official client for signing + placing + cancelling orders | `[trading]` extra |

### Stream live prices

```python
import asyncio
from polymarket_api import ClobWebSocketClient, PriceChange

async def main():
    client = ClobWebSocketClient()

    async def on_event(event):
        if isinstance(event, PriceChange):
            print(event.token_id[:12], event.best_bid, event.best_ask)

    # Runs forever, reconnecting as needed. Ctrl-C to stop.
    await client.run(["<clob_token_id>"], on_event)

asyncio.run(main())
```

### Place an order (optional)

Order placement is opt-in and pulls in Polymarket's official, audited client, which performs all EIP-712 signing:

```bash
pip install "polymarket-api-python[trading]"
```

```python
import os
from polymarket_api.orders import make_trading_client, place_limit_order

client = make_trading_client(os.environ["POLYMARKET_PRIVATE_KEY"])  # derives L2 creds for you
place_limit_order(client, token_id="<clob_token_id>", price=0.40, size=20, side="BUY")
```

This package never implements signing itself — see [`docs/sign-and-place-an-order.md`](docs/sign-and-place-an-order.md).

## Docs / Cookbook

Task-oriented, code-first recipes — each is a runnable snippet plus the gotchas that bite in production:

- [Read markets](docs/read-markets.md) — list and filter Gamma markets, decode the string-encoded fields
- [Order book snapshots](docs/orderbook.md) — spread, depth, and liquidity from one call
- [WebSockets](docs/websockets.md) — stream prices and book updates with auto-reconnect
- [Sign and place an order](docs/sign-and-place-an-order.md) — L1/L2 auth and the official client
- [Cancel and replace](docs/cancel-and-replace.md) — idempotent ids and the cancel/replace pattern
- [Auth and keys](docs/auth-and-keys.md) — what L1 vs L2 actually mean
- [Rate limits](docs/rate-limits.md) — the real per-endpoint limits and how to stay under them
- [Handling resolution](docs/handling-resolution.md) — detect when a market settles

## Install from source

```bash
git clone https://github.com/antflow-live/polymarket-api-python
cd polymarket-api-python
pip install -e ".[dev]"
pytest
```

## About antflow

This toolkit is maintained by **[antflow](https://antflow.live)** — an autonomous trading bot for Polymarket. antflow scans prediction markets, applies operator-defined risk controls, and executes and monitors trades automatically. We open-sourced the generic API plumbing we rely on so other Polymarket developers don't have to rebuild it.

- Website: **https://antflow.live**
- LinkedIn: **https://www.linkedin.com/company/antflow-live**
- Crunchbase: **https://www.crunchbase.com/organization/antflow**

> **Disambiguation:** this is **antflow — Polymarket trading**. It is unrelated to *antflow.ai* and to the *AntFlow* workflow-engine projects that share the name.

## Disclaimer

This is developer tooling for the Polymarket API, provided for **educational and informational purposes only**. It is **not financial advice** and makes **no representation about trading outcomes or profitability**. Prediction-market trading carries risk. Comply with Polymarket's terms and the laws of your jurisdiction. Use at your own risk; see the [MIT License](LICENSE) for warranty terms.

## License

[MIT](LICENSE) © 2026 antflow
