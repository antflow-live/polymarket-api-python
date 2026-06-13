"""Gamma field decoding and WebSocket event parsing — both pure, both offline."""

from polymarket_api import Market, decode_json_list, parse_event
from polymarket_api.ws import (
    BookUpdate,
    LastTradePrice,
    MarketResolved,
    PriceChange,
    TickSizeChange,
)


def test_decode_json_list_handles_string_and_list():
    assert decode_json_list('["0.47","0.53"]') == ["0.47", "0.53"]
    assert decode_json_list(["a", "b"]) == ["a", "b"]
    assert decode_json_list(None) == []
    assert decode_json_list("not json") == []


def test_market_from_dict_decodes_string_fields():
    market = Market.from_dict(
        {
            "id": "1234",
            "question": "Will it rain?",
            "slug": "will-it-rain",
            "active": True,
            "closed": False,
            "acceptingOrders": True,
            "enableOrderBook": True,
            "negRisk": False,
            "outcomes": '["Yes","No"]',
            "outcomePrices": '["0.47","0.53"]',
            "clobTokenIds": '["111","222"]',
            "volume24hr": "1500.5",
            "spread": "0.02",
            "endDate": "2026-12-31T00:00:00Z",
        }
    )
    assert market.outcomes == ["Yes", "No"]
    assert market.outcome_prices == [0.47, 0.53]
    assert market.clob_token_ids == ["111", "222"]
    assert market.yes_token_id == "111"
    assert market.no_token_id == "222"
    assert market.volume_24hr == 1500.5
    assert market.spread == 0.02


def test_market_missing_tokens_returns_none():
    market = Market.from_dict({"id": "1", "question": "q", "clobTokenIds": "[]"})
    assert market.yes_token_id is None
    assert market.no_token_id is None


def test_parse_price_change_event():
    event = parse_event(
        {"event_type": "price_change", "asset_id": "tok", "best_bid": "0.52", "best_ask": "0.53"}
    )
    assert isinstance(event, PriceChange)
    assert event.token_id == "tok"
    assert event.best_bid == 0.52
    assert event.best_ask == 0.53


def test_parse_batched_price_change_event():
    event = parse_event(
        {
            "event_type": "price_change",
            "price_changes": [{"asset_id": "tok", "best_bid": "0.10", "best_ask": "0.11"}],
        }
    )
    assert isinstance(event, PriceChange)
    assert event.token_id == "tok"
    assert event.best_bid == 0.10


def test_parse_book_event_derives_touch():
    event = parse_event(
        {
            "event_type": "book",
            "asset_id": "tok",
            "bids": [["0.40", "10"], ["0.42", "5"]],
            "asks": [["0.45", "5"], ["0.50", "3"]],
        }
    )
    assert isinstance(event, BookUpdate)
    assert event.best_bid == 0.42
    assert event.best_ask == 0.45


def test_parse_trade_and_tick_and_resolved():
    trade = parse_event({"event_type": "last_trade_price", "asset_id": "tok", "price": "0.5"})
    assert isinstance(trade, LastTradePrice) and trade.price == 0.5

    tick = parse_event(
        {"event_type": "tick_size_change", "asset_id": "tok", "old_tick_size": "0.01", "new_tick_size": "0.001"}
    )
    assert isinstance(tick, TickSizeChange) and tick.new_tick_size == "0.001"

    resolved = parse_event(
        {"event_type": "market_resolved", "market": "0xcond", "winning_outcome": "Yes"}
    )
    assert isinstance(resolved, MarketResolved) and resolved.condition_id == "0xcond"


def test_unknown_event_returns_none():
    assert parse_event({"event_type": "heartbeat"}) is None
