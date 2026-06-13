# Handling resolution

Unlike ordinary markets, Polymarket positions can **resolve**: when the underlying event is decided, the market settles and the winning outcome tokens become redeemable. A position you hold can settle while you sleep, changing your exposure with no order on your part. Build your accounting around "this market may resolve at any time" rather than treating settlement as an afterthought.

## Detect resolution from the stream

The market-channel WebSocket emits a `MarketResolved` event when a market settles. It's the lowest-latency signal that a token you're tracking is done:

```python
import asyncio
from polymarket_api import ClobWebSocketClient, MarketResolved

async def main():
    client = ClobWebSocketClient()

    async def on_event(event):
        if isinstance(event, MarketResolved):
            print(f"resolved: {event.condition_id}  winner={event.winning_outcome}")
            # Stop quoting this market, mark the position for redemption, reconcile.

    await client.run(["<token_id>"], on_event)

asyncio.run(main())
```

## Poll status as the source of truth

The stream is a notification, not a ledger. Treat the WebSocket event as a *trigger* and confirm against authoritative state — re-read the market from Gamma and check its flags:

```python
from polymarket_api import GammaClient

with GammaClient() as gamma:
    market = gamma.get_market("<market_id>")

if market.closed or not market.accepting_orders:
    print("market is closed/settling — stop quoting, reconcile positions")
```

## A resolution-aware decision cycle

The shape of a safe loop checks resolution *before* it evaluates anything else — a resolved market shouldn't be quoted:

```python
while running:
    market = gamma.get_market(market_id)          # latest metadata + status
    if market.closed or not market.accepting_orders:
        handle_resolution(market)                  # redeem / reconcile / stop
        break

    book = fetch_order_book(market.yes_token_id)
    # ... your own evaluation and (optional) orders here ...
    time.sleep(interval)                           # respect rate limits
```

## Gotchas

- **Resolution can lag the event.** A market doesn't free up the instant the real-world event happens — settlement can be delayed or disputed. Don't assume tokens are redeemable the moment you "know" the outcome.
- **The stream is a hint, not a guarantee.** Network drops mean you can miss a `MarketResolved` event. Always have a polling fallback that reconciles status, so you don't rely solely on the push.
- **Stop quoting a closed market immediately.** Once `accepting_orders` is false, new orders are rejected. Gate order placement on the live status, not on a value you cached minutes ago.
- **Settlement changes exposure without an order.** Your position accounting has to handle a holding converting to a redeemable (or worthless) outcome on its own — reconcile balances after resolution, don't infer them from your last trade.

---

Built by antflow — https://antflow.live
