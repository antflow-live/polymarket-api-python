# Sign and place an order

This toolkit does **not** implement order signing. EIP-712 order signing is security-critical and changes whenever Polymarket revises its exchange contracts, so the order layer is a thin wrapper over Polymarket's official, audited **py-clob-client** (the `py_clob_client_v2` package) — which does all the signing. You provide the inputs and a securely-loaded key; the official client signs and submits.

```bash
pip install "polymarket-api-python[trading]"
```

> Placing an order moves real funds. Test against a throwaway wallet and tiny sizes first. See [auth-and-keys.md](auth-and-keys.md) for how L1 (wallet key) and L2 (API creds) fit together.

## Place a limit order

```python
import os
from polymarket_api import GammaClient, fetch_order_book
from polymarket_api.orders import make_trading_client, place_limit_order

# 1) Find a token and read the book to pick a sane price.
with GammaClient() as gamma:
    market = next(iter(gamma.iter_markets(max_markets=1)))
token_id = market.yes_token_id
book = fetch_order_book(token_id)
print(f"touch: bid {book.best_bid} / ask {book.best_ask}")

# 2) Authenticate (derives L2 creds from your wallet key).
client = make_trading_client(os.environ["POLYMARKET_PRIVATE_KEY"])

# 3) Sign + post a resting bid just behind the touch.
resp = place_limit_order(
    client,
    token_id=token_id,
    price=round(book.best_bid, 2),
    size=20,          # shares
    side="BUY",
    tick_size="0.01",
)
print(resp)
```

Expected output (shape; fields depend on the client version):

```
touch: bid 0.62 / ask 0.63
{'success': True, 'orderID': '0xabc…', 'status': 'live', ...}
```

Keep the returned `orderID` — you need it to [cancel or replace](cancel-and-replace.md) the order.

## Under the hood

`place_limit_order` is a thin pass-through. The equivalent direct call against the official client is:

```python
from py_clob_client_v2 import OrderArgs, OrderType, PartialCreateOrderOptions, Side

resp = client.create_and_post_order(
    order_args=OrderArgs(token_id=token_id, price=0.62, side=Side.BUY, size=20),
    options=PartialCreateOrderOptions(tick_size="0.01"),
    order_type=OrderType.GTC,
)
```

Drop to the direct call whenever you need an argument the wrapper doesn't expose.

## Limit vs. marketable orders

- **Limit orders** specify the worst price you'll accept. They give you price control and can rest on the book to provide liquidity, but may not fill if the market moves away. Default for most automated strategies.
- **Marketable orders** (e.g. `OrderType.FOK`) cross the spread to fill now against resting liquidity. Certainty of execution, but you pay the spread and risk slippage on thin books. Reserve for exits that can't wait.

Either way, **size against visible depth** (`book.bid_depth_5pct` / `ask_depth_5pct`) — an order larger than the resting liquidity walks the book.

## Gotchas

- **`price` must sit on the tick.** Pass the market's current `tick_size` (often `"0.01"`, but it tightens near the 0/1 bounds). An off-tick price is rejected. Round your price to the tick.
- **Negative-risk markets settle on a different exchange contract.** For `market.neg_risk == True`, the client needs to know it's a neg-risk order; check `py_clob_client_v2`'s order options for the `neg_risk` flag rather than assuming the binary path.
- **Respect the minimum order size.** The CLOB rejects orders below a per-market floor. The `/book` response carries it — read `fetch_order_book(token_id).min_order_size` (commonly a few shares / ~$1 notional) and size above it.
- **A marketable BUY is notional-capped and can overfill.** A market/FOK *buy* caps the dollars you spend, not the shares you get: if it fills better than the touch, you receive *more* shares than the nominal size. Don't assume requested size == filled size — read the response back and reconcile against your position.
- **Make retries idempotent.** A network blip can hide a success. Use a deterministic [client order id](cancel-and-replace.md) so a retry can't double-fill.
- **This is not financial advice.** This page shows the mechanics of the API, not what to trade. Outcomes are your responsibility.

---

Built by antflow — https://antflow.live
