"""Optional order placement, layered over Polymarket's official client.

Reading markets, snapshotting the book, and streaming prices need **no
credentials** and **no extra dependencies**. Placing or cancelling orders does:
it requires your wallet private key (L1, used to EIP-712-sign each order) and
CLOB API credentials (L2, an HMAC key/secret/passphrase). Rather than reimplement
order signing — which is security-critical and changes whenever Polymarket
revises its exchange contracts — this module is a **thin wrapper over
Polymarket's official, audited** ``py_clob_client_v2`` package.

Install the trading extra::

    pip install "polymarket-api-python[trading]"

This module does NOT implement any signing itself. All EIP-712 signing and order
submission is delegated to ``py_clob_client_v2``.

.. note::
   Polymarket also publishes a newer unified ``py-sdk``. ``py_clob_client_v2`` is
   the current standalone CLOB client and is what these helpers target; if you
   adopt ``py-sdk`` later, the same concepts (build args → sign → post) apply.
"""

from __future__ import annotations

from typing import Any

from .constants import CLOB_API_URL, POLYGON_CHAIN_ID

_INSTALL_HINT = (
    "Order placement requires Polymarket's official client. Install it with:\n"
    '    pip install "polymarket-api-python[trading]"'
)


def _require_clob() -> Any:
    try:
        import py_clob_client_v2  # noqa: F401
    except ImportError as exc:  # pragma: no cover - exercised only without the extra
        raise ImportError(_INSTALL_HINT) from exc
    return __import__("py_clob_client_v2")


def make_trading_client(
    private_key: str,
    *,
    host: str = CLOB_API_URL,
    chain_id: int = POLYGON_CHAIN_ID,
    api_creds: Any = None,
    signature_type: int | None = None,
    funder: str | None = None,
) -> Any:
    """Build an authenticated ``py_clob_client_v2.ClobClient``.

    The fiddly part of getting started is the two-layer auth: an L1 key to sign,
    plus L2 API credentials for the trading endpoints. If ``api_creds`` is
    ``None`` this derives (or creates) them from your key automatically via
    ``create_or_derive_api_key()`` and attaches them.

    ``signature_type`` / ``funder`` are only needed for Polymarket proxy / smart
    -contract wallets — leave them unset for a plain EOA. Never hard-code
    ``private_key``; read it from the environment or a secrets manager.
    """
    _require_clob()
    from py_clob_client_v2 import ClobClient

    kwargs: dict[str, Any] = {"host": host, "chain_id": chain_id, "key": private_key}
    if signature_type is not None:
        kwargs["signature_type"] = signature_type
    if funder is not None:
        kwargs["funder"] = funder
    if api_creds is not None:
        kwargs["creds"] = api_creds

    client = ClobClient(**kwargs)
    if api_creds is None:
        creds = client.create_or_derive_api_key()
        client.set_api_creds(creds)
    return client


def place_limit_order(
    client: Any,
    *,
    token_id: str,
    price: float,
    size: float,
    side: str = "BUY",
    tick_size: str = "0.01",
    order_type: str = "GTC",
) -> Any:
    """Sign and post a limit order via the official client.

    ``side`` is ``"BUY"`` or ``"SELL"``; ``order_type`` is a name on
    ``py_clob_client_v2.OrderType`` (e.g. ``"GTC"``, ``"FOK"``). ``price`` and
    ``size`` are in the CLOB's usual units (price 0–1, size in shares). For
    negative-risk (multi-outcome) markets the client may need a ``neg_risk``
    flag — see the cookbook page ``docs/sign-and-place-an-order.md``.
    """
    _require_clob()
    from py_clob_client_v2 import (
        OrderArgs,
        OrderType,
        PartialCreateOrderOptions,
        Side,
    )

    side_enum = Side.BUY if str(side).upper() == "BUY" else Side.SELL
    order_type_enum = getattr(OrderType, str(order_type).upper())

    return client.create_and_post_order(
        order_args=OrderArgs(
            token_id=token_id, price=price, side=side_enum, size=size
        ),
        options=PartialCreateOrderOptions(tick_size=tick_size),
        order_type=order_type_enum,
    )


def cancel_order(client: Any, order_id: str) -> Any:
    """Cancel a single resting order by its CLOB order id."""
    _require_clob()
    try:
        from py_clob_client_v2 import OrderPayload
    except ImportError:  # payload type lives under clob_types in some versions
        from py_clob_client_v2.clob_types import OrderPayload  # type: ignore

    return client.cancel_order(OrderPayload(orderID=order_id))
