"""Phase 3 Build: 14 checks, income-promise block, model errors use no attempt, release approval (SRS BLD-0 to BLD-8)."""
import ast
import json
import os

import pytest

import approval
import llm
import orchestrator
from conftest import FakeLLM, TestFounder, drive, gen, load_brief

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def run_r(env, overrides=None, script=None):
    llm.set_fake(FakeLLM(overrides or {}))
    b, pre = load_brief("r")
    ctx = orchestrator.new_run(b, "t")
    drive(ctx, TestFounder(pre, script=script or {}))
    return ctx


def test_fixture_passes_all_applicable_checks(env, fake_sources):
    ctx = run_r(env)
    rep = [a for a in ctx.artifacts if a["name"] == "phase3_step5_test_report"]
    text = open(env / "outputs" / os.path.basename(rep[-1]["path"]), encoding="utf-8").read()
    assert text.count("| pass |") == 14 and "| QA-07 | Script integrity | n/a |" in text
    for name in ("phase3_step3_product_checklist", "phase3_step3_product_tracker", "phase3_step3_product_license",
                 "phase3_step4_user_docs", "phase3_step6_handoff", "phase3_gate_decision"):
        assert ctx.final(name), name


def test_income_promise_repeats_then_stops(env, fake_sources):
    def slots(system, user, schema, ids):
        d = gen(schema, ids)
        d["sections"][0]["items"][0] = "This checklist guarantees extra income for your agency"
        return d
    ctx = run_r(env, {"fill_template_slots": slots})
    gates_ = [g for g in ctx.gates if g["gate"] == "phase3_gate"]
    assert [g["outcome"] for g in gates_] == ["repeat", "repeat", "stop"]
    assert ctx.final_outcome == "stop"
    assert not ctx.final("phase3_step6_handoff")


def test_model_error_uses_no_build_attempt(env, fake_sources):
    calls = {"n": 0}

    def flaky(system, user, schema, ids):
        calls["n"] += 1
        if calls["n"] == 1:
            return llm.ModelError(["local: timeout"])
        return gen(schema, ids)
    llm.set_fake(FakeLLM({"fill_template_slots": flaky}))
    b, pre = load_brief("r")
    ctx = orchestrator.new_run(b, "t")
    f = TestFounder(pre)
    for _ in range(40):
        p = orchestrator.run_until_gate(ctx)
        if p["kind"] == "done":
            break
        if p["kind"] == "error":
            assert ctx.data.get("p3_attempt", 1) == 1
            orchestrator.respond(ctx, {"choice": "try_again"}, "button")
            continue
        orchestrator.respond(ctx, f.answer(p), "button")
    assert [g["outcome"] for g in ctx.gates if g["gate"] == "phase3_gate"] == ["go"]


def test_release_needs_approval_and_manifest_change_refused(env, fake_sources):
    ctx = run_r(env, script={"approval:None:release_product": {"choice": "reject"}})
    assert not ctx.final("phase3_step6_handoff")
    m = {"files": [{"path": "a", "sha256": "1"}]}
    aid = approval.request("release_product", json.dumps(m), "none", 0, "USD", "r1")
    approval.approve(aid, founder_action="button")
    m["files"][0]["sha256"] = "2"
    with pytest.raises(approval.ApprovalError, match="content_sha256"):
        approval.execute(aid, "release_product", json.dumps(m), "none", 0, "USD", "r1", lambda: 1)


def test_founder_cannot_override_test_gate(env):
    from run_context import RunContext
    with pytest.raises(approval.ApprovalError):
        approval.override(RunContext(brief={}, label="t"), 3, "stop", "please let this through anyway now", kind="phase3_test_gate")


def test_builder_never_calls_eval_exec_subprocess():
    for f in ("agents/builder.py", "agents/qa.py", "agents/doc_writer.py", "agents/packager.py"):
        tree = ast.parse(open(os.path.join(ROOT, f)).read())
        names = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)} | {n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)}
        mods = {a.name for n in ast.walk(tree) if isinstance(n, (ast.Import, ast.ImportFrom)) for a in n.names}
        assert not ({"eval", "exec", "system", "popen"} & names), f
        assert "subprocess" not in mods and "os.system" not in names, f


def test_templates_autoescape():
    from agents import builder, landing_writer
    assert builder.ENV.autoescape("x.md.j2") and landing_writer.ENV.autoescape("x.html.j2")
