"""Verify committed outputs and the decision log (SRS TEST-7, LOG-5, REPO-6).

    python scripts/check_outputs.py --all          # everything in outputs/ and decision_log.json
    python scripts/check_outputs.py --label t3     # one label only
Exit code 0 = all checks pass.
"""
import argparse
import hashlib
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NAME = re.compile(r"^phase[1-6]_(step\d+|gate)_[a-z0-9_]+-(?P<label>[a-z0-9]+)-a\d+\.(md|json|csv|txt|html)$")
KEYS = ("timestamp", "agent", "action", "sources", "model", "cost", "approved_by", "run_id")
SECRET = re.compile(r"gsk_[A-Za-z0-9]{6,}|nvapi-[A-Za-z0-9_\-]{6,}")


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--label")
    ap.add_argument("--outputs", default=os.environ.get("OUTPUTS_DIR", os.path.join(ROOT, "outputs")))
    ap.add_argument("--log", default=os.environ.get("DECISION_LOG_PATH", os.path.join(ROOT, "decision_log.json")))
    a = ap.parse_args(argv)
    problems, labels = [], {}
    files = sorted(f for f in os.listdir(a.outputs) if not f.startswith("."))
    for f in files:
        if f in ("payment_test_log.md", "README.md"):
            continue
        m = NAME.match(f)
        if not m:
            problems.append(f"bad name: {f}")
            continue
        if a.label and m.group("label") != a.label:
            continue
        labels.setdefault(m.group("label"), []).append(f)
    try:
        log = json.load(open(a.log, encoding="utf-8"))
    except (OSError, ValueError) as e:
        log = []
        problems.append(f"decision log unreadable: {e}")
    if not isinstance(log, list):
        problems.append("decision log is not a JSON list")
        log = []
    for i, e in enumerate(log):
        miss = [k for k in KEYS if k not in e]
        if miss:
            problems.append(f"log entry {i} missing {miss}")
        if e.get("approved_by") not in (None, "founder"):
            problems.append(f"log entry {i} approved_by invalid")
        if not isinstance(e.get("sources", []), list):
            problems.append(f"log entry {i} sources not a list")
    raw = open(a.log, encoding="utf-8").read() if os.path.exists(a.log) else ""
    if SECRET.search(raw):
        problems.append("API key string found in decision log")
    # Hashes match the write_output entries (no file edited after the run).
    written = {os.path.basename(e["path"]): e["sha256"] for e in log if e.get("action") == "write_output" and e.get("path")}
    for lab, fs in labels.items():
        for f in fs:
            body = open(os.path.join(a.outputs, f), "rb").read()
            if SECRET.search(body.decode("utf-8", "replace")):
                problems.append(f"API key string in {f}")
            if f in written and hashlib.sha256(body).hexdigest() != written[f]:
                problems.append(f"{f} changed after the run (hash differs from the log)")
            if written and f not in written:
                problems.append(f"{f} has no write_output log entry")
            if f.endswith(".md") and ("[S0" in body.decode("utf-8")):
                for sid_line in re.findall(r"\[S\d{3}\]\(([^)]*)\)", body.decode("utf-8")):
                    if not sid_line.startswith("http"):
                        problems.append(f"{f}: source ID without URL")
    stops = 0
    for lab, fs in labels.items():
        for f in fs:
            if "_gate_" in f and f.endswith(".json"):
                g = json.load(open(os.path.join(a.outputs, f), encoding="utf-8")).get("gate", {})
                stops += g.get("outcome") == "stop"
    if a.all:
        if not stops:
            problems.append("no stop verdict in outputs/")
        pt = os.path.join(a.outputs, "payment_test_log.md")
        if not os.path.exists(pt):
            problems.append("payment_test_log.md missing")
        else:
            bad = [l for l in open(pt, encoding="utf-8").read().splitlines() if l.strip() and "MOCKED" not in l]
            if bad:
                problems.append(f"payment_test_log.md lines without MOCKED: {len(bad)}")
    print(f"labels: { {k: len(v) for k, v in labels.items()} } · stop verdicts: {stops} · log entries: {len(log)}")
    for p in problems:
        print("FAIL:", p)
    print("OK" if not problems else f"{len(problems)} problem(s)")
    return 0 if not problems else 1


if __name__ == "__main__":
    sys.exit(main())
