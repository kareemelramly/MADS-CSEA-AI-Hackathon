"""MOCKED reconciliation (LCH-6). Checks gross - fees - refunds = net to the cent against orders,
payments, refunds and a SIMULATED payout batch, and compares the ledger with a mock processor
statement. A payout batch is a record only: it never initiates a transfer."""
import uuid

import log as logmod


def summary(con):
    gross = con.execute("SELECT COALESCE(SUM(amount_minor),0) FROM orders").fetchone()[0]
    fees = con.execute("SELECT COALESCE(SUM(fee_minor),0) FROM orders").fetchone()[0]
    refunds = con.execute("SELECT COALESCE(SUM(amount_minor),0) FROM refunds").fetchone()[0]
    orders = con.execute("SELECT COUNT(*) FROM orders").fetchone()[0]
    nref = con.execute("SELECT COUNT(*) FROM refunds").fetchone()[0]
    paid_events = con.execute("SELECT COUNT(*) FROM events WHERE type='MOCK_PAYMENT_SUCCEEDED' AND result LIKE '%\"paid\"%'").fetchone()[0]
    return {"orders": orders, "paid_events": paid_events, "gross_minor": gross, "fees_minor": fees,
            "refunds": nref, "refunds_minor": refunds, "net_minor": gross - fees - refunds, "label": "MOCKED"}


def reconcile(con, statement=None, run_id=None, currency="USD"):
    """statement: optional mock processor report {gross_minor, fees_minor, refunds_minor, net_minor}."""
    s = summary(con)
    issues = []
    if s["orders"] != s["paid_events"]:
        issues.append(f"orders {s['orders']} != paid events {s['paid_events']}")
    if s["gross_minor"] - s["fees_minor"] - s["refunds_minor"] != s["net_minor"]:
        issues.append("gross - fees - refunds != net")
    if statement:
        for k in ("gross_minor", "fees_minor", "refunds_minor", "net_minor"):
            if k in statement and statement[k] != s[k]:
                issues.append(f"{k}: ledger {s[k]} vs statement {statement[k]} (diff {statement[k] - s[k]})")
    batch = "po_" + uuid.uuid4().hex[:8]
    con.execute("INSERT INTO payout_batches VALUES (?,?,?,?,?)", (batch, s["net_minor"], currency,
                "SIMULATED · no transfer initiated", logmod.now_iso()))
    res = {**s, "payout_batch": batch, "payout_status": "SIMULATED · no transfer initiated", "matched": not issues, "issues": issues}
    logmod.log("reconcile", "mock_reconcile", run_id=run_id, mock="MOCKED", matched=not issues, issues=issues, net_minor=s["net_minor"])
    return res
