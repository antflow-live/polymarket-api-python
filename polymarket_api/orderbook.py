"""Fetch and analyze Polymarket CLOB order books.

:func:`fetch_order_book` calls the public CLOB REST endpoint
``GET https://clob.polymarket.com/book?token_id=...`` and returns an
:class:`OrderBookSnapshot` with the numbers you actually need to decide whether
a market is tradeable — spread, spread in basis points, mid price, depth within
5% of mid, and total resting liquidity — not just the raw ladder.

No API key is required to read the book.

Gotcha: for some thinly-quoted markets the ``/book`` endpoint can return a
stale dust book (e.g. 0.99/0.01 guard orders) while ``/price`` is accurate.
Treat a snapshot whose ``spread`` is implausibly wide as "no real two-sided
market", not as a tradeable quote.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import httpx

from .constants import CLOB_API_URL


def _level_price(level: Any) -> float:
    """Read the price from a CLOB level, which may be ``{"price","size"}`` or ``[price, size]``."""
    if isinstance(level, dict):
        return float(level.get("price", 0.0))
    if isinstance(level, (list, tuple)) and level:
        return float(level[0])
    return float(level)


def _level_size(level: Any) -> float:
    """Read the size from a CLOB level (dict or ``[price, size]`` pair)."""
    if isinstance(level, dict):
        return float(level.get("size", 0.0))
    if isinstance(level, (list, tuple)) and len(level) > 1:
        return float(level[1])
    return 0.0


@dataclass
class OrderBookSnapshot:
    """Point-in-time order book summary for one CLOB token.

    Prices are in USDC per share (0–1). ``spread_bps`` is the spread relative to
    the mid price. ``bid_depth_5pct`` / ``ask_depth_5pct`` sum the resting size
    within 5% of mid on each side — a quick read on how much you could trade
    near the touch without walking the book. ``bids`` / ``asks`` hold the top 10
    levels (bids price-descending, asks price-ascending).
    """

    token_id: str
    timestamp: str | None = None

    best_bid: float | None = None
    best_ask: float | None = None
    spread: float | None = None
    spread_bps: float | None = None
    mid_price: float | None = None

    bid_depth_5pct: float = 0.0
    ask_depth_5pct: float = 0.0

    total_bid_liquidity: float = 0.0
    total_ask_liquidity: float = 0.0

    bid_levels: int = 0
    ask_levels: int = 0

    bids: list[dict] = field(default_factory=list)
    asks: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Flat dict of the computed metrics (excludes the raw ladders)."""
        return {
            "token_id": self.token_id,
            "timestamp": self.timestamp,
            "best_bid": self.best_bid,
            "best_ask": self.best_ask,
            "spread": self.spread,
            "spread_bps": self.spread_bps,
            "mid_price": self.mid_price,
            "bid_depth_5pct": self.bid_depth_5pct,
            "ask_depth_5pct": self.ask_depth_5pct,
            "total_bid_liquidity": self.total_bid_liquidity,
            "total_ask_liquidity": self.total_ask_liquidity,
            "bid_levels": self.bid_levels,
            "ask_levels": self.ask_levels,
        }


def parse_order_book(token_id: str, raw: dict) -> OrderBookSnapshot:
    """Build an :class:`OrderBookSnapshot` from a raw CLOB ``/book`` response.

    Levels are re-sorted explicitly (bids high→low, asks low→high) so the result
    is correct regardless of the order the API returns them in.
    """
    bids = [
        {"price": _level_price(b), "size": _level_size(b)}
        for b in (raw.get("bids") or [])
    ]
    asks = [
        {"price": _level_price(a), "size": _level_size(a)}
        for a in (raw.get("asks") or [])
    ]
    bids.sort(key=lambda x: x["price"], reverse=True)
    asks.sort(key=lambda x: x["price"])

    best_bid = bids[0]["price"] if bids else None
    best_ask = asks[0]["price"] if asks else None

    spread = spread_bps = mid_price = None
    if best_bid is not None and best_ask is not None:
        spread = best_ask - best_bid
        mid_price = (best_bid + best_ask) / 2
        spread_bps = (spread / mid_price * 10_000) if mid_price > 0 else None

    bid_depth_5pct = ask_depth_5pct = 0.0
    if mid_price:
        bid_threshold = mid_price * 0.95
        ask_threshold = mid_price * 1.05
        bid_depth_5pct = sum(b["size"] for b in bids if b["price"] >= bid_threshold)
        ask_depth_5pct = sum(a["size"] for a in asks if a["price"] <= ask_threshold)

    return OrderBookSnapshot(
        token_id=token_id,
        timestamp=str(raw["timestamp"]) if raw.get("timestamp") is not None else None,
        best_bid=best_bid,
        best_ask=best_ask,
        spread=spread,
        spread_bps=spread_bps,
        mid_price=mid_price,
        bid_depth_5pct=round(bid_depth_5pct, 2),
        ask_depth_5pct=round(ask_depth_5pct, 2),
        total_bid_liquidity=round(sum(b["size"] for b in bids), 2),
        total_ask_liquidity=round(sum(a["size"] for a in asks), 2),
        bid_levels=len(bids),
        ask_levels=len(asks),
        bids=bids[:10],
        asks=asks[:10],
    )


def fetch_order_book(
    token_id: str,
    *,
    base_url: str = CLOB_API_URL,
    client: httpx.Client | None = None,
    timeout: float = 10.0,
) -> OrderBookSnapshot:
    """Fetch the live order book for a CLOB token and return a computed snapshot.

    ``token_id`` is a CLOB token id (e.g. ``market.yes_token_id`` from Gamma).
    Pass your own ``httpx.Client`` to reuse a connection pool across many calls.
    """
    owns_client = client is None
    http = client or httpx.Client(timeout=timeout)
    try:
        resp = http.get(f"{base_url.rstrip('/')}/book", params={"token_id": token_id})
        resp.raise_for_status()
        return parse_order_book(token_id, resp.json())
    finally:
        if owns_client:
            http.close()
