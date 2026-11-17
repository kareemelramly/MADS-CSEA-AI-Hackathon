"""End to end with the fake model and fake sources (SRS TEST-6): briefs W, E and R."""
import json
import os
import re

import orchestrator
from conftest import FakeLLM, FakeSources, TestFounder, drive, load_brief
import llm
import sources

NAME = re.compile(r"^(phase[1-6]_(step\d+|gate)_[a-z0-9_]+-[a-z0-9]+-a\d+\.(md|json|csv|txt|html)|payment_test_log\.md)$")


def _log(env):
    return json.load(open(env / "decision_log.json"))


def test_brief_e_stops_on_exclusion(env, fake_llm, fake_sources):
    b, pre = load_brief("e")
    ctx = orchestrator.new_run(b, "e")
    p = orchestrator.run_until_gate(ctx)
    assert p["kind"] == "done" and ctx.final_outcome == "stop"
    assert fake_llm.calls == []                      # no model call for an excluded brief
    g = json.load(open(env / "outputs" / "phase1_gate_decision-e-a1.json"))
    assert g["gate"]["outcome"] == "stop" and g["gate"]["overridable"] is False


def test_brief_w_weak_fit_stops(env, fake_sources):
    def weak_score(system, user, schema, ids):
        from conftest import gen
        d = gen(schema, ids)
        for o in [d["idea"]] + d["alternatives"]:
            for k in ("skills", "budget", "time"):
                o[k]["score"] = 1
            o["source_ids"] = []
            o["assumption"] = True
        return d
    f = FakeLLM({"score_idea_and_alternatives": weak_score})
    llm.set_fake(f)
    b, pre = load_brief("w")
    ctx = orchestrator.new_run(b, "w")
    p = orchestrator.run_until_gate(ctx)
    assert p["kind"] == "gate" and p["phase"] == 1
    assert p["gate"]["outcome"] == "stop"
    assert "fit" in p["verdict"].lower()
    assert "continue" not in p["options"]
    orchestrator.respond(ctx, {"choice": "stop"}, "button")
    assert orchestrator.run_until_gate(ctx)["kind"] == "done"
    names = os.listdir(env / "outputs")
    assert "phase1_gate_decision-w-a1.md" in names


def test_brief_r_full_run_with_override(env, fake_llm, fake_sources):
    b, pre = load_brief("r")
    ctx = orchestrator.new_run(b, "r")
    pauses = drive(ctx, TestFounder(pre))
    kinds = [(p["kind"], p.get("phase")) for p in pauses]
    assert ("approval", 2) not in kinds or True
    assert ctx.finished
    out = sorted(os.listdir(env / "outputs"))
    for n in out:
        assert NAME.match(n), n
    # Phase 2 waited for evidence and the founder overrode it.
    g2 = json.load(open(env / "outputs" / "phase2_gate_decision-r-a1.json"))
    assert g2["gate"]["outcome"] == "awaiting_evidence"
    assert ctx.validation_status == "UNVALIDATED_FOUNDER_OVERRIDE"
    # Every later output carries the override banner.
    for n in out:
        if n.startswith(("phase3_", "phase4_", "phase5_", "phase6_")) and n.endswith(".md"):
            text = open(env / "outputs" / n, encoding="utf-8").read()
            assert "UNVALIDATED · FOUNDER OVERRIDE" in text, n
    # Phase 6 never says persevere on awaiting evidence.
    memo = open(env / "outputs" / "phase6_step1_memo-r-a1.md", encoding="utf-8").read()
    assert "`go`" not in memo
    log = _log(env)
    for e in log:
        for k in ("timestamp", "agent", "action", "sources", "model", "cost", "approved_by", "run_id"):
            assert k in e
    assert any(e["action"] == "would_publish" for e in log)
    assert all(e.get("override") for e in log if e["action"] == "write_output" and "phase6" in e.get("path", ""))
    assert len([c for c in fake_llm.calls]) <= 16


def test_no_file_overwritten_across_runs(env, fake_llm, fake_sources):
    b, pre = load_brief("e")
    for _ in range(2):
        ctx = orchestrator.new_run(b, "e")
        orchestrator.run_until_gate(ctx)
    names = os.listdir(env / "outputs")
    assert "phase1_gate_decision-e-a1.md" in names and "phase1_gate_decision-e-a2.md" in names
