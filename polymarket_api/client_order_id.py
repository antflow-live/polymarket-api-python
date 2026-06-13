"""Deterministic client order ids for idempotent CLOB submission.

A *client order id* lets you retry an order POST without risking a duplicate
fill: rebuild the SAME id from the same inputs and the CLOB treats a repeat
submission as the same order. Derive it from stable inputs — a strategy id, the
market token, and a retry counter — so a network retry reproduces the id while a
genuinely new order gets a fresh one.

The id is a hex digest truncated to 32 chars, which fits comfortably inside the
CLOB's 64-char limit.
"""

from __future__ import annotations

import hashlib

DEFAULT_LENGTH = 32


def build_client_order_id(*parts: object, length: int = DEFAULT_LENGTH) -> str:
    """Build a deterministic client order id from any number of stable parts.

    The same parts always produce the same id; change any part (e.g. bump a retry
    counter for a genuinely new attempt) to get a new one.

    >>> build_client_order_id("my-strategy", "71321...token", 0)
    'c2a9...'  # 32 hex chars, stable across calls
    """
    key = ":".join(str(p) for p in parts)
    return hashlib.sha256(key.encode()).hexdigest()[:length]
