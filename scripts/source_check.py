"""Live check of the evidence sources (writes nothing to outputs/ or decision_log.json).
    python scripts/source_check.py ["query"]"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import sources  # noqa: E402

q = sys.argv[1] if len(sys.argv) > 1 else "wedding planning"
t = time.time()
res = sources.search_all(q, timeout=10)
ok = 0
for k, v in res.items():
    print(f"{k:15s} status={v['status']} items={len(v['items'])} error={v['error']}{' (background only)' if v.get('background_only') else ''}")
    ok += v["status"] == 200 and not v.get("background_only")
print(f"{ok} demand sources answered in {time.time() - t:.1f} s (need at least 2)")
sys.exit(0 if ok >= 2 else 1)
