"""Phase 1 Discover on recorded-style fixtures, no network (SRS DIS-1 to DIS-11, CORE-1)."""
import json

import gates
import orchestrator
import sources
from conftest import FakeLLM, FakeSources, load_brief
import llm

TH = {"min_sources_ok": 2, "min_items_screened": 20, "min_relevant": 3, "min_relevant_sources": 2, "min_fit": 3.0}


def _gate(**kw):
    base = dict(missing_fields=[], excluded=None, values_conflict=None,
                coverage={"sources_ok": 3, "items_screened": 46, "failed": [], "retry_used": True},
                relevant={"count": 5, "sources": ["hn", "se", "gh"]}, fit=3.5, alternatives=[], thresholds=TH)
    base.update(kw)
    return gates.discover_gate(**base)


def test_excluded_brief_stops_not_overridable():
    g = _gate(excluded="financial_or_crypto")
    assert g.outcome == "stop" and not g.overridable


def test_missing_fields_repeat(env, fake_llm, fake_sources):
    b, _ = load_brief("r")
    b.pop("skills")
    ctx = orchestrator.new_run(b, "m")
    p = orchestrator.run_until_gate(ctx)
    assert p["gate"]["outcome"] == "repeat" and "skills" in p["verdict"]
    assert fake_llm.calls == []


def test_thin_coverage_repeats_never_stops():
    g = _gate(coverage={"sources_ok": 2, "items_screened": 7, "failed": ["github (HTTP 403)"], "retry_used": True},
              relevant={"count": 0, "sources": []}, fit=1)
    assert g.outcome == "repeat" and "7 items screened" in g.verdict and g.nothing_decided


def test_adequate_coverage_weak_evidence_no_alternative_stops():
    g = _gate(relevant={"count": 1, "sources": ["hn"]})
    assert g.outcome == "stop" and "1 relevant of 46 screened" in g.verdict


def test_weak_evidence_with_passing_alternative_pivots():
    g = _gate(relevant={"count": 1, "sources": ["hn"]}, alternatives=[{"name": "Alt", "fit": 4, "passes_evidence": True}])
    assert g.outcome == "pivot_back"


def test_low_fit_stops_or_pivots():
    assert _gate(fit=2.1).outcome == "stop"
    assert _gate(fit=2.1, alternatives=[{"name": "A", "fit": 3.4, "passes_evidence": True}]).outcome == "pivot_back"


def test_go_does_not_declare_demand_validated():
    g = _gate()
    assert g.outcome == "go" and "NOT validated" in g.verdict
    assert "does not independently establish demand" in g.verdict


def test_thresholds_logged_before_first_search(env, fake_llm, fake_sources):
    b, _ = load_brief("r")
    ctx = orchestrator.new_run(b, "t")
    orchestrator.run_until_gate(ctx)
    acts = [e["action"] for e in json.load(open(env / "decision_log.json"))]
    assert acts.index("define_research_criteria") < acts.index("search_sources")


def test_items_without_url_dropped_and_ids_assigned(env, fake_llm):
    class NoUrl(FakeSources):
        def __call__(self, url, timeout):
            if "api.github.com" in url:
                return 200, json.dumps({"items": [{"html_url": None, "title": "x"}] * 5})
            return super().__call__(url, timeout)
    sources.set_http(NoUrl("rich"))
    b, _ = load_brief("r")
    ctx = orchestrator.new_run(b, "t")
    orchestrator.run_until_gate(ctx)
    assert all(r["url"] for r in ctx.sources.values())
    assert all(sid.startswith("S") for sid in ctx.sources)


def test_unknown_source_id_from_model_is_rejected(env, fake_sources):
    def bad(system, user, schema, ids):
        return {"items": [{"source_id": "S999", "relevant": True, "pain_point": "x", "signal": "complaint"}]}
    llm.set_fake(FakeLLM({"screen_evidence": bad}))
    b, _ = load_brief("r")
    ctx = orchestrator.new_run(b, "t")
    orchestrator.run_until_gate(ctx)
    # S999 is not in the batch, so it is never counted as relevant evidence.
    assert all(r["source_id"] != "S999" for r in ctx.data.get("p1.1.relevant", []))


def test_source_outage_gives_repeat(env, fake_llm):
    sources.set_http(FakeSources("outage"))
    b, _ = load_brief("r")
    ctx = orchestrator.new_run(b, "t")
    p = orchestrator.run_until_gate(ctx)
    assert p["gate"]["outcome"] == "repeat" and "inconclusive" in p["verdict"]


def test_thin_search_fixture_repeats(env, fake_llm):
    sources.set_http(FakeSources("thin"))
    b, _ = load_brief("w")
    ctx = orchestrator.new_run(b, "t")
    p = orchestrator.run_until_gate(ctx)
    assert p["gate"]["outcome"] == "repeat"
    assert p["gate"]["numbers"]["sources_answered"] == 2


