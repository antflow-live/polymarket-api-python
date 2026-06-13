# Rate limits

Any system that trades around the clock has to respect rate limits and survive the messy reality of networks. Polymarket enforces limits with Cloudflare using **sliding windows**, and over-limit requests are throttled (delayed/queued), not silently dropped. The figures below are current as of 2026 — always confirm against the [official rate-limit docs](https://docs.polymarket.com/quickstart/introduction/rate-limits), since they change.

## The limits that matter

| Endpoint group | Limit |
| --- | --- |
| CLOB general | ~9,000 requests / 10s |
| Market data — `/book`, `/price`, `/midpoint` (single) | ~1,500 / 10s |
| Market data — batch | ~500 / 10s |
| `POST /order` | ~3,500 / 10s burst, ~36,000 / 10min sustained (~60/s avg) |
| `DELETE /order` | ~3,000 / 10s burst, ~30,000 / 10min sustained |
| Batch `POST /orders` / `DELETE /orders` | ~1,000 / 10s burst, ~15,000 / 10min sustained |

Note the **dual-tier** trading limits: a short burst window *and* a longer sustained window. A loop that bursts fine over 10 seconds can still trip the 10-minute ceiling. Budget against both.

## Stay under the limit by design

- **Stream, don't poll.** A single [WebSocket](websockets.md) subscription replaces a polling loop over `/book` for many tokens, and it's closer to live. This toolkit's `ClobWebSocketClient` is the intended path for live prices.
- **Reuse one HTTP client.** Pass a shared `httpx.Client` into `fetch_order_book` (and reuse one `GammaClient`) so you're not paying connection setup per request.
- **Space out pagination.** `GammaClient.iter_markets(page_sleep=0.3)` already paces page fetches; keep a small sleep when sweeping many pages.
- **Reprice on meaningful moves.** Cancel-and-replace is two trading calls. Repricing on every tick burns the trading budget fast — gate on a price move or a timer.

## Handle the throttle gracefully

- **Back off and retry** on `429` and transient errors with exponential backoff — don't hammer. (The WebSocket client already backs off on reconnect.)
- **Make retries idempotent.** Use a deterministic [client order id](cancel-and-replace.md) so a retried `POST /order` can't double-fill.
- **Fail safe, not open.** When data is stale or a call fails, the correct default is usually to *do nothing*, not to guess. A trader that fails open places orders on bad data.

## Gotchas

- **Throttling looks like latency, not errors.** Because Cloudflare queues over-limit requests, you may see rising latency before you see rejections. Watch your request timing, not just error codes.
- **The 10-minute window is the sneaky one.** Bursty repricing can pass every 10-second check and still hit the sustained ceiling. Track a rolling 10-minute count for trading calls.
- **Limits are shared across your IP / credentials.** Multiple processes on one box draw from the same budget. Coordinate, or shard across credentials.

---

Built by antflow — https://antflow.live
