"""pivot_back routes for G3, G4 and G5, and the SIMULATED persona stress test (SRS VAL-9)."""
import json
import os

import gates
import llm
import orchestrator
from conftest import FakeLLM, TestFounder, drive, gen, load_brief


def _run(script, overrides=None, label="p"):
    llm.set_fake(FakeLLM(overrides or {}))
    b, pre = load_brief("r")
    ctx = orchestrator.new_run(b, label)
    drive(ctx, TestFounder(pre, script=script), max_steps=120)
    return ctx


def test_g3_rescope_once_then_stop(env, fake_sources):
    def five_steps(system, user, schema, ids):
        d = gen(schema, ids)
        d["journey"] = [f"Step {i}" for i in range(5)]               # builder fills only 3 sections -> QA-04 fails
        return d
    ctx = _run({"gate:3:": {"choice": "pivot"}}, {"define_mvp": five_steps})
    outs = [g["outcome"] for g in ctx.gates if g["gate"] == "phase3_gate"]
    assert "pivot_back" not in outs[:2] and outs.count("repeat") >= 4
    log = json.load(open(env / "decision_log.json"))
    assert any(e["action"] == "pivot_back" and e.get("from_phase") == 3 for e in log)
    assert ctx.final_outcome == "stop"


def test_g3_banned_content_never_rescopes():
    qa = [{"id": "QA-08", "name": "Banned", "status": "fail", "evidence": "x"}]
    assert gates.build_gate(qa=qa, attempt=3, max_attempts=3, rescope_left=True).outcome == "stop"


def test_g4_rejected_offer_pivots_to_phase3(env, fake_sources):
    calls = {"n": 0}

    def once_reject(p):
        calls["n"] += 1
        return {"choice": "reject"} if calls["n"] == 1 else {"choice": "approve"}
    ctx = _run({"approval:None:commercial_setup": once_reject, "gate:4:": {"choice": "pivot"}})
    log = json.load(open(env / "decision_log.json"))
    assert any(e["action"] == "pivot_back" and e.get("from_phase") == 4 and e.get("to_phase") == 3 for e in log)
    assert ctx.finished and ctx.final("phase6_step1_memo")


def test_g5_rejected_drafts_retry(env, fake_sources):
    calls = {"n": 0}

    def once_reject(p):
        calls["n"] += 1
        return {"choice": "reject"} if calls["n"] == 1 else {"choice": "approve"}
    ctx = _run({"approval:None:publish_store_page": once_reject, "gate:5:": {"choice": "retry"}})
    g5 = [g["outcome"] for g in ctx.gates if g["gate"] == "phase5_gate"]
    assert g5[0] == "pivot_back" and g5[-1] == "go"


def test_persona_test_is_simulated_and_excluded(env, fake_sources):
    def personas(system, user, schema, ids):
        d = gen(schema, ids)
        for p in d["personas"]:
            p["would_join_waitlist"] = True
        return d
    ctx = _run({}, {"simulate_personas": personas})
    f = ctx.final("phase2_step4_persona_stress_test")
    text = open(env / "outputs" / os.path.basename(f["path"]), encoding="utf-8").read()
    assert text.count("SIMULATED") >= 6
    g2 = json.load(open(env / "outputs" / "phase2_gate_decision_p_a1.json"))["gate"]
    assert g2["outcome"] == "awaiting_evidence" and g2["numbers"]["simulated_signups_excluded"] == 5
    assert g2["numbers"]["real_signups"] == 0
