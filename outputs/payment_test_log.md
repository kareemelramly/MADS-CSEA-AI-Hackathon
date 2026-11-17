# Payment and delivery test log (MOCKED)

MOCKED · run payment-test-20261117T211229Z · 2026-11-17T21:12:29Z · local SQLite ledger, no payment SDK, no network, no card fields. No payment of any kind runs, including sandbox or test mode.

- MOCKED · 1 pay: event evt_test_1 → order ord_test_1 paid, fee 95 of 1900 minor units, download token issued
- MOCKED · 1b deliver: download with token allowed=True
- MOCKED · 2 duplicate pay: same event replayed → duplicate=True, entitlements=1 (no double delivery)
- MOCKED · 3 refund: refunded 1900 minor units; future access revoked; an already downloaded copy cannot be revoked
- MOCKED · 4 duplicate refund: refused: already refunded
- MOCKED · 5 revoked download: allowed=False (revoked after refund)
- MOCKED · 6a reconcile: gross 1900 − fees 95 − refunds 1900 = net -95; matched=True; payout SIMULATED · no transfer initiated
- MOCKED · 6b 1-cent mismatch vs mock processor statement: matched=False; flagged: net_minor: ledger -95 vs statement -94 (diff 1)

Result: all 6 cases behaved as expected (MOCKED).
