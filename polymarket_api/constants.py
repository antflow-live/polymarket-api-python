"""Public Polymarket API endpoints and network constants.

These are the public, documented Polymarket endpoints — no credentials are
required to reach Gamma or to read the CLOB order book. Override the hosts if
you proxy the API or point at a test environment.
"""

from __future__ import annotations

# Gamma — read-only market & event metadata.
GAMMA_API_URL = "https://gamma-api.polymarket.com"

# CLOB — Central Limit Order Book REST API (book reads are public).
CLOB_API_URL = "https://clob.polymarket.com"

# CLOB market-channel WebSocket (public price/book streaming).
CLOB_WS_URL = "wss://ws-subscriptions-clob.polymarket.com/ws/market"

# Polygon mainnet. Polymarket settles on Polygon.
POLYGON_CHAIN_ID = 137
