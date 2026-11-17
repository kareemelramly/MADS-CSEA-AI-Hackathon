"""Decision log (SRS LOG-1 to LOG-4).

The SQLite table `action_log` in STATE_DIR is canonical. After every append, `decision_log.json`
(DECISION_LOG_PATH) is re-exported atomically (temp file + replace) with the entries written to that
path, so a crash never leaves a half-written JSON file. Every entry has the five required keys
(`action`, `sources`, `model`, `cost`, `approved_by`) plus `timestamp`, `agent` and `run_id`.
"""
import json
import os
import re
import sqlite3
import tempfile
import threading
from datetime import datetime, timezone

import config

REQUIRED_KEYS = ("timestamp", "agent", "action", "sources", "model", "cost", "approved_by", "run_id")
_SECRET = re.compile(r"(gsk_[A-Za-z0-9]{6,}|nvapi-[A-Za-z0-9_\-]{6,}|Bearer\s+[A-Za-z0-9._\-]{8,})")
_lock = threading.Lock()


def _db():
    path = os.path.join(config.state_dir(), "actions.sqlite")
    con = sqlite3.connect(path, timeout=10)
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("""CREATE TABLE IF NOT EXISTS action_log(
        seq INTEGER PRIMARY KEY AUTOINCREMENT, log_path TEXT NOT NULL, run_id TEXT, entry TEXT NOT NULL)""")
    return con


def scrub(value):
    """Remove anything that looks like an API key or auth header (LOG-4, SEC-2)."""
    if isinstance(value, str):
        return _SECRET.sub("[REDACTED]", value)
    if isinstance(value, list):
        return [scrub(v) for v in value]
    if isinstance(value, dict):
        return {k: scrub(v) for k, v in value.items()}
    return value


def now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def log(agent, action, sources=None, model=None, cost=0, approved_by=None, run_id=None, **extra):
    sources = [s for s in (sources or []) if isinstance(s, str) and s.startswith("http")]
    if approved_by not in (None, "founder"):
        raise ValueError("approved_by must be 'founder' or None")
    entry = {
        "timestamp": now_iso(),
        "agent": agent,
        "action": action,
        "sources": sources,
        "model": model,
        "cost": float(cost) if cost else 0,
        "approved_by": approved_by,
        "run_id": run_id,
    }
    for k, v in extra.items():
        if v is not None and k not in entry:
            entry[k] = v
    entry = scrub(entry)
    path = config.decision_log_path()
    with _lock:
        con = _db()
        try:
            with con:
                con.execute("INSERT INTO action_log(log_path, run_id, entry) VALUES (?,?,?)",
                            (os.path.abspath(path), run_id, json.dumps(entry, sort_keys=False)))
        finally:
            con.close()
        export(path)
    return entry


def entries(path=None, run_id=None):
    path = os.path.abspath(path or config.decision_log_path())
    con = _db()
    try:
        q = "SELECT entry FROM action_log WHERE log_path=?"
        args = [path]
        if run_id:
            q += " AND run_id=?"
            args.append(run_id)
        rows = con.execute(q + " ORDER BY seq", args).fetchall()
    finally:
        con.close()
    return [json.loads(r[0]) for r in rows]


def export(path=None):
    """Atomically rewrite the JSON log from the canonical table."""
    path = path or config.decision_log_path()
    data = entries(path)
    d = os.path.dirname(os.path.abspath(path)) or "."
    os.makedirs(d, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=d, prefix=".decision_log.", suffix=".tmp")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=1, ensure_ascii=False)
        f.write("\n")
    os.replace(tmp, path)


def reset(path=None):
    """Start a fresh committed log (used only by scripts/demo_runs.sh before the demo runs)."""
    path = os.path.abspath(path or config.decision_log_path())
    con = _db()
    try:
        with con:
            con.execute("DELETE FROM action_log WHERE log_path=?", (path,))
    finally:
        con.close()
    export(path)
