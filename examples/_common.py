"""Shared helpers for the runnable examples (NOT part of the library).

Kept here, out of `polymarket_api`, on purpose: choosing *which* market to look
at is application logic, not generic API plumbing.
"""

from __future__ import annotations

from polymarket_api import GammaClient, Market


def pick_tradeable_market(gamma: GammaClient, *, scan: int = 80) -> Market:
    """Return a high-volume market with a genuine two-sided book to demo on.

    Scans the busiest markets and returns the first whose YES price is mid-range
    (0.10–0.90), is accepting orders, and has CLOB token ids — so the snapshot
    and stream show a real spread instead of a 0.00 longshot. Falls back to the
    single busiest market if nothing mid-range is found.
    """
    busiest: Market | None = None
    for market in gamma.iter_markets(max_markets=scan):
        if busiest is None:
            busiest = market
        if not market.clob_token_ids or not market.outcome_prices:
            continue
        yes = market.outcome_prices[0]
        if 0.10 <= yes <= 0.90 and market.accepting_orders:
            return market
    if busiest is None:
        raise RuntimeError("Gamma returned no markets.")
    return busiest
