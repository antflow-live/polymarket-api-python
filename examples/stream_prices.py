"""Stream live price changes for the busiest market. Read-only, no credentials.

    python examples/stream_prices.py

Press Ctrl-C to stop.
"""

import asyncio

from polymarket_api import (
    BookUpdate,
    ClobWebSocketClient,
    GammaClient,
    LastTradePrice,
    PriceChange,
)


async def main() -> None:
    with GammaClient() as gamma:
        market = next(iter(gamma.iter_markets(max_markets=1)))

    token_ids = [t for t in (market.yes_token_id, market.no_token_id) if t]
    if not token_ids:
        print("No CLOB tokens to subscribe to.")
        return

    print(f"Streaming: {market.question}")
    print("(Ctrl-C to stop)\n")

    client = ClobWebSocketClient()

    async def on_event(event) -> None:
        if isinstance(event, PriceChange):
            print(f"price  {event.token_id[:10]}…  bid={event.best_bid}  ask={event.best_ask}")
        elif isinstance(event, BookUpdate):
            print(f"book   {event.token_id[:10]}…  bid={event.best_bid}  ask={event.best_ask}")
        elif isinstance(event, LastTradePrice):
            print(f"trade  {event.token_id[:10]}…  @ {event.price}")

    try:
        await client.run(token_ids, on_event)
    except KeyboardInterrupt:
        await client.stop()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
