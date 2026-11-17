"""Phase 5 MOCKED ledger (SRS LCH-2 to LCH-7, SAFE-4, SEC-5)."""
import ast
import os
from datetime import datetime, timedelta, timezone

import pytest

import delivery
import payments
import reconcile
import refunds

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EV = {"event_id": "evt_1", "order_id": "ord_1", "product_id": "pack", "amount_minor": 1900, "currency": "USD"}


@pytest.fixture
def con(env):
    c = payments.connect(str(env / "ledger.sqlite"))
    yield c
    c.close()


def test_payment_creates_one_entitlement_and_duplicate_is_ignored(con):
    r1 = payments.handle_mock_payment(con, EV, "sha")
    r2 = payments.handle_mock_payment(con, EV, "sha")
    assert r2["duplicate"] and r2["token"] == r1["token"]
    assert con.execute("SELECT COUNT(*) FROM entitlements").fetchone()[0] == 1


def test_duplicate_order_new_event_no_second_entitlement(con):
    payments.handle_mock_payment(con, EV, "sha")
    r = payments.handle_mock_payment(con, {**EV, "event_id": "evt_2"}, "sha")
    assert r["status"] == "duplicate_order_ignored"
    assert con.execute("SELECT COUNT(*) FROM entitlements").fetchone()[0] == 1


def test_refund_revokes_and_second_refund_refused(con):
    r = payments.handle_mock_payment(con, EV, "sha")
    assert delivery.download(con, r["token"])["allowed"]
    assert refunds.handle_mock_refund(con, {"event_id": "rf1", "order_id": "ord_1"})["status"] == "refunded"
    d = delivery.download(con, r["token"])
    assert not d["allowed"] and "revoked" in d["reason"]
    assert "refused" in refunds.handle_mock_refund(con, {"event_id": "rf2", "order_id": "ord_1"})["status"]


def test_orphan_refund_quarantined(con):
    assert refunds.handle_mock_refund(con, {"event_id": "rfx", "order_id": "nope"})["status"] == "quarantined"


def test_token_expires(con):
    r = payments.handle_mock_payment(con, EV, "sha")
    later = datetime.now(timezone.utc) + timedelta(hours=48)
    assert not delivery.download(con, r["token"], now=later)["allowed"]


def test_reconcile_matches_and_flags_one_cent(con):
    payments.handle_mock_payment(con, EV, "sha")
    ok = reconcile.reconcile(con)
    assert ok["matched"] and ok["net_minor"] == 1900 - 95
    bad = reconcile.reconcile(con, statement={"net_minor": ok["net_minor"] + 1})
    assert not bad["matched"] and "diff 1" in bad["issues"][0]
    assert "no transfer" in bad["payout_status"]


def test_card_fields_rejected(con):
    with pytest.raises(ValueError):
        payments.handle_mock_payment(con, {**EV, "card_number": "x"}, "sha")


def test_ledger_modules_make_no_network_calls():
    for f in ("payments.py", "delivery.py", "refunds.py", "reconcile.py", "approval.py"):
        tree = ast.parse(open(os.path.join(ROOT, f)).read())
        mods = {a.name.split(".")[0] for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names}
        mods |= {n.module.split(".")[0] for n in ast.walk(tree) if isinstance(n, ast.ImportFrom) and n.module}
        assert not (mods & {"urllib", "requests", "http", "socket", "httpx", "llm", "sources", "stripe"}), (f, mods)


def test_payment_test_run_script_all_mocked(env):
    import subprocess
    import sys
    out = env / "pt.md"
    r = subprocess.run([sys.executable, os.path.join(ROOT, "scripts", "payment_test_run.py"), "--output", str(out)],
                       capture_output=True, text=True, env={**os.environ})
    assert r.returncode == 0, r.stderr
    lines = [l for l in open(out, encoding="utf-8").read().splitlines() if l.startswith("- ")]
    assert len(lines) >= 6 and all("MOCKED" in l for l in lines)


def test_tampered_product_file_is_not_delivered(env):
    import hashlib
    import delivery
    files = [b"checklist", b"tracker"]
    released = hashlib.sha256(b"".join(hashlib.sha256(b).digest() for b in files)).hexdigest()
    assert delivery.verify_product(files, released)
    assert not delivery.verify_product([b"checklist EDITED", b"tracker"], released)