def test_model_outage_every_tier_gives_repeat(env, fake_sources):
    llm.set_fake(lambda *a: llm.ModelError(["all tiers down"]))
    b, _ = load_brief("r")
    ctx = orchestrator.new_run(b, "t")
    p = orchestrator.run_until_gate(ctx)
    assert p["kind"] == "error" and p["outcome"] == "repeat"


def test_founder_url_registered_only_if_it_loads(env, fake_llm):
    from run_context import RunContext
    class F(FakeSources):
        def __call__(self, url, timeout):
            return (404, "") if "broken" in url else (200, "<title>Forum</title> planners complain about spreadsheets")
    sources.set_http(F())
    c = RunContext(brief={}, label="t")
    assert sources.fetch_founder_url(c, "https://broken.example/x", "claim") is None
    assert sources.fetch_founder_url(c, "https://ok.example/x", "claim") == "S001"


def test_interview_drops_hypothetical_questions(env, fake_sources):
    def qs(system, user, schema, ids):
        return {"questions": [{"question": "Would you buy this?", "why": "x"}] + [{"question": f"Tell me about the last time you planned an event {i}", "why": "y"} for i in range(5)]}
    llm.set_fake(FakeLLM({"write_interview_script": qs}))
    b, _ = load_brief("r")
    ctx = orchestrator.new_run(b, "t")
    orchestrator.run_until_gate(ctx)
    kept, dropped = ctx.data["p1.1.interview"]
    assert dropped == 1 and all("Would" not in q["question"] for q in kept)


def test_launches_and_duplicates_do_not_count_as_demand(env, fake_sources):
    """Reviewer-reported evidence bugs: product launches are supply, duplicates count once,
    and a target country no source mentions is labelled ASSUMPTION."""
    from conftest import FakeLLM
    import llm

    def screen(system, user, schema, ids):
        return {"items": [{"source_id": i, "relevant": True, "pain_point": "p",
                           "signal": "launch_or_ad" if n % 2 else "complaint"} for n, i in enumerate(ids[:5])]}
    f = FakeLLM({"screen_evidence": screen})
    llm.set_fake(f)
    b, _ = load_brief("r")
    ctx = orchestrator.new_run(b, "d")
    orchestrator.run_until_gate(ctx)
    rel = ctx.data["p1.1.relevant"]
    assert rel and all(x["signal"] == "complaint" for x in rel)
    log = json.load(open(env / "decision_log.json"))
    summ = [e for e in log if e["action"] == "screen_summary"][0]
    assert summ["excluded_not_demand"]
    comp = open(env / "outputs" / "phase1_step3_comparison_d_a1.md").read()
    assert "Target region (Egypt)" in comp and "ASSUMPTION" in comp


def test_identical_excerpts_count_once():
    from agents.researcher import _same, _words
    a = _words("Need a vendor tracker for weddings, spreadsheets are a mess every single time")
    assert _same(a, _words("Need a vendor tracker for weddings, spreadsheets are a mess every single time!"))
    assert not _same(a, _words("How do I export a Notion database to CSV for my accountant"))


def test_hobby_repos_and_repeated_pain_points_do_not_count(env, fake_sources):
    from agents import opportunity_analyst as oa
    assert oa.HOBBY_REPO.search("https://github.com/x/sharkbyte_hackathon/issues/2")
    assert oa.HOBBY_REPO.search("https://github.com/x/habit-tracker-test/issues/1")
    assert not oa.HOBBY_REPO.search("https://github.com/monliu99/wedding-planner/issues/8")
    from conftest import FakeLLM

    def screen(system, user, schema, ids):
        return {"items": [{"source_id": i, "relevant": True, "pain_point": "Students need weekly streaks.",
                           "signal": "request"} for i in ids[:5]]}
    llm.set_fake(FakeLLM({"screen_evidence": screen}))
    b, _ = load_brief("r")
    ctx = orchestrator.new_run(b, "p")
    orchestrator.run_until_gate(ctx)
    assert len(ctx.data["p1.1.relevant"]) == 1           # the same pain point counts once


def test_place_without_a_cited_mention_is_labelled_everywhere():
    from agents import render_claim
    from run_context import RunContext
    ctx = RunContext(brief={"countries": "Egypt"}, label="z")
    ctx.sources["S001"] = {"url": "https://example.org/a", "excerpt": "I need a wedding checklist", "title": ""}
    out = render_claim(ctx, {"text": "Couples in Egypt need checklists", "source_ids": ["S001"]})
    assert "Egypt: ASSUMPTION" in out
    ctx.sources["S002"] = {"url": "https://example.org/b", "excerpt": "Weddings in Egypt are hard to plan", "title": ""}
    assert "ASSUMPTION" not in render_claim(ctx, {"text": "Couples in Egypt need checklists", "source_ids": ["S002"]})
