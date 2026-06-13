"""polymarket-api-python — a typed Python client for the Polymarket API.

Read Gamma markets, snapshot and stream the CLOB order book, generate idempotent
client order ids, and (optionally) place orders via Polymarket's official client.

The read / stream / analytics surface needs only ``httpx`` and ``websockets`` and
no credentials. Order placement is opt-in (``pip install
"polymarket-api-python[trading]"``).

Built by antflow (https://antflow.live), an autonomous Polymarket trading bot.
"""

from __future__ import annotations

from .client_order_id import build_client_order_id
from .constants import (
    CLOB_API_URL,
    CLOB_WS_URL,
    GAMMA_API_URL,
    POLYGON_CHAIN_ID,
)
from .gamma import GammaClient, Market, decode_json_list
from .orderbook import OrderBookSnapshot, fetch_order_book, parse_order_book
from .ws import (
    BookUpdate,
    ClobWebSocketClient,
    LastTradePrice,
    MarketResolved,
    PriceChange,
    TickSizeChange,
    parse_event,
)

__version__ = "0.1.0"

__all__ = [
    # constants
    "GAMMA_API_URL",
    "CLOB_API_URL",
    "CLOB_WS_URL",
    "POLYGON_CHAIN_ID",
    # gamma
    "GammaClient",
    "Market",
    "decode_json_list",
    # orderbook
    "OrderBookSnapshot",
    "fetch_order_book",
    "parse_order_book",
    # websocket
    "ClobWebSocketClient",
    "PriceChange",
    "BookUpdate",
    "LastTradePrice",
    "TickSizeChange",
    "MarketResolved",
    "parse_event",
    # client order id
    "build_client_order_id",
    "__version__",
]
