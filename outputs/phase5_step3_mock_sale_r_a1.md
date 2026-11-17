UNVALIDATED · FOUNDER OVERRIDE

# Phase 5 · Step 3 · Sale to cash (MOCKED)

No payment of any kind runs: every event below is a local MOCKED record in SQLite. No card field, payment SDK or network call exists.

## Event trail

| # | Step | Result |
|---|---|---|
| 1 | Payment event received | MOCKED · payment event evt_20261117T203304Z-r_1 → order ord_20261117T203304Z-r_1 status paid, fee 95 minor units |
| 2 | Product files verified | MOCKED · product files re-hashed before grant: match |
| 3 | Automatic delivery | MOCKED · download with token → allowed=True |
| 4 | Duplicate event (idempotency) | MOCKED · same event replayed → duplicate=True, no second entitlement |
| 5 | Refund and access revoked | MOCKED · refund → refunded; download afterwards allowed=False (revoked after refund) |
| 6 | Reconciliation | MOCKED · reconcile: gross 1900, fees 95, refunds 1900, net -95; matched=True; payout po_e310d0dc SIMULATED · no transfer initiated |

## Cash summary (MOCKED)

| Line | Amount |
|---|---|
| Orders | 1 |
| Gross | 19.00 USD |
| Processor fees (mock rate, ASSUMPTION) | 0.95 USD |
| Refunds (1) | 19.00 USD |
| Net | -0.95 USD |
| Payout | po_e310d0dc SIMULATED · no transfer initiated |

## What this shows

- A payment event triggers delivery automatically, only after the product files match the released hashes.
- Replaying the same event does not deliver twice; a refund revokes future downloads.
- Orders, payments, fees, refunds and the payout batch reconcile to the cent.

It does not show that anyone will buy: no real customer was involved.
