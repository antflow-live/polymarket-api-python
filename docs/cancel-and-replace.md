# Cancel and replace

An unfilled limit order rests on the book until it fills, expires, or you pull it. Repricing — moving your quote as the market moves — is a *cancel* of the old order followed by a *place* of a new one. The risk in any networked trading loop is the retry that hides a success and double-fills. The fix is a **deterministic client order id**.

## Cancel an order

```python
from polymarket_api.orders import cancel_order

cancel_order(client, "<orderID>")   # the id returned when you placed it
```

## The cancel-and-replace pattern

```python
from polymarket_api import fetch_order_book
from polymarket_api.orders import place_limit_order, cancel_order

state = {"order_id": None}

def reprice(client, token_id, *, size=20):
    book = fetch_order_book(token_id)
    target = round(book.best_bid, 2)   # quote just behind the touch

    if state["order_id"]:
        cancel_order(client, state["order_id"])

    resp = place_limit_order(client, token_id=token_id, price=target, size=size, side="BUY")
    state["order_id"] = resp.get("orderID")
    return state["order_id"]
```

## Idempotent submission with a client order id

`build_client_order_id` turns stable inputs into a repeatable id. Build it from inputs that identify *this specific attempt*; a network retry then reproduces the same id (and the CLOB treats it as the same order), while a genuinely new order — bump the retry counter — gets a fresh one.

```python
from polymarket_api import build_client_order_id

coid = build_client_order_id("my-strategy", token_id, retry=0)
# Pass coid to your order builder so a retried POST can't double-fill.
# Same inputs → same id (safe to resend); change any input → new id.
```

```python
>>> build_client_order_id("my-strategy", "7132…token", 0)
'9f2c1ab8e4d7...'   # 32 hex chars, identical on every call
>>> build_client_order_id("my-strategy", "7132…token", 1)
'5b0a77c3f1e2...'   # bumping the retry counter → a new order
```

## Gotchas

- **Cancel can race a fill.** Between deciding to cancel and the cancel landing, the order may fill. Treat "cancel failed / already gone" as a possible fill, then reconcile against the exchange before re-placing — don't assume the size is free.
- **Reconcile after any disconnect.** After a dropped connection, your local view of open orders may be wrong. Pull current orders/positions from the exchange before acting again, rather than trusting stale local state.
- **Don't churn the book.** Each reprice is a cancel + a place, both of which count against the [rate limit](rate-limits.md). Reprice on a meaningful move (or a timer), not on every tick.
- **A new id is a new order.** Reusing the same client order id intentionally is what makes a retry safe; reusing it *unintentionally* for a different order can get the second one ignored. Make the inputs uniquely identify the attempt.

---

Built by antflow — https://antflow.live
