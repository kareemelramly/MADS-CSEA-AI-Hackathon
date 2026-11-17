"""MOCKED sale-to-cash test run (SRS LCH-7). No payment of any kind runs: every event is local.

Writes outputs/payment_test_log.md (or --output) covering pay, duplicate pay, refund, duplicate
refund, revoked download and a 1-cent reconciliation mismatch. Every line is labelled MOCKED.
"""
import argparse
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config  # noqa: E402
import delivery  # noqa: E402
import payments  # noqa: E402
import reconcile  # noqa: E402
import refunds  # noqa: E402
import log as logmod  # noqa: E402


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", default=os.path.join(config.outputs_dir(), "payment_test_log.md"))
    a = ap.parse_args(argv)
    run_id = "payment-test-" + logmod.now_iso().replace(":", "").replace("-", "")
    db = os.path.join(tempfile.mkdtemp(prefix="mockledger-"), "ledger.sqlite")
    con = payments.connect(db)
    files = [b"# Checklist\n- [ ] item\n", b"journey_step,item\nJ1,item\n"]
    pkg = delivery.package_hash(files)
    ev = {"event_id": "evt_test_1", "order_id": "ord_test_1", "product_id": "a1-pack", "amount_minor": 1900, "currency": "USD"}
    L = [f"# Payment and delivery test log (MOCKED)", "",
         f"MOCKED · run {run_id} · {logmod.now_iso()} · local SQLite ledger, no payment SDK, no network, no card fields. "
         "No payment of any kind runs, including sandbox or test mode.", ""]
    r1 = payments.handle_mock_payment(con, ev, pkg, run_id=run_id)
    L.append(f"- MOCKED · 1 pay: event {ev['event_id']} → order {r1['order_id']} {r1['status']}, fee {r1['fee_minor']} of {ev['amount_minor']} minor units, download token issued")
    d = delivery.download(con, r1["token"], run_id=run_id)
    L.append(f"- MOCKED · 1b deliver: download with token allowed={d['allowed']}")
    r2 = payments.handle_mock_payment(con, ev, pkg, run_id=run_id)
    n = con.execute("SELECT COUNT(*) FROM entitlements").fetchone()[0]
    L.append(f"- MOCKED · 2 duplicate pay: same event replayed → duplicate={r2.get('duplicate')}, entitlements={n} (no double delivery)")
    rf = refunds.handle_mock_refund(con, {"event_id": "evt_test_rf1", "order_id": ev["order_id"]}, run_id=run_id)
    L.append(f"- MOCKED · 3 refund: {rf['status']} {rf.get('amount_minor')} minor units; {rf.get('note')}")
    rf2 = refunds.handle_mock_refund(con, {"event_id": "evt_test_rf2", "order_id": ev["order_id"]}, run_id=run_id)
    L.append(f"- MOCKED · 4 duplicate refund: {rf2['status']}")
    d2 = delivery.download(con, r1["token"], run_id=run_id)
    L.append(f"- MOCKED · 5 revoked download: allowed={d2['allowed']} ({d2.get('reason')})")
    ok = reconcile.reconcile(con, run_id=run_id)
    L.append(f"- MOCKED · 6a reconcile: gross {ok['gross_minor']} − fees {ok['fees_minor']} − refunds {ok['refunds_minor']} = net {ok['net_minor']}; matched={ok['matched']}; payout {ok['payout_status']}")
    bad = reconcile.reconcile(con, statement={"net_minor": ok["net_minor"] + 1}, run_id=run_id)
    L.append(f"- MOCKED · 6b 1-cent mismatch vs mock processor statement: matched={bad['matched']}; flagged: {'; '.join(bad['issues'])}")
    passed = d["allowed"] and r2.get("duplicate") and n == 1 and rf["status"] == "refunded" and "refused" in rf2["status"] \
        and not d2["allowed"] and ok["matched"] and not bad["matched"]
    L += ["", f"Result: {'all 6 cases behaved as expected' if passed else 'UNEXPECTED RESULT: see lines above'} (MOCKED)."]
    con.close()
    os.makedirs(os.path.dirname(os.path.abspath(a.output)), exist_ok=True)
    with open(a.output, "w", encoding="utf-8") as f:
        f.write("\n".join(L) + "\n")
    print("\n".join(L))
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
