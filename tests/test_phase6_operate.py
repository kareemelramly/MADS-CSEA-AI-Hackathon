"""Phase 6 Operate: real-only metrics, targets first, support rules (SRS OPS-1 to OPS-8)."""
import json

import pytest

import approval
import gates
import orchestrator
from agents import analyst, support_agent
from conftest import FakeLLM, TestFounder, drive, gen, load_brief
from run_context import RunContext
import llm

T = {"waitlist_signups": 100}


def test_mock_only_never_persevere():
    g = gates.operate_gate(targets=T, metrics=[{"name": "mock_orders", "value": 500, "label": "MOCKED"}], phase2_completed=True, alternative_left=False)
    assert g.outcome == "repeat"


def test_awaiting_never_persevere():
    g = gates.operate_gate(targets=T, metrics=[{"name": "waitlist_signups", "value": None, "label": "real"}], phase2_completed=False, alternative_left=True)
    assert g.outcome == "repeat"


def test_real_metrics_rules():
    real = lambda v: [{"name": "waitlist_signups", "value": v, "label": "real"}]
    assert gates.operate_gate(targets=T, metrics=real(120), phase2_completed=True, alternative_left=False).outcome == "go"
    assert gates.operate_gate(targets=T, metrics=real(20), phase2_completed=True, alternative_left=True).outcome == "pivot_back"
    assert gates.operate_gate(targets=T, metrics=real(20), phase2_completed=True, alternative_left=False).outcome == "stop"


def test_values_without_evidence_are_simulated():
    c = RunContext(brief={}, label="t")
    c.handoffs["H2"] = {"experiment_status": "not_started"}
    rows = analyst.metrics(c, {"orders": 1}, [{"name": "paying_customers", "value": 9}])
    lab = {r["name"]: r["label"] for r in rows}
    assert lab["paying_customers"] == "SIMULATED" and lab["mock_orders"] == "MOCKED"


def test_targets_logged_first_and_every_number_labelled(env, fake_llm, fake_sources):
    b, pre = load_brief("r")
    ctx = orchestrator.new_run(b, "t")
    drive(ctx, TestFounder(pre))
    acts = [e["action"] for e in json.load(open(env / "decision_log.json"))]
    assert acts.index("set_phase6_targets") < acts.index("draft_support_faq")
    memo = open(env / "outputs" / "phase6_step1_memo_t_a1.md", encoding="utf-8").read()
    rows = [l for l in memo.splitlines() if l.startswith("| ") and not l.startswith("| Metric") and "|---" not in l and "Target" not in l]
    metric_rows = [l for l in rows if l.count("|") == 5]
    assert metric_rows and all(any(t in l for t in ("| real |", "| MOCKED |", "| SIMULATED |")) for l in metric_rows)
    assert "persevere is recommended" not in memo


def test_founder_decision_logged(env, fake_llm, fake_sources):
    b, pre = load_brief("r")
    ctx = orchestrator.new_run(b, "t")
    drive(ctx, TestFounder(pre, script={"gate:6:": {"choice": "pivot"}}))
    e = [x for x in json.load(open(env / "decision_log.json")) if x["action"] == "phase6_decision"][0]
    assert e["approved_by"] == "founder" and e["choice"] == "pivot" and e["recommendation"] == "repeat"


def test_support_refuses_advice_and_promises():
    for q in ("Can I get a refund?", "Is this legal advice for my contract?", "Will this help my tax return?"):
        assert support_agent.answer_policy({"question": q, "answer": "Sure!", "cites": ["terms"]})["escalate"]
    r = support_agent.answer_policy({"question": "Format?", "answer": "This guarantees more income", "cites": []})
    assert r["escalate"]
    ok = support_agent.answer_policy({"question": "What format is it?", "answer": "Markdown and CSV files.", "cites": ["product_docs"]})
    assert not ok["escalate"] and ok["label"].startswith("DRAFT")


def test_support_reply_needs_approval(env):
    aid = approval.request("send_support_reply", "Markdown and CSV files.", "buyer (placeholder)", 0, "USD", "r1")
    with pytest.raises(approval.ApprovalError):
        approval.execute(aid, "send_support_reply", "Markdown and CSV files.", "buyer (placeholder)", 0, "USD", "r1", lambda: 1)
    approval.approve(aid, founder_action="button")
    res = approval.execute(aid, "send_support_reply", "Markdown and CSV files.", "buyer (placeholder)", 0, "USD", "r1",
                           lambda: approval.send_stub("r1", "buyer (placeholder)", "sha"))
    assert "STUBBED" in res["status"]
