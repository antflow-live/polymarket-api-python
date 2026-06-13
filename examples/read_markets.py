"""List the most-active Polymarket markets. Read-only, no credentials.

    python examples/read_markets.py
"""

from polymarket_api import GammaClient


def main() -> None:
    with GammaClient() as gamma:
        print(f"{'24h vol':>12}  {'YES':>5}  question")
        print("-" * 80)
        for market in gamma.iter_markets(max_markets=15):
            yes = market.outcome_prices[0] if market.outcome_prices else None
            yes_str = f"{yes:.2f}" if yes is not None else "  ?  "
            question = (market.question[:60] + "…") if len(market.question) > 61 else market.question
            print(f"{market.volume_24hr:>12,.0f}  {yes_str:>5}  {question}")


if __name__ == "__main__":
    main()
