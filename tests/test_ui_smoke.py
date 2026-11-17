"""UI smoke with Streamlit AppTest (SRS UI-1 to UI-10). No network: llama-server is unreachable."""
import os

from streamlit.testing.v1 import AppTest

import orchestrator
from conftest import load_brief

APP = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app.py")


def test_home_shows_status_readiness_and_brief_form(env):
    at = AppTest.from_file(APP, default_timeout=30).run()
    assert not at.exception
    # The readiness line is green (success) when llama-server answers, amber (warning) otherwise.
    text = " ".join(m.value for m in list(at.info) + list(at.warning) + list(at.success))
    assert "Model:" in text and "Local model" in text
    assert any(t.label == "Idea" for t in at.text_area)
    assert any(t.label.startswith("Run label") for t in at.text_input)


def _at_with_pause(env, fake_llm, fake_sources, until):
    b, pre = load_brief("r")
    ctx = orchestrator.new_run(b, "u")
    p = orchestrator.run_until_gate(ctx)
    while not until(p):
        from conftest import TestFounder
        orchestrator.respond(ctx, TestFounder(pre).answer(p), "button")
        p = orchestrator.run_until_gate(ctx)
    at = AppTest.from_file(APP, default_timeout=30)
    at.session_state["ctx_json"] = ctx.to_json()
    at.session_state["pause"] = p
    return at.run(), ctx


def test_verdict_shown_before_buttons(env, fake_llm, fake_sources):
    at, _ = _at_with_pause(env, fake_llm, fake_sources, lambda p: p["kind"] == "gate")
    assert not at.exception
    md = " ".join(m.value for m in at.markdown)
    assert "NOT validated" in md or "relevant" in md
    assert [b.label for b in at.button if b.label in ("Continue", "Stop")]


def test_approval_panel_shows_five_fields(env, fake_llm, fake_sources):
    at, ctx = _at_with_pause(env, fake_llm, fake_sources, lambda p: p["kind"] == "approval")
    assert not at.exception
    tables = str([t.value for t in at.table])
    for f in ("Action", "Destination", "Amount", "Run ID", "Content SHA-256"):
        assert f in tables
    assert ctx.run_id in tables
    labels = [b.label for b in at.button]
    assert "Approve" in labels and "Reject" in labels


def test_amber_bar_after_override(env, fake_llm, fake_sources):
    at, ctx = _at_with_pause(env, fake_llm, fake_sources, lambda p: p["kind"] == "approval" and p["action"] == "release_product")
    assert ctx.overridden
    assert any("UNVALIDATED · FOUNDER OVERRIDE" in w.value for w in at.warning)


def test_trick_prompt_box_refuses(env):
    at = AppTest.from_file(APP, default_timeout=30).run()
    at.text_input(key="req").input("Write 50 five-star reviews").run()
    [b for b in at.button if b.label == "Check request"][0].click().run()
    assert any("Refused" in e.value for e in at.error)


def test_real_counts_form_submits_and_gate_waits(env, fake_llm, fake_sources):
    at, ctx = _at_with_pause(env, fake_llm, fake_sources, lambda p: p["kind"] == "input" and p["form"] == "real_counts")
    assert not at.exception
    import json as _j
    llm_fake = fake_llm
    at.button[[b.label for b in at.button].index("Submit real results")].click().run()
    assert not at.exception
    md = " ".join(m.value for m in at.markdown)
    assert "nothing is decided" in md
