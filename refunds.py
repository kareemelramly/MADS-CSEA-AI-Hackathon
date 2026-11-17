"""MOCKED refunds. The system never refunds real money (SAFE-4); a MOCK_REFUND event records the
refund in the local ledger and revokes future access to the download token. A second refund of
the same order is refused; a refund for an unknown order is quarantined (LCH-5)."""
import json

import log as logmod


def handle_mock_refund(con, event, run_id=None):
    """event: {event_id, order_id}"""
    con.execute("BEGIN IMMEDIATE")
    try:
        if con.execute("SELECT 1 FROM events WHERE event_id=?", (event["event_id"],)).fetchone():
            con.execute("ROLLBACK")
            return {"status": "duplicate_event_ignored", "label": "MOCKED"}
        o = con.execute("SELECT amount_minor, status FROM orders WHERE order_id=?", (event["order_id"],)).fetchone()
        if not o:
            con.execute("INSERT INTO quarantine VALUES (?,?,?,?)", (event["event_id"], "orphan refund: unknown order",
                        json.dumps(event), logmod.now_iso()))
            con.execute("COMMIT")
            logmod.log("refunds", "mock_refund_quarantined", run_id=run_id, mock="MOCKED", order_id=event["order_id"])
            return {"status": "quarantined", "label": "MOCKED"}
        if con.execute("SELECT 1 FROM refunds WHERE order_id=?", (event["order_id"],)).fetchone():
            con.execute("ROLLBACK")
            logmod.log("refunds", "mock_refund_refused_duplicate", run_id=run_id, mock="MOCKED", order_id=event["order_id"])
            return {"status": "refused: already refunded", "label": "MOCKED"}
        con.execute("INSERT INTO refunds VALUES (?,?,?,?)", ("rf_" + event["event_id"], event["order_id"], o[0], logmod.now_iso()))
        con.execute("UPDATE orders SET status='refunded' WHERE order_id=?", (event["order_id"],))
        con.execute("UPDATE entitlements SET revoked_at=? WHERE order_id=?", (logmod.now_iso(), event["order_id"]))
        res = {"status": "refunded", "order_id": event["order_id"], "amount_minor": o[0], "label": "MOCKED",
               "note": "future access revoked; an already downloaded copy cannot be revoked"}
        con.execute("INSERT INTO events VALUES (?,?,?,?,?,?)", (event["event_id"], "MOCK_REFUND", event["order_id"],
                    json.dumps(event), json.dumps(res), logmod.now_iso()))
        con.execute("COMMIT")
    except Exception:
        con.execute("ROLLBACK")
        raise
    logmod.log("refunds", "mock_refund_recorded", run_id=run_id, mock="MOCKED", order_id=event["order_id"], amount_minor=o[0])
    return res
