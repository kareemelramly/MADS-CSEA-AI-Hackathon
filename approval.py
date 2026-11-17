"""Founder approval enforced at the executor (SRS 4.9, ADR-02).

An approval binds {action, content_sha256, destination, amount_minor, currency, run_id}. It is
granted only by an explicit founder action (UI button or typed CLI answer), never by default or
timeout. `execute()` is the only path to an effect: it recomputes the binding, requires status
`approved` and not consumed, marks it consumed in the same transaction, then runs `do()`.
Effects in this project are all STUBBED (log `would_publish` / `would_send`) or internal.
Prohibited actions can never be queued, so they can never be approved.
"""
import hashlib
import json
import os
import sqlite3
import uuid

import config
import log as logmod

PROHIBITED = {"charge", "charge_card", "payment", "take_payment", "refund_money", "transfer", "payout",
              "create_account", "store_credentials", "store_password", "store_card", "sandbox_payment"}
ALLOWED = {"publish_landing_page", "release_product", "commercial_setup", "publish_store_page",
           "post_launch_message", "send_support_reply"}
RISK = {a: "high" for a in ALLOWED}  # APR-10: every external-effect action is high risk


class ApprovalError(Exception):
    pass


def _db():
    path = os.path.join(config.state_dir(), "approvals.sqlite")
    con = sqlite3.connect(path, timeout=10, isolation_level=None)
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("""CREATE TABLE IF NOT EXISTS approvals(
        id TEXT PRIMARY KEY, run_id TEXT, action TEXT, destination TEXT, amount_minor INTEGER, currency TEXT,
        content_sha256 TEXT, binding_key TEXT, field_hashes TEXT, content_preview TEXT, status TEXT,
        requested_at TEXT, decided_at TEXT, consumed_at TEXT, approved_by TEXT)""")
    return con


def _h(v):
    return hashlib.sha256(str(v).encode()).hexdigest()


