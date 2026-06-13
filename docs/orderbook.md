# Order book snapshots

The price you see in the UI is the top of the book. What actually decides your fill is the **depth** — how much size rests at each level. A thin book means even a modest order walks the ladder and fills at progressively worse prices. `fetch_order_book` returns a snapshot with the touch, the spread, and the depth already computed, so you don't have to reduce the raw ladder yourself. No API key required.

## Snapshot a token

```python
from polymarket_api import GammaClient, fetch_order_book

with GammaClient() as gamma:
    market = next(iter(gamma.iter_markets(max_markets=1)))

book = fetch_order_book(market.yes_token_id)

print(f"bid {book.best_bid}  ask {book.best_ask}  mid {book.mid_price:.4f}")
print(f"spread {book.spread:.4f} ({book.spread_bps:.0f} bps)")
print(f"depth within 5% of mid:  bid {book.bid_depth_5pct}  ask {book.ask_depth_5pct}")
print(f"total resting liquidity: bid {book.total_bid_liquidity}  ask {book.total_ask_liquidity}")
```

Expected output:

```
bid 0.62  ask 0.63  mid 0.6250
spread 0.0100 (160 bps)
depth within 5% of mid:  bid 4210.0  ask 3880.0
total resting liquidity: bid 18044.0  ask 15992.0
```

## What's in the snapshot

| Field | Meaning |
| --- | --- |
| `best_bid` / `best_ask` | Top of book on each side |
| `mid_price` | `(best_bid + best_ask) / 2` |
| `spread` / `spread_bps` | Absolute spread, and spread relative to mid in basis points |
| `bid_depth_5pct` / `ask_depth_5pct` | Total resting size within 5% of mid — a quick read on how much you can trade near the touch |
| `total_bid_liquidity` / `total_ask_liquidity` | Sum of all resting size on each side |
| `bids` / `asks` | The top 10 levels, sorted (bids high→low, asks low→high) |

## Reuse a connection for many tokens

Pass your own `httpx.Client` to avoid a new connection per call when snapshotting a basket of tokens:

```python
import httpx
from polymarket_api import fetch_order_book

with httpx.Client(timeout=10.0) as http:
    for token_id in token_ids:
        book = fetch_order_book(token_id, client=http)
        ...
```

## Gotchas

- **Stale dust books.** For some thinly-quoted markets `/book` can return guard orders (e.g. a `0.99 / 0.01` pair) while `/price` is accurate. A snapshot whose `spread_bps` is implausibly wide is "no real two-sided market", not a tradeable quote — treat it as untradeable rather than a screaming arbitrage.
- **Size against visible depth.** An order larger than the depth near the touch will walk the book. Compare your intended size to `bid_depth_5pct` / `ask_depth_5pct` before sending.
- **Snapshots are point-in-time.** For anything latency-sensitive, stream updates over the [WebSocket](websockets.md) instead of polling `/book` in a tight loop — it's lighter on the rate limit and closer to live.
- **A missing side returns `None`.** If one side of the book is empty, `best_bid`/`best_ask` (and the derived `spread`/`mid`) are `None`. Guard for it.

---

Built by antflow — https://antflow.live
