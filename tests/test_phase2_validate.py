"""Phase 2 Validate: gate branches, approval, guardrails, override (SRS VAL-1 to VAL-10, CORE-8)."""
import itertools

import pytest

import approval
import gates
import orchestrator
from conftest import FakeLLM, TestFounder, drive, load_brief
import llm

PLAN = {"signups_target": 100, "days": 14, "min_visitors": 200}
LOCK = gates.lock_target(PLAN)


def vg(status="completed", signups=0, visitors=None, attempt=1, alts=True, plan=PLAN):
    return gates.validate_gate(plan=plan, lock=LOCK, counts={"experiment_status": status, "signups": signups, "visitors": visitors},
                               attempt=attempt, max_attempts=2, alternatives_left=alts)


def test_not_started_awaits_evidence():
    g = vg(status="not_started")
    assert g.outcome == "awaiting_evidence" and "nothing is decided" in g.verdict


def test_running_awaits_evidence():
    assert vg(status="running").outcome == "awaiting_evidence"


def test_completed_zero_fails():
    assert vg(signups=0).outcome in ("pivot_back", "stop")
    assert vg(signups=0, alts=False).outcome == "stop"


def test_twelve_of_hundred_fails():
    g = vg(signups=12, alts=True)
    assert g.outcome == "pivot_back" and "0.12" in g.verdict


def test_final_attempt_near_miss():
    assert vg(signups=60, attempt=1).outcome == "repeat"
    assert vg(signups=60, attempt=2, alts=False).outcome == "stop"


def test_low_exposure_and_abandoned_repeat():
    assert vg(signups=50, visitors=40).outcome == "repeat"
    assert vg(status="abandoned").outcome == "repeat"


def test_target_tamper_stops():
    g = vg(signups=100, plan={**PLAN, "signups_target": 10})
    assert g.outcome == "stop" and not g.overridable


def test_go_on_target():
    assert vg(signups=100).outcome == "go"


def test_simulated_counts_never_reach_gate():
    g = gates.validate_gate(plan=PLAN, lock=LOCK, counts={"experiment_status": "completed", "signups": 0, "simulated_signups": 500},
                            attempt=1, max_attempts=2, alternatives_left=False)
    assert g.outcome == "stop" and "excluded" in g.verdict


def test_gate_covers_all_branches():
    seen = set()
    for st, s, v, a, alt in itertools.product(["not_started", "running", "completed", "abandoned"], [0, 12, 60, 100, 150],
                                              [None, 40, 500], [1, 2], [True, False]):
        g = vg(status=st, signups=s, visitors=v, attempt=a, alts=alt)
        assert g.outcome in gates.OUTCOMES + (gates.PAUSE,)
        seen.add(g.outcome)
    assert seen == {"go", "repeat", "pivot_back", "stop", "awaiting_evidence"}


def test_publish_blocked_without_approval(env):
    aid = approval.request("publish_landing_page", "<p>x</p>", "none", 0, "USD", "r1")
    with pytest.raises(approval.ApprovalError):
        approval.execute(aid, "publish_landing_page", "<p>x</p>", "none", 0, "USD", "r1", lambda: 1)
    approval.approve(aid, founder_action="button")
    with pytest.raises(approval.ApprovalError):
        approval.execute(aid, "publish_landing_page", "<p>changed</p>", "none", 0, "USD", "r1", lambda: 1)


@pytest.mark.parametrize("bad", ["Join 2,000 planners on the waitlist", "Only 3 spots left!", "Rated 4.9/5",
                                 "Guaranteed to grow your income", "What our customers say: amazing"])
def test_banned_landing_elements_refused(env, fake_sources, bad):
    def landing(system, user, schema, ids):
        from conftest import gen
        d = gen(schema, ids)
        d["headline"] = bad
        return d
    llm.set_fake(FakeLLM({"write_landing_page": landing}))
    b, pre = load_brief("r")
    ctx = orchestrator.new_run(b, "t")
    p = orchestrator.run_until_gate(ctx)
    orchestrator.respond(ctx, {"choice": "continue"}, "button")
    p = orchestrator.run_until_gate(ctx)
    assert p["kind"] == "gate" and p["phase"] == 2 and "guardrails" in p["verdict"]
    assert not any(a["name"] == "phase2_step3_landing_page" for a in ctx.artifacts)


def test_awaiting_without_override_does_not_start_phase3(env, fake_llm, fake_sources):
    b, pre = load_brief("r")
    ctx = orchestrator.new_run(b, "t")
    f = TestFounder(pre, script={"gate:2:": {"choice": "stop"}})
    drive(ctx, f)
    assert not any(a["name"].startswith("phase3") for a in ctx.artifacts)
    assert ctx.final_outcome == "awaiting_evidence"


def test_override_needs_reason(env, fake_llm, fake_sources):
    b, pre = load_brief("r")
    ctx = orchestrator.new_run(b, "t")
    f = TestFounder(pre, script={"gate:2:": {"choice": "override", "reason": "short"}})
    with pytest.raises(approval.ApprovalError):
        drive(ctx, f)


def test_canvas_boxes_sourced_or_assumption(env, fake_llm, fake_sources):
    b, pre = load_brief("r")
    ctx = orchestrator.new_run(b, "t")
    drive(ctx, TestFounder(pre, script={"gate:2:": {"choice": "stop"}}))
    canvas = ctx.data["p2.canvas"]
    assert len(canvas) == 9
    assert all(v["source_ids"] or v["assumption"] for v in canvas.values())
