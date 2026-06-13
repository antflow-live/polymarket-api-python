"""Stream live prices and order-book updates from the Polymarket CLOB WebSocket.

Connect to the public CLOB *market* channel, subscribe to a set of token ids,
and receive typed events as they arrive. The client handles the parts that make
a long-lived market feed annoying to write yourself:

- **Auto-reconnect** with exponential backoff.
- **PING/PONG keepalive** (the server expects a periodic ``PING``).
- **A stale watchdog** that force-reconnects if no data arrives for a while —
  TCP can stay "open" long after the feed has silently died.
- **Typed events** — :class:`PriceChange`, :class:`BookUpdate`,
  :class:`LastTradePrice`, :class:`TickSizeChange`, :class:`MarketResolved`.

No API key is required for the public market channel.

Example::

    import asyncio
    from polymarket_api import ClobWebSocketClient, PriceChange

    async def main():
        client = ClobWebSocketClient()

        async def on_event(event):
            if isinstance(event, PriceChange):
                print(event.token_id[:12], event.best_bid, event.best_ask)

        await client.run(["7132...token"], on_event)

    asyncio.run(main())
"""

from __future__ import annotations

import asyncio
import inspect
import json
import time
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Union

import websockets

from .constants import CLOB_WS_URL

# ---------------------------------------------------------------------------
# Typed events
# ---------------------------------------------------------------------------


@dataclass
class PriceChange:
    """Best bid/ask moved for a token (``event_type == "price_change"``)."""

    token_id: str
    best_bid: float | None
    best_ask: float | None
    raw: dict = field(default_factory=dict, repr=False)


@dataclass
class BookUpdate:
    """A full book snapshot for a token (``event_type == "book"``).

    ``best_bid``/``best_ask`` are derived from the levels for convenience.
    """

    token_id: str
    bids: list[dict]
    asks: list[dict]
    best_bid: float | None
    best_ask: float | None
    raw: dict = field(default_factory=dict, repr=False)


@dataclass
class LastTradePrice:
    """A trade printed at ``price`` for a token (``event_type == "last_trade_price"``)."""

    token_id: str
    price: float
    raw: dict = field(default_factory=dict, repr=False)


@dataclass
class TickSizeChange:
    """The minimum tick tightened/loosened for a token.

    Polymarket auto-tightens the tick near the 0/1 bounds (e.g. 0.01 → 0.001).
    Resting orders priced on the old tick can be rejected as off-tick on the
    next reprice, so re-round your quotes when you see this.
    """

    token_id: str
    old_tick_size: str | None
    new_tick_size: str | None
    raw: dict = field(default_factory=dict, repr=False)


@dataclass
class MarketResolved:
    """A market resolved (``event_type == "market_resolved"``)."""

    condition_id: str
    winning_outcome: str | None
    winning_asset_id: str | None
    raw: dict = field(default_factory=dict, repr=False)


Event = Union[PriceChange, BookUpdate, LastTradePrice, TickSizeChange, MarketResolved]
EventHandler = Callable[[Event], Union[None, Awaitable[None]]]


def _extract_prices(levels: list) -> list[float]:
    out: list[float] = []
    for entry in levels:
        if isinstance(entry, (list, tuple)) and entry:
            out.append(float(entry[0]))
        elif isinstance(entry, dict):
            out.append(float(entry.get("price", 0.0)))
        else:
            out.append(float(entry))
    return out


def parse_event(data: dict) -> Event | None:
    """Map a raw CLOB market-channel message to a typed event, or ``None`` if unknown."""
    event_type = data.get("event_type")

    if event_type == "price_change":
        # Some feeds batch multiple changes; the touch fields are also present
        # at the top level for single updates. Prefer explicit per-change rows.
        changes = data.get("price_changes")
        if changes:
            # Return the first; callers wanting all can read event.raw.
            change = changes[0]
            return PriceChange(
                token_id=change.get("asset_id", ""),
                best_bid=_to_float(change.get("best_bid")),
                best_ask=_to_float(change.get("best_ask")),
                raw=data,
            )
        return PriceChange(
            token_id=data.get("asset_id", ""),
            best_bid=_to_float(data.get("best_bid")),
            best_ask=_to_float(data.get("best_ask")),
            raw=data,
        )

    if event_type == "book":
        bids = data.get("bids", []) or []
        asks = data.get("asks", []) or []
        bid_prices = _extract_prices(bids)
        ask_prices = _extract_prices(asks)
        return BookUpdate(
            token_id=data.get("asset_id", ""),
            bids=bids,
            asks=asks,
            best_bid=max(bid_prices) if bid_prices else None,
            best_ask=min(ask_prices) if ask_prices else None,
            raw=data,
        )

    if event_type == "last_trade_price":
        price = _to_float(data.get("price"))
        if price is None:
            return None
        return LastTradePrice(token_id=data.get("asset_id", ""), price=price, raw=data)

    if event_type == "tick_size_change":
        return TickSizeChange(
            token_id=data.get("asset_id", ""),
            old_tick_size=data.get("old_tick_size"),
            new_tick_size=data.get("new_tick_size"),
            raw=data,
        )

    if event_type == "market_resolved":
        return MarketResolved(
            condition_id=data.get("market") or data.get("condition_id") or "",
            winning_outcome=data.get("winning_outcome"),
            winning_asset_id=data.get("winning_asset_id"),
            raw=data,
        )

    return None


