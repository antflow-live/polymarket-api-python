"""Print an order-book snapshot for an active market's YES token. Read-only.

    python examples/orderbook_snapshot.py
"""

from _common import pick_tradeable_market

from polymarket_api import GammaClient, fetch_order_book


def main() -> None:
    with GammaClient() as gamma:
        market = pick_tradeable_market(gamma)

    token_id = market.yes_token_id
    if not token_id:
        print(f"Market {market.id!r} has no CLOB token ids yet.")
        return

    print(market.question)
    book = fetch_order_book(token_id)

    if book.best_bid is None or book.best_ask is None:
        print("No two-sided market right now.")
        return

    print(f"  best bid : {book.best_bid}")
    print(f"  best ask : {book.best_ask}")
    print(f"  mid      : {book.mid_price:.4f}")
    print(f"  spread   : {book.spread:.4f}  ({book.spread_bps:.0f} bps)")
    print(f"  depth ±5%: bid={book.bid_depth_5pct}  ask={book.ask_depth_5pct}")
    print(f"  liquidity: bid={book.total_bid_liquidity}  ask={book.total_ask_liquidity}")


if __name__ == "__main__":
    main()
