"""Cost per run from the decision log (SRS LOG-7, PERF-4, PERF-9). Reports calls, tokens, cost and
system time per run ID and per tier. Writes docs/cost_report.md and refreshes the README cost
line between the cost markers. Charges are observed from the log; electricity is not included.

    python scripts/cost_per_run.py [--run-id ID] [--no-readme]
"""
import argparse
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def summarize(log):
    runs = {}
    for e in log:
        rid = e.get("run_id")
        if not rid:
            continue
        r = runs.setdefault(rid, {"calls": 0, "tokens": 0, "prompt": 0, "completion": 0, "cost": 0.0, "tiers": {}, "system_time_s": None,
                                  "outcome": None, "label": rid.split("-")[-1]})
        if e.get("model"):
            r["calls"] += 1
            t = (e.get("prompt_tokens") or 0) + (e.get("completion_tokens") or 0)
            r["tokens"] += t
            r["prompt"] += e.get("prompt_tokens") or 0
            r["completion"] += e.get("completion_tokens") or 0
            tier = e["model"].split("/")[0] + "/" + e["model"].split("/")[1] if "/" in e["model"] else e["model"]
            tt = r["tiers"].setdefault(tier, {"calls": 0, "tokens": 0, "model": e["model"]})
            tt["calls"] += 1
            tt["tokens"] += t
        r["cost"] += float(e.get("cost") or 0)
        if e.get("action") == "end_run":
            r["system_time_s"] = e.get("system_time_s")
            r["outcome"] = e.get("outcome")
    return runs


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-id")
    ap.add_argument("--log", default=os.path.join(ROOT, "decision_log.json"))
    ap.add_argument("--no-readme", action="store_true")
    a = ap.parse_args(argv)
    log = json.load(open(a.log, encoding="utf-8"))
    runs = summarize(log)
    if a.run_id:
        runs = {k: v for k, v in runs.items() if k == a.run_id}
    lines = ["# Cost per run (generated from decision_log.json)", "",
             "Observed charges come from the log (`cost` field, USD). Local and free-tier calls are charged $0.00. "
             "Electricity and hardware are not included (ASSUMPTION).", "",
             "| Run ID | Outcome | Model calls | Tokens (prompt + completion) | Observed charge | System time (s) | Tiers |", "|---|---|---|---|---|---|---|"]
    for rid, r in runs.items():
        tiers = "; ".join(f"{k}: {v['calls']} calls, {v['tokens']} tokens" for k, v in r["tiers"].items()) or "none (no model call)"
        lines.append(f"| {rid} | {r['outcome']} | {r['calls']} | {r['tokens']} ({r['prompt']} + {r['completion']}) | ${r['cost']:.2f} | {r['system_time_s']} | {tiers} |")
    full = [r for r in runs.values() if r["label"] == "r"]
    if full:
        r = max(full, key=lambda x: x["calls"])
        lines += ["", f"Full-run measurement (from 1 complete run, label r): {r['calls']} model calls, {r['tokens']} tokens."]
    os.makedirs(os.path.join(ROOT, "docs"), exist_ok=True)
    open(os.path.join(ROOT, "docs", "cost_report.md"), "w", encoding="utf-8").write("\n".join(lines) + "\n")
    print("\n".join(lines))
    if not a.no_readme and full:
        r = max(full, key=lambda x: x["calls"])
        tiers = ", ".join(f"{v['tokens']} tokens on {v['model']}" for v in r["tiers"].values())
        sentence = (f"About ${r['cost']:.2f} per run observed (run R: {r['calls']} model calls, about {r['tokens']} tokens: {tiers}; "
                    f"system time {r['system_time_s']} s). Electricity not included (ASSUMPTION). Details: [docs/cost_report.md](docs/cost_report.md).")
        p = os.path.join(ROOT, "README.md")
        txt = open(p, encoding="utf-8").read()
        new = re.sub(r"(<!-- cost:start -->\n).*?(\n<!-- cost:end -->)", lambda m: m.group(1) + sentence + m.group(2), txt, flags=re.S)
        open(p, "w", encoding="utf-8").write(new)
    mc = os.path.join(ROOT, "model_check_result.json")
    if not a.no_readme and os.path.exists(mc):
        m = json.load(open(mc, encoding="utf-8"))
        speed = (f"measured {m.get('measured_at')} on the team laptop through llama.cpp: {m['valid']}/{m['of']} schema-valid "
                 f"(correctness {m['correctness']}), about {m['avg_tokens_per_s']} tokens/s, slowest call {m['max_seconds_per_call']} s "
                 f"(performance {m['performance']} against the 40 tokens/s and 30 s planning limits).")
        p = os.path.join(ROOT, "README.md")
        txt = open(p, encoding="utf-8").read()
        txt = re.sub(r"(<!-- speed:start -->).*?(<!-- speed:end -->)", lambda x: x.group(1) + speed + x.group(2), txt, flags=re.S)
        open(p, "w", encoding="utf-8").write(txt)
    return 0


if __name__ == "__main__":
    sys.exit(main())
