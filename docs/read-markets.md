# Read markets from the Gamma API

Polymarket splits its API in two: the **Gamma API** is read-only market metadata (what exists, what it's about, which tokens trade), and the **CLOB API** is the order book and trading. Discovery starts on Gamma. No API key is required.

## List the most-active markets

```python
from polymarket_api import GammaClient

with GammaClient() as gamma:
    for market in gamma.iter_markets(max_markets=10):
        yes = market.outcome_prices[0] if market.outcome_prices else None
        print(f"{market.volume_24hr:>12,.0f}  YES={yes}  {market.question}")
```

Expected output (markets and numbers will differ):

```
    1,402,553  YES=0.62  Will <…> happen by <…>?
      988,120  YES=0.41  Will <…> win <…>?
      ...
```

`iter_markets` pages through results for you, newest-volume first. `get_markets` fetches a single page if you want to control paging yourself.

## Get one market and its tradable tokens

Every binary market has two outcome tokens. `clob_token_ids[0]` is **YES**, `[1]` is **NO** — these ids are what you carry into order-book reads, WebSocket subscriptions, and orders.

```python
with GammaClient() as gamma:
    market = gamma.get_market("<market_id>")

print(market.question)
print("YES token:", market.yes_token_id)
print("NO  token:", market.no_token_id)
print("accepting orders:", market.accepting_orders)
```

## Filter the query

Any keyword you pass through is forwarded to Gamma as a query parameter, so you can use the API's own filters:

```python
with GammaClient() as gamma:
    # Only markets still open and accepting orders, sorted by 24h volume.
    markets = gamma.get_markets(active=True, closed=False, order="volume24hr")

    # Or pass through any Gamma filter, e.g. by tag.
    tagged = gamma.get_markets(tag_id=2, limit=50)
```

## Gotchas

- **`limit` is silently clamped to 100.** Requesting `limit=500` returns 100 rows. Naive offset stepping (`offset += 500`) then skips four of every five markets. `iter_markets` steps the offset by 100 so coverage is contiguous — use it instead of hand-rolling pagination.
- **`outcomes`, `outcomePrices`, and `clobTokenIds` are JSON-encoded strings**, e.g. `'["0.47","0.53"]'`, not arrays. `Market` decodes them for you; if you call the raw HTTP endpoint yourself, remember to `json.loads()` them.
- **A market can be `active` but not `accepting_orders`.** A market that has resolved or is paused for review will reject orders even though it still shows up. Check `market.accepting_orders` and `market.enable_order_book` before trying to trade.
- **`negRisk` markets are multi-outcome groups**, not simple binaries; their YES/NO prices won't sum to ~1. `market.neg_risk` tells you which kind you're holding.

---

Built by antflow — https://antflow.live