def _to_float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------


class ClobWebSocketClient:
    """A resilient subscriber for the public Polymarket CLOB market channel.

    Call :meth:`run` with the token ids you care about and an event handler.
    :meth:`run` loops forever (reconnecting as needed) until the task is
    cancelled or :meth:`stop` is called.
    """

    def __init__(
        self,
        *,
        url: str = CLOB_WS_URL,
        ping_interval: float = 10.0,
        reconnect_base: float = 1.0,
        reconnect_max: float = 30.0,
        max_tokens_per_connection: int = 500,
        stale_timeout: float = 60.0,
    ) -> None:
        self._url = url
        self._ping_interval = ping_interval
        self._reconnect_base = reconnect_base
        self._reconnect_max = reconnect_max
        self._max_tokens = max_tokens_per_connection
        self._stale_timeout = stale_timeout

        self._running = False
        self._ws: Any = None
        self._last_data_ts = 0.0

    async def run(self, token_ids: list[str], on_event: EventHandler) -> None:
        """Subscribe to ``token_ids`` and dispatch each parsed event to ``on_event``.

        ``on_event`` may be a sync or async callable. This coroutine returns only
        when cancelled or after :meth:`stop`.
        """
        tokens = list(token_ids)[: self._max_tokens]
        if len(token_ids) > self._max_tokens:
            tokens = token_ids[: self._max_tokens]
        self._running = True
        reconnect_attempts = 0

        while self._running:
            ping_task = None
            watchdog_task = None
            try:
                async with websockets.connect(
                    self._url,
                    ping_interval=None,  # we send our own application-level PING
                    ping_timeout=None,
                    open_timeout=20,
                    close_timeout=5,
                    max_size=10_000_000,
                ) as ws:
                    self._ws = ws
                    reconnect_attempts = 0
                    await ws.send(json.dumps({"assets_ids": tokens, "type": "market"}))
                    self._last_data_ts = time.monotonic()

                    ping_task = asyncio.create_task(self._ping_loop(ws))
                    watchdog_task = asyncio.create_task(self._stale_watchdog(ws))

                    await self._message_loop(ws, on_event)
            except (OSError, websockets.exceptions.WebSocketException):
                # Connection dropped / refused — fall through to backoff.
                pass
            finally:
                for task in (ping_task, watchdog_task):
                    if task and not task.done():
                        task.cancel()
                self._ws = None

            if not self._running:
                break
            backoff = min(
                self._reconnect_base * (2**reconnect_attempts), self._reconnect_max
            )
            reconnect_attempts += 1
            await asyncio.sleep(backoff)

    async def stop(self) -> None:
        """Stop the run loop and close the active connection."""
        self._running = False
        if self._ws is not None:
            try:
                await self._ws.close()
            except Exception:
                pass

    async def _message_loop(self, ws: Any, on_event: EventHandler) -> None:
        async for message in ws:
            if message == "PONG":
                continue
            try:
                data = json.loads(message)
            except (json.JSONDecodeError, TypeError):
                continue

            items = data if isinstance(data, list) else [data]
            for item in items:
                if not isinstance(item, dict):
                    continue
                self._last_data_ts = time.monotonic()
                event = parse_event(item)
                if event is None:
                    continue
                result = on_event(event)
                if inspect.isawaitable(result):
                    await result

    async def _ping_loop(self, ws: Any) -> None:
        while self._running:
            await asyncio.sleep(self._ping_interval)
            try:
                await ws.send("PING")
            except Exception:
                return

    async def _stale_watchdog(self, ws: Any) -> None:
        while self._running:
            await asyncio.sleep(self._stale_timeout)
            if time.monotonic() - self._last_data_ts > self._stale_timeout:
                try:
                    await ws.close()
                finally:
                    return