def binding(action, content, destination, amount_minor, currency, run_id):
    b = {"action": action, "content_sha256": hashlib.sha256(content.encode()).hexdigest(),
         "destination": destination, "amount_minor": int(amount_minor), "currency": currency, "run_id": run_id}
    key = hashlib.sha256(json.dumps(b, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return b, key


def request(action, content, destination, amount_minor, currency, run_id, agent="orchestrator"):
    if action in PROHIBITED or action not in ALLOWED:
        logmod.log(agent, "approval_refused_prohibited", run_id=run_id, requested_action=action)
        raise ApprovalError(f"'{action}' is prohibited or unknown and can never be approved")
    if int(amount_minor) != 0:
        logmod.log(agent, "approval_refused_amount", run_id=run_id, requested_action=action, amount_minor=int(amount_minor))
        raise ApprovalError("only amount 0 can be approved: no money is ever spent or moved (BR-5)")
    b, key = binding(action, content, destination, amount_minor, currency, run_id)
    fields = {k: _h(v) for k, v in b.items()}
    aid = "apr_" + uuid.uuid4().hex[:12]
    con = _db()
    try:
        con.execute("INSERT INTO approvals VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (aid, run_id, action, destination, int(amount_minor), currency, b["content_sha256"], key,
                     json.dumps(fields), content[:4000], "pending", logmod.now_iso(), None, None, None))
    finally:
        con.close()
    logmod.log(agent, "approval_requested", run_id=run_id, approval_id=aid, requested_action=action,
               destination=destination, amount_minor=int(amount_minor), currency=currency,
               content_sha256=b["content_sha256"], risk=RISK[action])
    return aid


def get(aid):
    con = _db()
    try:
        con.row_factory = sqlite3.Row
        r = con.execute("SELECT * FROM approvals WHERE id=?", (aid,)).fetchone()
        return dict(r) if r else None
    finally:
        con.close()


def pending(run_id=None):
    con = _db()
    try:
        con.row_factory = sqlite3.Row
        q = "SELECT * FROM approvals WHERE status='pending'" + (" AND run_id=?" if run_id else "")
        return [dict(r) for r in con.execute(q, (run_id,) if run_id else ())]
    finally:
        con.close()


def approve(aid, *, founder_action):
    """Called only from the UI button handler or the CLI prompt. `founder_action` must be the
    literal string 'button' or 'typed', so no code path can approve by default."""
    if founder_action not in ("button", "typed"):
        raise ApprovalError("approval requires an explicit founder action")
    return _decide(aid, "approved")


def reject(aid, *, founder_action):
    if founder_action not in ("button", "typed"):
        raise ApprovalError("rejection requires an explicit founder action")
    return _decide(aid, "rejected")


def _decide(aid, status):
    con = _db()
    try:
        con.execute("BEGIN IMMEDIATE")
        r = con.execute("SELECT status, run_id, action FROM approvals WHERE id=?", (aid,)).fetchone()
        if not r or r[0] != "pending":
            con.execute("ROLLBACK")
            raise ApprovalError(f"approval {aid} is not pending")
        con.execute("UPDATE approvals SET status=?, decided_at=?, approved_by=? WHERE id=?",
                    (status, logmod.now_iso(), "founder", aid))
        con.execute("COMMIT")
    finally:
        con.close()
    logmod.log("founder", f"approval_{status}", run_id=r[1], approved_by="founder" if status == "approved" else None,
               approval_id=aid, requested_action=r[2])
    return status


def execute(aid, action, content, destination, amount_minor, currency, run_id, do):
    """The only path to an effect. Returns do()'s result. Raises ApprovalError on any mismatch."""
    b, key = binding(action, content, destination, amount_minor, currency, run_id)
    con = _db()
    try:
        con.execute("BEGIN IMMEDIATE")
        r = con.execute("SELECT status, binding_key, field_hashes FROM approvals WHERE id=?", (aid,)).fetchone()
        if not r:
            con.execute("ROLLBACK")
            logmod.log("executor", "execute_refused", run_id=run_id, reason="no approval", requested_action=action)
            raise ApprovalError("no such approval")
        status, stored_key, fields = r
        if status != "approved":
            con.execute("ROLLBACK")
            reason = "already consumed" if status == "consumed" else f"status {status}"
            logmod.log("executor", "execute_refused", run_id=run_id, reason=reason, approval_id=aid)
            raise ApprovalError(f"approval {aid}: {reason}")
        if stored_key != key:
            stored = json.loads(fields)
            changed = [k for k, v in b.items() if _h(v) != stored.get(k)]
            con.execute("UPDATE approvals SET status='void' WHERE id=?", (aid,))
            con.execute("COMMIT")
            logmod.log("executor", "approval_mismatch", run_id=run_id, approval_id=aid, changed_fields=changed)
            raise ApprovalError(f"approval_mismatch: changed {', '.join(changed)}; a new approval is needed")
        con.execute("UPDATE approvals SET status='consumed', consumed_at=? WHERE id=?", (logmod.now_iso(), aid))
        result = do()
        con.execute("COMMIT")
    except ApprovalError:
        raise
    except Exception:
        try:
            con.execute("ROLLBACK")
        except sqlite3.Error:
            pass
        raise
    finally:
        con.close()
    logmod.log("executor", "execute", run_id=run_id, approved_by="founder", approval_id=aid,
               executed_action=action, destination=destination)
    return result


# ------------------------------------------------------------------ STUBBED effects
def publish_stub(run_id, action, destination, sha):
    logmod.log("executor", "would_publish", run_id=run_id, approved_by="founder", stub="STUBBED",
               executed_action=action, destination=destination, content_sha256=sha)
    return {"status": "STUBBED · NOT PUBLISHED", "destination": destination}


def send_stub(run_id, recipient, sha):
    logmod.log("executor", "would_send", run_id=run_id, approved_by="founder", stub="STUBBED",
               recipient=recipient, content_sha256=sha)
    return {"status": "STUBBED · NOT SENT"}


# ------------------------------------------------------------------ override
NON_OVERRIDABLE = {"exclusion", "guardrail", "phase3_test_gate", "approval", "payment_ban", "target_tampered", "qa"}


def override(ctx, phase, outcome, reason, kind="evidence"):
    """Founder override of an evidence gate (APR-8). Never for exclusions, guardrails, the Phase 3
    test gate, approvals or the payment ban."""
    if kind in NON_OVERRIDABLE:
        ctx.log("founder", "override_refused", phase=phase, kind=kind)
        raise ApprovalError(f"{kind} cannot be overridden")
    if outcome not in ("awaiting_evidence", "repeat", "pivot_back", "stop"):
        raise ApprovalError("only a non-go evidence outcome can be overridden")
    if not reason or len(reason.strip()) < 20:
        raise ApprovalError("override needs a typed reason of at least 20 characters")
    ctx.overrides.append({"phase": phase, "original_outcome": outcome, "reason": reason.strip(), "at": logmod.now_iso()})
    ctx.validation_status = "UNVALIDATED_FOUNDER_OVERRIDE" if phase == 2 else ctx.validation_status
    ctx.log("founder", "override", approved_by="founder", phase=phase, original_outcome=outcome, reason=reason.strip())
    return ctx.overrides[-1]
