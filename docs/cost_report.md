# Cost per run (generated from decision_log.json)

Observed charges come from the log (`cost` field, USD). Local and free-tier calls are charged $0.00. Electricity and hardware are not included (ASSUMPTION).

| Run ID | Outcome | Model calls | Tokens (prompt + completion) | Observed charge | System time (s) | Tiers |
|---|---|---|---|---|---|---|
| 20261117T194739Z-r | stop | 15 | 18411 (12865 + 5546) | $0.00 | 77.1 | local/llamacpp: 15 calls, 18411 tokens |
| 20261117T195109Z-w | pivot_back | 6 | 9636 (7334 + 2302) | $0.00 | 32.4 | local/llamacpp: 6 calls, 9636 tokens |
| 20261117T195149Z-e | stop | 0 | 0 (0 + 0) | $0.00 | 0.0 | none (no model call) |
| payment-test-20261117T195150Z | None | 0 | 0 (0 + 0) | $0.00 | None | none (no model call) |

Complete six-phase run 20261117T194739Z-r: 15 model calls, 18411 tokens, $0.00 observed charges.
