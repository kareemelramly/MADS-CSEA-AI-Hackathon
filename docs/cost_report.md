# Cost per run (generated from decision_log.json)

Observed charges come from the log (`cost` field, USD). Local and free-tier calls are charged $0.00. Electricity and hardware are not included (ASSUMPTION).

| Run ID | Outcome | Model calls | Tokens (prompt + completion) | Observed charge | System time (s) | Tiers |
|---|---|---|---|---|---|---|
| 20261117T201525Z-r | stop | 16 | 19222 (13225 + 5997) | $0.00 | 230.6 | local/llamacpp: 16 calls, 19222 tokens |
| 20261117T202306Z-w | stop | 6 | 9623 (7335 + 2288) | $0.00 | 88.0 | local/llamacpp: 6 calls, 9623 tokens |
| 20261117T202438Z-e | stop | 0 | 0 (0 + 0) | $0.00 | 0.0 | none (no model call) |
| payment-test-20261117T202438Z | None | 0 | 0 (0 + 0) | $0.00 | None | none (no model call) |

Complete six-phase run 20261117T201525Z-r: 16 model calls, 19222 tokens, $0.00 observed charges.
