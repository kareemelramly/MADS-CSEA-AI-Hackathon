# Cost per run (generated from decision_log.json)

Observed charges come from the log (`cost` field, USD). Local and free-tier calls are charged $0.00. Electricity and hardware are not included (ASSUMPTION).

| Run ID | Outcome | Model calls | Tokens (prompt + completion) | Observed charge | System time (s) | Tiers |
|---|---|---|---|---|---|---|
| 20261117T165636Z-w | None | 7 | 10902 (8213 + 2689) | $0.00 | None | tier3/llamacpp: 7 calls, 10902 tokens |
| 20261117T165843Z-e | stop | 0 | 0 (0 + 0) | $0.00 | 0.0 | none (no model call) |
| 20261117T165843Z-r | stop | 6 | 7935 (5790 + 2145) | $0.00 | 56.0 | tier3/llamacpp: 6 calls, 7935 tokens |
| payment-test-20261117T170053Z | None | 0 | 0 (0 + 0) | $0.00 | None | none (no model call) |

Full-run measurement (from 1 complete run, label r): 6 model calls, 7935 tokens.
If every call went to Groq's free tier (200,000 tokens/day, provider page read 17 Nov 2026), about 25 full runs per day would fit (estimate).
