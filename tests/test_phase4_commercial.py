"""Phase 4: price evidence, DRAFT policies, commercial approval (SRS COM-1 to COM-3)."""
import json

import pytest

import approval
import gates
import sources
from agents import pricer, policy_drafter
from conftest import FakeLLM, gen
from run_context import RunContext
import llm


class Pages:
    def __init__(self, broken=()):
        self.broken = broken

    def __call__(self, url, timeout):
        if any(b in url for b in self.broken):
            return 404, ""
        return 200, "<html>Price $19 one-time, $25, $15</html>"


Q = [{"name": f"c{i}", "url": f"https://shop.example/{i}", "amount": a, "currency": "USD", "kind": "one_time", "display": f"${a}"}
     for i, a in enumerate([19, 25, 15])]


def test_median_of_three_in_code(env):
    sources.set_http(Pages())
    r = pricer.run(RunContext(brief={}, label="t"), Q)
    assert r["price"] == 19 and r["paid_quotes"] == 3


def test_fewer_than_three_repeat(env):
    sources.set_http(Pages(broken=("/2",)))
    r = pricer.run(RunContext(brief={}, label="t"), Q)
    assert r["price"] is None and r["paid_quotes"] == 2
    g = gates.commercial_gate(quotes_ok=2, price=None, policies_missing=[], overridden_price=False)
    assert g.outcome == "repeat"


def test_free_and_subscription_not_in_median(env):
    sources.set_http(Pages())
    q = Q + [{"name": "free", "url": "https://shop.example/f", "amount": 0, "currency": "USD", "kind": "free"},
             {"name": "sub", "url": "https://shop.example/s", "amount": 99, "currency": "USD", "kind": "subscription"}]
    r = pricer.run(RunContext(brief={}, label="t"), q)
    assert r["price"] == 19 and len(r["rows"]) == 5


def test_criteria_logged_first(env):
    sources.set_http(Pages())
    pricer.run(RunContext(brief={}, label="t"), Q)
    acts = [e["action"] for e in json.load(open(env / "decision_log.json"))]
    assert acts[0] == "define_pricing_criteria"


def test_policies_start_with_draft_banner(env):
    llm.set_fake(FakeLLM())
    c = RunContext(brief={}, label="t")
    c.handoffs["H1"] = {"idea_name": "Pack", "idea_description": "d"}
    docs, missing = policy_drafter.run(c, 19, "USD")
    assert not missing and set(docs) == {"terms", "privacy", "refund", "delivery"}
    assert all(d.startswith("DRAFT · FOUNDER REVIEW REQUIRED · Not legal advice") for d in docs.values())


def test_compliance_claim_flagged(env):
    def pol(system, user, schema, ids):
        d = gen(schema, ids)
        d["privacy"]["purpose"] = "We are fully compliant with GDPR."
        return d
    llm.set_fake(FakeLLM({"draft_policies": pol}))
    c = RunContext(brief={}, label="t")
    c.handoffs["H1"] = {"idea_name": "Pack", "idea_description": "d"}
    _, missing = policy_drafter.run(c, 19, "USD")
    assert missing


def test_changed_price_after_approval_refused(env):
    content = json.dumps({"price": 19})
    aid = approval.request("commercial_setup", content, "none: STUBBED", 0, "USD", "r1")
    approval.approve(aid, founder_action="button")
    with pytest.raises(approval.ApprovalError):
        approval.execute(aid, "commercial_setup", json.dumps({"price": 29}), "none: STUBBED", 0, "USD", "r1", lambda: 1)


def test_requirements_have_no_payment_sdk():
    import os
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    req = open(os.path.join(root, "requirements.txt")).read().lower()
    for sdk in ("stripe", "paypal", "braintree", "square", "adyen", "paddle", "lemonsqueezy"):
        assert sdk not in req
