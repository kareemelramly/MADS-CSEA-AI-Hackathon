"""Backbone: log keys, write-once outputs, approval binding (5 fields), single use, prohibited
actions, overrides (SRS LOG-1, CORE-6, CORE-7, APR-1 to APR-9)."""
import json

import pytest

import approval
import log
import orchestrator
from run_context import RunContext


def ctx():
    return RunContext(brief={"idea": "x"}, label="t")


def test_log_entries_have_required_keys(env):
    c = ctx()
    c.log("researcher", "find_opportunities", sources=["https://example.org/a", "not a url"])
    data = json.load(open(env / "decision_log.json"))
    assert len(data) == 1
    e = data[0]
    for k in ("timestamp", "agent", "action", "sources", "model", "cost", "approved_by", "run_id"):
        assert k in e
    assert e["sources"] == ["https://example.org/a"] and e["run_id"] == c.run_id


def test_log_never_contains_keys(env):
    log.log("llm", "x", detail="Authorization: Bearer abcdefghijklmnop nvapi-1234567890abc")
    raw = open(env / "decision_log.json").read()
    assert "abcdefghijklmnop" not in raw and "nvapi-123" not in raw


def test_old_saved_run_with_unknown_keys_still_loads(env):
    ctx = orchestrator.new_run({"idea": "public demo idea"}, "t")
    d = json.loads(ctx.to_json())
    d["remote_model_consent"] = True          # field from an older version
    assert RunContext.from_json(json.dumps(d)).run_id == ctx.run_id

def test_write_once_and_attempts(env):
    c = ctx()
    a1 = c.out("phase1_step1_opportunities", "md", "one")
    a2 = c.out("phase1_step1_opportunities", "md", "two")
    assert a1["path"].endswith("_t_a1.md") and a2["path"].endswith("_t_a2.md")
    assert a1["status"] == "superseded" and a2["status"] == "final"
    with pytest.raises(FileExistsError):
        open(env / "outputs" / "phase1_step1_opportunities_t_a1.md", "x")
    with pytest.raises(ValueError):
        c.out("random_name", "md", "x")


BASE = dict(action="publish_landing_page", content="<html>page</html>", destination="none: STUBBED", amount_minor=0, currency="USD")


def _approved(run_id):
    aid = approval.request(BASE["action"], BASE["content"], BASE["destination"], 0, "USD", run_id)
    approval.approve(aid, founder_action="button")
    return aid


@pytest.mark.parametrize("field,value", [("action", "release_product"), ("content", "<html>changed</html>"),
                                         ("destination", "twitter"), ("amount_minor", 1), ("run_id", "other-run")])
def test_approval_refused_after_any_field_change(env, field, value):
    aid = _approved("run-1")
    args = {**BASE, "run_id": "run-1", field: value}
    with pytest.raises(approval.ApprovalError, match="approval_mismatch"):
        approval.execute(aid, args["action"], args["content"], args["destination"], args["amount_minor"], args["currency"], args["run_id"], lambda: "done")
    logd = json.load(open(env / "decision_log.json"))
    mm = [e for e in logd if e["action"] == "approval_mismatch"]
    assert mm and field.replace("content", "content_sha256") in mm[-1]["changed_fields"]


def test_consumed_approval_cannot_run_twice(env):
    aid = _approved("run-1")
    assert approval.execute(aid, **BASE, run_id="run-1", do=lambda: "ok") == "ok"
    with pytest.raises(approval.ApprovalError, match="consumed"):
        approval.execute(aid, **BASE, run_id="run-1", do=lambda: "ok")


def test_execute_without_approval_refused(env):
    aid = approval.request(BASE["action"], BASE["content"], BASE["destination"], 0, "USD", "run-1")
    with pytest.raises(approval.ApprovalError):
        approval.execute(aid, **BASE, run_id="run-1", do=lambda: "ok")
    with pytest.raises(approval.ApprovalError):
        approval.execute("apr_missing", **BASE, run_id="run-1", do=lambda: "ok")


def test_no_default_approval(env):
    aid = approval.request(BASE["action"], BASE["content"], BASE["destination"], 0, "USD", "run-1")
    with pytest.raises(approval.ApprovalError):
        approval.approve(aid, founder_action="auto")
    assert approval.get(aid)["status"] == "pending"


@pytest.mark.parametrize("action", ["charge_card", "refund_money", "transfer", "create_account", "store_credentials", "sandbox_payment"])
def test_prohibited_actions_cannot_be_requested(env, action):
    with pytest.raises(approval.ApprovalError):
        approval.request(action, "x", "y", 0, "USD", "run-1")


def test_nonzero_amount_cannot_be_requested(env):
    with pytest.raises(approval.ApprovalError):
        approval.request("commercial_setup", "x", "y", 500, "USD", "run-1")


def test_override_rules(env):
    c = ctx()
    with pytest.raises(approval.ApprovalError):
        approval.override(c, 2, "awaiting_evidence", "too short")
    with pytest.raises(approval.ApprovalError):
        approval.override(c, 1, "stop", "a long enough reason for the override", kind="exclusion")
    with pytest.raises(approval.ApprovalError):
        approval.override(c, 3, "stop", "a long enough reason for the override", kind="phase3_test_gate")
    approval.override(c, 2, "awaiting_evidence", "Founder wants to see the later phases now")
    assert c.validation_status == "UNVALIDATED_FOUNDER_OVERRIDE"
    rec = c.out("phase3_step1_mvp_definition", "md", "body")
    text = open(env / "outputs" / rec["path"].split("/")[-1], encoding="utf-8").read()
    assert text.startswith("UNVALIDATED · FOUNDER OVERRIDE")
    c.log("x", "after_override")
    assert json.load(open(env / "decision_log.json"))[-1]["override"] is True
