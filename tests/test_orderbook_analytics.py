"""Order-book analytics are pure functions — test them without any network."""

from polymarket_api import parse_order_book


def _book():
    # Deliberately unsorted to prove parse_order_book re-sorts by price.
    return {
        "timestamp": "1745000000",
        "bids": [
            {"price": "0.60", "size": "100"},
            {"price": "0.62", "size": "50"},   # best bid
            {"price": "0.55", "size": "999"},  # outside 5% of mid
        ],
        "asks": [
            {"price": "0.66", "size": "40"},
            {"price": "0.63", "size": "30"},   # best ask
            {"price": "0.80", "size": "999"},  # outside 5% of mid
        ],
    }


def test_best_bid_ask_and_spread():
    snap = parse_order_book("tok", _book())
    assert snap.best_bid == 0.62
    assert snap.best_ask == 0.63
    assert round(snap.spread, 4) == 0.01
    assert round(snap.mid_price, 4) == 0.625
    # 0.01 / 0.625 * 10_000 = 160 bps
    assert round(snap.spread_bps) == 160


def test_levels_are_sorted():
    snap = parse_order_book("tok", _book())
    assert [b["price"] for b in snap.bids] == [0.62, 0.60, 0.55]
    assert [a["price"] for a in snap.asks] == [0.63, 0.66, 0.80]


def test_depth_within_5pct_excludes_far_levels():
    snap = parse_order_book("tok", _book())
    # mid=0.625 → bid threshold 0.59375, ask threshold 0.65625.
    # bid 0.55 (size 999) and ask 0.80 (size 999) are excluded.
    assert snap.bid_depth_5pct == 150.0  # 50 + 100
    assert snap.ask_depth_5pct == 30.0   # only the 0.63 level
    assert snap.total_bid_liquidity == 1149.0
    assert snap.total_ask_liquidity == 1069.0
    assert snap.bid_levels == 3
    assert snap.ask_levels == 3


def test_list_pair_levels_are_supported():
    snap = parse_order_book("tok", {"bids": [["0.40", "10"]], "asks": [["0.45", "5"]]})
    assert snap.best_bid == 0.40
    assert snap.best_ask == 0.45


def test_empty_book_is_safe():
    snap = parse_order_book("tok", {"bids": [], "asks": []})
    assert snap.best_bid is None
    assert snap.best_ask is None
    assert snap.spread is None
    assert snap.bid_depth_5pct == 0.0
