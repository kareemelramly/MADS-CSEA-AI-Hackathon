"""Analyst (Phase 6, no model call). Metrics table by code, every value labelled real, MOCKED or
SIMULATED; recommendation from `gates.operate_gate` on real values only; memo filled from a
Jinja2 template (OPS-1 to OPS-5). Mock or simulated data never gives "persevere"."""
import os

from jinja2 import Environment, FileSystemLoader, select_autoescape

from agents import ROOT

ENV = Environment(loader=FileSystemLoader(os.path.join(ROOT, "templates")), autoescape=select_autoescape(["j2"]),
                  keep_trailing_newline=True)


def metrics(ctx, ledger_summary, real_entries):
    h2 = ctx.handoffs.get("H2", {})
    rows = []
    if h2.get("experiment_status") == "completed":
        rows.append({"name": "waitlist_signups", "value": h2.get("signups"), "label": "real", "evidence": "Phase 2 completed experiment (founder-entered)"})
    else:
        rows.append({"name": "waitlist_signups", "value": None, "label": "real", "evidence": f"no completed experiment (status {h2.get('experiment_status')})"})
    for k in ("orders", "gross_minor", "refunds", "net_minor"):
        if k in ledger_summary:
            rows.append({"name": f"mock_{k}", "value": ledger_summary[k], "label": "MOCKED", "evidence": "local mock ledger"})
    for e in real_entries or []:
        rows.append({"name": e["name"], "value": e.get("value"), "label": "real" if e.get("evidence") else "SIMULATED",
                     "evidence": e.get("evidence") or "no evidence link: treated as SIMULATED"})
    return rows


def memo(ctx, rows, gate, targets, decision=None):
    ctx.log("analyst", "write_operate_memo", outcome=gate.outcome,
            real_metrics=sum(1 for r in rows if r["label"] == "real" and r["value"] is not None))
    return ENV.get_template("memo.md.j2").render(
        run_id=ctx.run_id, overrides=ctx.overrides, rows=rows, gate=gate, targets=targets,
        validation_status=ctx.validation_status, decision=decision,
        awaiting=ctx.handoffs.get("H2", {}).get("experiment_status") != "completed")
