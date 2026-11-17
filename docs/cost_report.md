# Cost per run (generated from decision_log.json)

Observed charges come from the log (`cost` field, USD). Local and free-tier calls are charged $0.00. Electricity and hardware are not included (ASSUMPTION).

| Run ID | Outcome | Model calls | Tokens (prompt + completion) | Observed charge | System time (s) | Tiers |
|---|---|---|---|---|---|---|
| 20261117T210325Z-r | stop | 16 | 19963 (13965 + 5998) | $0.00 | 239.5 | local/llamacpp: 16 calls, 19963 tokens |
| 20261117T211039Z-w | pivot_back | 6 | 9701 (7420 + 2281) | $0.00 | 91.7 | local/llamacpp: 6 calls, 9701 tokens |
| 20261117T211229Z-e | stop | 0 | 0 (0 + 0) | $0.00 | 0.0 | none (no model call) |
| payment-test-20261117T211229Z | None | 0 | 0 (0 + 0) | $0.00 | None | none (no model call) |

Complete six-phase run 20261117T210325Z-r: 16 model calls, 19963 tokens, $0.00 observed charges.
