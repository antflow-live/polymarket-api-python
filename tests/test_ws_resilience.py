"""The market feed must survive bad events and throwing handlers (no network)."""

import json

from polymarket_api import PriceChange
from polymarket_api.ws import ClobWebSocketClient, parse_event


class _FakeWS:
    """Minimal async-iterable stand-in for a websocket connection."""

    def __init__(self, messages):
        self._messages = list(messages)

    def __aiter__(self):
        return self

    async def __anext__(self):
        if not self._messages:
            raise StopAsyncIteration
        return self._messages.pop(0)


def _price_msg(asset_id, bid, ask):
    return json.dumps(
        {
            "event_type": "price_change",
            "asset_id": asset_id,
            "best_bid": bid,
            "best_ask": ask,
        }
    )


async def test_throwing_handler_does_not_drop_the_feed():
    """A handler that raises on one event must not stop later events."""
    seen = []

    async def handler(event):
        seen.append(event.token_id)
        if event.token_id == "A":
            raise ValueError("boom")  # must be isolated, not fatal

    client = ClobWebSocketClient()
    client._running = True
    await client._message_loop(
        _FakeWS([_price_msg("A", "0.5", "0.6"), _price_msg("B", "0.4", "0.5")]),
        handler,
    )

    assert seen == ["A", "B"]  # B was still delivered after A raised


async def test_malformed_messages_are_skipped():
    """Non-JSON, non-dict, and unknown-type messages don't raise."""
    seen = []

    def handler(event):
        seen.append(event.token_id)

    client = ClobWebSocketClient()
    client._running = True
    await client._message_loop(
        _FakeWS(
            [
                "not json",  # JSONDecodeError → skipped
                json.dumps([1, 2, 3]),  # list of non-dicts → skipped
                json.dumps({"event_type": "who_knows"}),  # unknown type → None
                _price_msg("Z", "0.1", "0.2"),  # the one real event
            ]
        ),
        handler,
    )

    assert seen == ["Z"]


def test_sync_handler_is_supported():
    """parse_event + a sync handler round-trip (smoke)."""
    event = parse_event(
        {"event_type": "price_change", "asset_id": "T", "best_bid": "0.7", "best_ask": "0.8"}
    )
    assert isinstance(event, PriceChange)
    assert event.best_bid == 0.7 and event.best_ask == 0.8
