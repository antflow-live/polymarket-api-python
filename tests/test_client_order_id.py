"""Client order ids must be deterministic and length-bounded."""

from polymarket_api import build_client_order_id


def test_is_deterministic():
    a = build_client_order_id("strategy-x", "token-123", 0)
    b = build_client_order_id("strategy-x", "token-123", 0)
    assert a == b


def test_distinct_inputs_differ():
    base = build_client_order_id("strategy-x", "token-123", 0)
    retry = build_client_order_id("strategy-x", "token-123", 1)
    other_token = build_client_order_id("strategy-x", "token-999", 0)
    assert base != retry
    assert base != other_token


def test_default_length_fits_clob_limit():
    coid = build_client_order_id("a", "b", 0)
    assert len(coid) == 32
    assert len(coid) <= 64


def test_custom_length():
    assert len(build_client_order_id("a", length=16)) == 16


def test_hex_only():
    coid = build_client_order_id("a", "b", 2)
    assert all(c in "0123456789abcdef" for c in coid)
