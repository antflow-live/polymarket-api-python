# Stream prices over WebSockets

Polling `/book` in a loop is wasteful and laggy. The CLOB **market channel** WebSocket pushes price and book updates as they happen. The hard part of a long-lived feed isn't subscribing — it's staying connected: reconnecting after drops, keeping the socket alive, and noticing when the feed has silently died. `ClobWebSocketClient` handles all three. No API key required for the public market channel.

## Subscribe and react

```python
import asyncio
from polymarket_api import ClobWebSocketClient, PriceChange, BookUpdate, LastTradePrice

async def main():
    client = ClobWebSocketClient()

    async def on_event(event):
        if isinstance(event, PriceChange):
            print(f"price  {event.token_id[:10]}…  bid={event.best_bid}  ask={event.best_ask}")
        elif isinstance(event, BookUpdate):
            print(f"book   {event.token_id[:10]}…  bid={event.best_bid}  ask={event.best_ask}")
        elif isinstance(event, LastTradePrice):
            print(f"trade  {event.token_id[:10]}…  @ {event.price}")

    await client.run(["<token_id_1>", "<token_id_2>"], on_event)

asyncio.run(main())
```

Expected output (continuous stream):

```
book   7132a0ff3a…  bid=0.61  ask=0.63
price  7132a0ff3a…  bid=0.62  ask=0.63
trade  7132a0ff3a…  @ 0.62
...
```

`run()` loops forever, reconnecting as needed, until you cancel the task or call `await client.stop()`. The handler may be sync or async.

## Event types

| Event | When | Useful fields |
| --- | --- | --- |
| `PriceChange` | Best bid/ask moved | `token_id`, `best_bid`, `best_ask` |
| `BookUpdate` | Full book snapshot (sent on connect and on change) | `bids`, `asks`, derived `best_bid`/`best_ask` |
| `LastTradePrice` | A trade printed | `token_id`, `price` |
| `TickSizeChange` | Minimum tick tightened/loosened | `old_tick_size`, `new_tick_size` |
| `MarketResolved` | Market settled | `condition_id`, `winning_outcome` |

Every event also carries `.raw` — the original message dict — if you need a field the typed event doesn't surface (e.g. all rows of a batched `price_change`).

## Tuning the client

```python
client = ClobWebSocketClient(
    ping_interval=10.0,       # seconds between application-level PINGs
    reconnect_base=1.0,       # backoff doubles each attempt...
    reconnect_max=30.0,       # ...capped here
    stale_timeout=60.0,       # force a reconnect if no data for this long
    max_tokens_per_connection=500,
)
```

## Gotchas

- **Send your own PING.** The CLOB market channel expects a periodic application-level `PING` (the client sends it for you on `ping_interval`); plain TCP keepalive isn't enough. `PONG` replies are filtered out before your handler sees them.
- **A socket can look "open" after the feed dies.** The stale watchdog force-reconnects if no message arrives within `stale_timeout`. Don't rely on the connection raising an error on its own.
- **Re-round quotes on `TickSizeChange`.** Polymarket tightens the tick near the 0/1 bounds (e.g. `0.01 → 0.001`). A resting order priced on the old tick can be rejected as off-tick when you next reprice it.
- **Subscriptions are capped per connection.** Above `max_tokens_per_connection` (default 500) the list is truncated; shard across multiple clients for very large baskets.
- **Reconnect = re-snapshot.** After a reconnect you get fresh `BookUpdate` snapshots. Rebuild local state from those rather than assuming your pre-drop view is still valid.

---

Built by antflow — https://antflow.live
