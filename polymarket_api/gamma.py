"""Read Polymarket markets from the public Gamma API.

The Gamma API (``https://gamma-api.polymarket.com``) is Polymarket's read-only
metadata API. This module wraps the ``/markets`` endpoint with a small typed
client that handles the two things that trip up most callers:

1. **The ``/markets`` endpoint silently CLAMPS ``limit`` to 100.** Asking for
   ``limit=500`` still returns 100 rows, so naive offset stepping (offset += 500)
   skips four out of every five markets. :meth:`GammaClient.iter_markets` pages in
   steps of 100 so coverage is contiguous.
2. **Some fields come back as JSON-encoded STRINGS, not arrays.** ``outcomes``,
   ``outcomePrices`` and ``clobTokenIds`` arrive as e.g. ``'["0.47","0.53"]'``.
   :class:`Market` decodes them for you, so ``market.clob_token_ids`` is a real list.

No API key is required for Gamma reads.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from typing import Any, Iterator

import httpx

from .constants import GAMMA_API_URL

# The Gamma /markets endpoint silently clamps `limit` to this value.
GAMMA_MARKET_PAGE_SIZE = 100


def decode_json_list(value: Any) -> list:
    """Decode a Gamma list field that may be a JSON-encoded string or a real list.

    Gamma returns ``outcomes``, ``outcomePrices`` and ``clobTokenIds`` as
    JSON-encoded strings (``'["0.47","0.53"]'``). Returns ``[]`` for missing or
    unparseable values rather than raising.
    """
    if value is None:
        return []
    if isinstance(value, str):
        try:
            return json.loads(value)
        except (json.JSONDecodeError, ValueError):
            return []
    return list(value)


@dataclass
class Market:
    """A Gamma market with its string-encoded list fields decoded.

    ``clob_token_ids[0]`` is the YES outcome token and ``clob_token_ids[1]`` is
    NO; ``outcome_prices`` lines up 1:1 with ``outcomes``. Use :attr:`yes_token_id`
    / :attr:`no_token_id` to read the book or subscribe to price updates.
    """

    id: str
    question: str
    slug: str
    active: bool
    closed: bool
    accepting_orders: bool
    enable_order_book: bool
    neg_risk: bool
    outcomes: list[str]
    outcome_prices: list[float]
    clob_token_ids: list[str]
    volume_24hr: float
    spread: float | None
    end_date: str | None
    raw: dict = field(default_factory=dict, repr=False)

    @classmethod
    def from_dict(cls, d: dict) -> "Market":
        prices: list[float] = []
        for p in decode_json_list(d.get("outcomePrices")):
            try:
                prices.append(float(p))
            except (TypeError, ValueError):
                continue
        spread = d.get("spread")
        return cls(
            id=str(d.get("id", "")),
            question=d.get("question", "") or "",
            slug=d.get("slug", "") or "",
            active=bool(d.get("active", False)),
            closed=bool(d.get("closed", False)),
            accepting_orders=bool(d.get("acceptingOrders", False)),
            enable_order_book=bool(d.get("enableOrderBook", False)),
            neg_risk=bool(d.get("negRisk", False)),
            outcomes=[str(o) for o in decode_json_list(d.get("outcomes"))],
            outcome_prices=prices,
            clob_token_ids=[str(t) for t in decode_json_list(d.get("clobTokenIds"))],
            volume_24hr=float(d.get("volume24hr") or 0.0),
            spread=(float(spread) if spread is not None else None),
            end_date=d.get("endDate") or d.get("endDateIso"),
            raw=d,
        )

    @property
    def yes_token_id(self) -> str | None:
        """CLOB token id for the YES outcome, or ``None`` if unavailable."""
        return self.clob_token_ids[0] if self.clob_token_ids else None

    @property
    def no_token_id(self) -> str | None:
        """CLOB token id for the NO outcome, or ``None`` if unavailable."""
        return self.clob_token_ids[1] if len(self.clob_token_ids) > 1 else None


class GammaClient:
    """Minimal synchronous client for the public Polymarket Gamma read API.

    Usable as a context manager (``with GammaClient() as g: ...``) so the
    underlying HTTP connection pool is closed for you. Pass your own
    ``httpx.Client`` to reuse a pool or set custom transport options.
    """

    def __init__(
        self,
        base_url: str = GAMMA_API_URL,
        *,
        timeout: float = 10.0,
        client: httpx.Client | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._client = client
        self._owns_client = client is None

    def _http(self) -> httpx.Client:
        if self._client is None:
            self._client = httpx.Client(timeout=self._timeout)
        return self._client

    def close(self) -> None:
        if self._owns_client and self._client is not None:
            self._client.close()
            self._client = None

    def __enter__(self) -> "GammaClient":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def get_markets(
        self,
        *,
        limit: int = GAMMA_MARKET_PAGE_SIZE,
        offset: int = 0,
        active: bool | None = True,
        closed: bool | None = False,
        order: str | None = "volume24hr",
        ascending: bool = False,
        **params: Any,
    ) -> list[Market]:
        """Fetch one page of markets.

        ``limit`` is capped at 100 (the server clamps it anyway). Extra keyword
        arguments are forwarded as query params, so you can pass any filter the
        Gamma API supports (e.g. ``tag_id=...``, ``liquidity_num_min=...``).
        """
        query: dict[str, Any] = {
            "limit": min(limit, GAMMA_MARKET_PAGE_SIZE),
            "offset": offset,
            "ascending": str(ascending).lower(),
        }
        if active is not None:
            query["active"] = str(active).lower()
        if closed is not None:
            query["closed"] = str(closed).lower()
        if order is not None:
            query["order"] = order
        query.update(params)

        resp = self._http().get(f"{self._base_url}/markets", params=query)
        resp.raise_for_status()
        data = resp.json()
        return [Market.from_dict(m) for m in data]

    def iter_markets(
        self,
        *,
        max_markets: int = 1000,
        page_sleep: float = 0.3,
        **kwargs: Any,
    ) -> Iterator[Market]:
        """Yield markets across pages, stepping the offset by 100 (the real page size).

        Stops after ``max_markets`` or when a page comes back empty. ``page_sleep``
        spaces requests out to stay well under the Gamma rate limit. Any other
        keyword argument (``active``, ``closed``, ``order``, ...) is passed through
        to :meth:`get_markets`.
        """
        offset = 0
        fetched = 0
        while fetched < max_markets:
            page = self.get_markets(offset=offset, **kwargs)
            if not page:
                break
            for market in page:
                yield market
                fetched += 1
                if fetched >= max_markets:
                    return
            offset += GAMMA_MARKET_PAGE_SIZE
            if page_sleep:
                time.sleep(page_sleep)

    def get_market(self, market_id: str) -> Market:
        """Fetch a single market by its Gamma id."""
        resp = self._http().get(f"{self._base_url}/markets/{market_id}")
        resp.raise_for_status()
        return Market.from_dict(resp.json())
