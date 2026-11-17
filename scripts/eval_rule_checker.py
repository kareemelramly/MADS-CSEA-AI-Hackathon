"""Measures the trick-prompt defences and writes docs/guardrail_eval.md (numbers only from this run).

Layer 1 = fixed pattern rules (guardrails.check_request). Layer 2 = local model rule checker
(agents/rule_checker.py). Two sets: the main set (patterns were tuned on it: in-sample) and the
held-out set (written after the last pattern change and never used to tune).

    python scripts/eval_rule_checker.py            # uses LOCAL_BASE_URL (default http://127.0.0.1:8080/v1)
    python scripts/eval_rule_checker.py --patterns-only
"""
import argparse
import datetime
import json
import os
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.environ["DECISION_LOG_PATH"] = os.path.join(tempfile.mkdtemp(prefix="rule_eval_"), "log.json")  # never touches the demo log
os.environ.setdefault("STATE_DIR", tempfile.mkdtemp(prefix="rule_eval_state_"))
os.environ.setdefault("LOCAL_BASE_URL", "http://127.0.0.1:8080/v1")

import guardrails  # noqa: E402
import llm  # noqa: E402
from agents import rule_checker  # noqa: E402


def load(name):
    with open(os.path.join(ROOT, "tests", "evals", name), encoding="utf-8") as f:
        return [c for c in json.load(f) if c["kind"] == "request"]


def score(cases, flag):
    banned = [c for c in cases if c["banned"]]
    benign = [c for c in cases if not c["banned"]]
    missed = [c["text"] for c in banned if not flag(c["text"])]
    false_alarms = [c["text"] for c in benign if flag(c["text"])]
    return {"caught": len(banned) - len(missed), "banned": len(banned), "false_alarms": len(false_alarms),
            "benign": len(benign), "missed": missed, "false_alarm_list": false_alarms}


def line(name, s):
    return (f"| {name} | {s['caught']}/{s['banned']} ({s['caught'] / max(s['banned'], 1):.0%}) | "
            f"{s['false_alarms']}/{s['benign']} ({s['false_alarms'] / max(s['benign'], 1):.0%}) |")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--patterns-only", action="store_true")
    a = ap.parse_args()
    sets = {"main (in-sample)": load("trick_prompts.json"), "regression (original holdout)": load("trick_prompts_holdout.json")}
    model_ok = (not a.patterns_only) and llm.local_ready()[0] == "ready"
    model_id = llm.model_label(llm.tiers()[0]) if model_ok else None
    rows, details = [], []
    for name, cases in sets.items():
        p = score(cases, lambda t: guardrails.check_request(t) is not None)
        rows.append(line(f"{name}, patterns only", p))
        if model_ok:
            unchecked = []

            def both(t):
                r = rule_checker.check(t)
                if not r["refused"] and not r["model_checked"]:
                    unchecked.append(t)
                return r["refused"]
            b = score(cases, both)
            rows.append(line(f"{name}, patterns + local model", b))
            if unchecked:
                details.append(f"- {name}: the model check did not run for {len(unchecked)} request(s); patterns decided those.")
            details += [f"- {name}, still missed: {t}" for t in b["missed"]] + [f"- {name}, false alarm: {t}" for t in b["false_alarm_list"]]
        else:
            details += [f"- {name}, missed by patterns: {t}" for t in p["missed"]] + [f"- {name}, false alarm: {t}" for t in p["false_alarm_list"]]
    now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    md = ["# Guardrail evaluation (trick prompts)", "",
          f"Measured {now} by `scripts/eval_rule_checker.py`. Model layer: "
          + (f"`{model_id}` through the local llama.cpp server." if model_ok else "NOT measured in this run (no local model reachable or --patterns-only)."), "",
          "| Set and layers | Banned requests refused | Honest requests refused (false alarms) |", "|---|---|---|", *rows, "",
          "The main set was used to write the original pattern rules. The original held-out set is now a regression set because its false alarms informed changes to the patterns and model prompt. "
          "A request is refused if either layer refuses. Everything the agents produce is checked again by `guardrails.check` and needs founder approval before it can go anywhere, so this box is not the only defence.", "",
          "## Misses and false alarms", "", *(details or ["- none"]), ""]
    out = os.path.join(ROOT, "docs", "guardrail_eval.md")
    with open(out, "w", encoding="utf-8") as f:
        f.write("\n".join(md))
    print("\n".join(rows))
    print(f"written {os.path.relpath(out, ROOT)}")


if __name__ == "__main__":
    main()
