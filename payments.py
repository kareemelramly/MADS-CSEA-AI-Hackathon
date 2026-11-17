"""MOCKED payment events (Phase 5, Core step: deliver automatically). SRS LCH-2 to LCH-4.

No payment SDK, no network, no card fields, no sandbox: a "payment" here is a local event
`MOCK_PAYMENT_SUCCEEDED` written by the founder's "Simulate purchase (MOCKED)" button or by
scripts/payment_test_run.py. Integer minor units; unique event_id and order_id; one SQLite
transaction per event; a duplicate event returns the original result and grants nothing new.
"""
import json
import os
import sqlite3

import config
import log as logmod

LABEL = "MOCKED"


def connect(path=None):
    path = path or os.path.join(config.state_dir(), "ledger.sqlite")
    con = sqlite3.connect(path, timeout=10, isolation_level=None)
    con.execute("PRAGMA journal_mode=WAL")
    con.executescript("""
    CREATE TABLE IF NOT EXISTS events(event_id TEXT PRIMARY KEY, type TEXT NOT NULL, order_id TEXT, payload TEXT, result TEXT, created_at TEXT);
    CREATE TABLE IF NOT EXISTS orders(order_id TEXT PRIMARY KEY, product_id TEXT, amount_minor INTEGER NOT NULL CHECK(amount_minor >= 0),
        currency TEXT NOT NULL, fee_minor INTEGER NOT NULL, status TEXT NOT NULL, created_at TEXT);
    CREATE TABLE IF NOT EXISTS entitlements(token TEXT PRIMARY KEY, order_id TEXT UNIQUE NOT NULL, product_sha256 TEXT,
        expires_at TEXT, revoked_at TEXT, downloads INTEGER DEFAULT 0);
    CREATE TABLE IF NOT EXISTS refunds(refund_id TEXT PRIMARY KEY, order_id TEXT UNIQUE NOT NULL, amount_minor INTEGER NOT NULL, created_at TEXT);
    CREATE TABLE IF NOT EXISTS quarantine(event_id TEXT PRIMARY KEY, reason TEXT, payload TEXT, created_at TEXT);
    CREATE TABLE IF NOT EXISTS payout_batches(batch_id TEXT PRIMARY KEY, net_minor INTEGER, currency TEXT, status TEXT, created_at TEXT);
    """)
    return con


def fee_for(amount_minor):
    return int(round(amount_minor * config.mock_fee_rate()))


def handle_mock_payment(con, event, product_sha256, run_id=None, now=None):
    """event: {event_id, order_id, product_id, amount_minor, currency}. Returns the result dict."""
    import delivery
    for k in ("event_id", "order_id", "product_id", "amount_minor", "currency"):
        if k not in event:
            raise ValueError(f"missing {k}")
    if any(k in event for k in ("card", "card_number", "cvv", "password")):
        raise ValueError("card or credential fields are never accepted")
    amt = int(event["amount_minor"])
    con.execute("BEGIN IMMEDIATE")
    try:
        row = con.execute("SELECT result FROM events WHERE event_id=?", (event["event_id"],)).fetchone()
        if row:
            con.execute("ROLLBACK")
            res = json.loads(row[0])
            res["duplicate"] = True
            logmod.log("payments", "mock_payment_duplicate_ignored", run_id=run_id, mock=LABEL, event_id=event["event_id"])
            return res
        if con.execute("SELECT 1 FROM orders WHERE order_id=?", (event["order_id"],)).fetchone():
            res = {"status": "duplicate_order_ignored", "order_id": event["order_id"], "label": LABEL}
            con.execute("INSERT INTO events VALUES (?,?,?,?,?,?)", (event["event_id"], "MOCK_PAYMENT_SUCCEEDED", event["order_id"],
                        json.dumps(event), json.dumps(res), logmod.now_iso()))
            con.execute("COMMIT")
            logmod.log("payments", "mock_payment_duplicate_order", run_id=run_id, mock=LABEL, order_id=event["order_id"])
            return res
        fee = fee_for(amt)
        con.execute("INSERT INTO orders VALUES (?,?,?,?,?,?,?)", (event["order_id"], event["product_id"], amt, event["currency"],
                    fee, "paid", logmod.now_iso()))
        token = delivery.grant(con, event["order_id"], product_sha256, now=now)
        res = {"status": "paid", "order_id": event["order_id"], "token": token, "fee_minor": fee, "label": LABEL}
        con.execute("INSERT INTO events VALUES (?,?,?,?,?,?)", (event["event_id"], "MOCK_PAYMENT_SUCCEEDED", event["order_id"],
                    json.dumps(event), json.dumps(res), logmod.now_iso()))
        con.execute("COMMIT")
    except Exception:
        con.execute("ROLLBACK")
        raise
    logmod.log("payments", "mock_payment_recorded", run_id=run_id, mock=LABEL, order_id=event["order_id"], amount_minor=amt,
               currency=event["currency"], fee_minor=fee)
    return res
