"""Rebuild final run reports from decision_log.json (no model call, nothing typed by hand).

    python scripts/run_report.py --all          every finished run in decision_log.json
    python scripts/run_report.py <run_id>       one run

Runs that already wrote their report when they ended keep it; a run without one (for example a log
from an older version) gets outputs/phase<N>_step9_run_report_<label>_a1.md and .html. PDFs are
always rebuilt into state/reports/<run_id>.pdf (not committed: outputs/ holds text files only).
"""
import hashlib
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import log as logmod  # noqa: E402
import report  # noqa: E402


def main(argv):
    entries = json.load(open(os.path.join(ROOT, "decision_log.json"), encoding="utf-8"))
    ended = [e["run_id"] for e in entries if e["action"] == "end_run" and e.get("run_id")]
    added = []
    want = ended if (not argv or argv[0] == "--all") else argv
    for rid in want:
        s = report.summarize(entries, rid, ROOT)
        has = any("_run_report_" in f for f in s["files"])
        if not has:
            n = max(1, s["max_phase"])
            for ext, body in (("md", report.to_markdown(s)), ("html", report.to_html(s))):
                rel = f"outputs/phase{n}_step9_run_report_{s['label']}_a1.{ext}"
                path = os.path.join(ROOT, rel)
                with open(path, "w", encoding="utf-8") as f:
                    f.write(body)
                added.append({"timestamp": logmod.now_iso(), "agent": "orchestrator", "action": "write_output", "sources": [],
                              "model": None, "cost": 0, "approved_by": None, "run_id": rid, "path": rel,
                              "sha256": hashlib.sha256(body.encode("utf-8")).hexdigest(),
                              "generated_by": "scripts/run_report.py"})
        pdf = report.to_pdf(s, report.pdf_path(rid))
        print(f"{rid}: phase {s['max_phase']} of 6, outcome {s['outcome']}, report {'kept' if has else 'written'}"
              + (f", PDF {os.path.relpath(pdf, ROOT)}" if pdf else ", PDF skipped (pip install reportlab)"))
    if added:      # append to the JSON log directly; never rebuild it from another store
        path = os.path.join(ROOT, "decision_log.json")
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(entries + added, f, indent=1, ensure_ascii=False)
            f.write("\n")
        os.replace(tmp, path)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
