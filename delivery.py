"""MOCKED delivery: a local download token bound to one order, with expiry
(MOCK_TOKEN_EXPIRY_HOURS). Product files are re-hashed against the release manifest before the
first grant. A refund revokes FUTURE access only; a copy already downloaded cannot be revoked."""
import hashlib
import secrets
from datetime import datetime, timedelta, timezone

import config
import log as logmod


def _now(now=None):
    return now or datetime.now(timezone.utc)


def grant(con, order_id, product_sha256, now=None):
    """Called inside the payment transaction."""
    token = "mocktok_" + secrets.token_hex(8)
    exp = (_now(now) + timedelta(hours=config.mock_token_expiry_hours())).strftime("%Y-%m-%dT%H:%M:%SZ")
    con.execute("INSERT INTO entitlements(token, order_id, product_sha256, expires_at) VALUES (?,?,?,?)",
                (token, order_id, product_sha256, exp))
    return token


def verify_product(files_bytes, expected_sha256):
    """files_bytes: list of bytes in manifest order. Returns True when the package hash matches."""
    h = hashlib.sha256()
    for b in files_bytes:
        h.update(hashlib.sha256(b).digest())
    return h.hexdigest() == expected_sha256


def package_hash(files_bytes):
    h = hashlib.sha256()
    for b in files_bytes:
        h.update(hashlib.sha256(b).digest())
    return h.hexdigest()


def download(con, token, run_id=None, now=None):
    r = con.execute("SELECT order_id, expires_at, revoked_at FROM entitlements WHERE token=?", (token,)).fetchone()
    if not r:
        res = {"allowed": False, "reason": "unknown token"}
    elif r[2]:
        res = {"allowed": False, "reason": "revoked after refund", "order_id": r[0]}
    elif _now(now).strftime("%Y-%m-%dT%H:%M:%SZ") > r[1]:
        res = {"allowed": False, "reason": "token expired", "order_id": r[0]}
    else:
        # Conditional update: a refund that revokes the token between the read and this write wins.
        ts = _now(now).strftime("%Y-%m-%dT%H:%M:%SZ")
        cur = con.execute("UPDATE entitlements SET downloads = downloads + 1 WHERE token=? AND revoked_at IS NULL AND expires_at >= ?",
                          (token, ts))
        res = {"allowed": True, "order_id": r[0]} if cur.rowcount == 1 else \
            {"allowed": False, "reason": "revoked or expired during download", "order_id": r[0]}
    logmod.log("delivery", "mock_download", run_id=run_id, mock="MOCKED", allowed=res["allowed"], reason=res.get("reason"))
    return res
