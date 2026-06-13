# Auth and keys: what L1 and L2 actually mean

Reading markets and the order book needs **no credentials**. Trading needs two distinct layers of auth, and conflating them is the most common reason a first order fails. Here's the mental model.

## The two layers

| Layer | What it is | Used for |
| --- | --- | --- |
| **L1 — wallet key** | Your Polygon wallet's private key. Every order is EIP-712-**signed** with it. | Proving you authorize a specific order. |
| **L2 — API credentials** | An `api_key` / `secret` / `passphrase` triple, *derived from* your wallet. Each trading request is HMAC-signed with the secret. | Authenticating your session against the trading endpoints. |

Trading is **non-custodial**: your funds stay in your wallet and Polymarket's smart contracts. The L1 key signs orders; the API never holds your money. That also means **securing the key is entirely your responsibility** — a leaked key is an irreversible loss.

## Getting credentials

`make_trading_client` does the L1→L2 dance for you: it builds the official client from your wallet key, then derives (or creates) the L2 credentials and attaches them.

```python
import os
from polymarket_api.orders import make_trading_client

client = make_trading_client(os.environ["POLYMARKET_PRIVATE_KEY"])
# Now authenticated for both signing (L1) and trading requests (L2).
```

Requires the trading extra:

```bash
pip install "polymarket-api-python[trading]"
```

### Reuse credentials instead of re-deriving

Deriving on every start is fine, but you can derive once, store the triple securely, and pass it back to skip the round trip:

```python
from py_clob_client_v2 import ApiCreds
from polymarket_api.orders import make_trading_client

creds = ApiCreds(
    api_key=os.environ["CLOB_API_KEY"],
    api_secret=os.environ["CLOB_SECRET"],
    api_passphrase=os.environ["CLOB_PASSPHRASE"],
)
client = make_trading_client(os.environ["POLYMARKET_PRIVATE_KEY"], api_creds=creds)
```

## Keeping the key safe

- **Load from the environment or a secret manager. Never hard-code it, never commit it.** This repo's `.gitignore` excludes `.env`, `*.key`, `*.pem`, and `*.secret` for exactly this reason.
- **Scope exposure tightly.** Use a dedicated wallet for automated trading with only the funds you intend to risk, not your main wallet.
- **Treat the L2 secret like a password too.** It can place and cancel orders for the session even without re-signing each request.

## Gotchas

- **`401 Invalid api key` on a `post_order` while reads work.** This almost always means L2 creds weren't set (or were set on a different client instance than the one posting). Derive creds and `set_api_creds` on the *same* client you trade with — `make_trading_client` does this for you.
- **Proxy / smart-contract wallets need a `signature_type` (and sometimes a `funder`).** A plain EOA needs neither. If you trade through a Polymarket proxy wallet, pass `signature_type=` / `funder=` to `make_trading_client`.
- **API versions move.** `py_clob_client_v2` is the current standalone CLOB client; Polymarket also publishes a newer unified `py-sdk`. The L1/L2 split above is stable across both — only method names differ.

---

Built by antflow — https://antflow.live
