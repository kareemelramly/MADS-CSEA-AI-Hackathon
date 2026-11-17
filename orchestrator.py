"""Six-phase state machine (SRS 4.1, ADR-01). No LLM decides control flow.

`run_until_gate(ctx)` runs the next phase work until something needs the founder (a gate verdict,
an approval, an input form), the run stops, or the time budget is used. It returns a *pause*
dict. The founder answers with `respond(ctx, answer, founder_action)` from the UI (button) or the
CLI (typed), and `run_until_gate` continues. Every stage caches finished work in `ctx.data`, so a
resumed stage never repeats a model call, an output file or an approval.

CLI (headless stage tests and the committed demo runs):
    python -m orchestrator --brief tests/fixtures/brief_w.json --label w [--until-gate 1] [--log path]
"""
import argparse
import hashlib
import json
import os
import sys
import time

import approval
import config
import gates
import guardrails
import llm
import payments
import delivery
import refunds
import reconcile
from run_context import RunContext
from agents import (researcher, opportunity_analyst, interview_planner, strategist, landing_writer, validation_kit,
                    mvp_planner, builder, doc_writer, qa, packager, pricer, policy_drafter, launcher, analyst, support_agent,
                    persona_simulator)


class _Pause(Exception):
    def __init__(self, pause):
        self.pause = pause


def new_run(brief, label):
    ctx = RunContext(brief=dict(brief), label=label)
    ctx.data["original_idea"] = brief.get("idea")
    ctx.log("orchestrator", "start_run", label=ctx.label, brief_idea=brief.get("idea"))
    return ctx


def reset(ctx, *prefixes):
    """Forget cached work and founder answers of the given stages so they run again (pivot or retry)."""
    for store in (ctx.data, ctx.founder):
        for k in [k for k in store if k.startswith(prefixes)]:
            store.pop(k)


def once(ctx, key, fn):
    if key not in ctx.data:
        ctx.data[key] = fn()
    return ctx.data[key]


def need(ctx, pid, pause):
    """Return the founder's answer to pause `pid`, or pause the run to ask for it."""
    if pid in ctx.founder:
        return ctx.founder[pid]
    pause = {"id": pid, "run_id": ctx.run_id, **pause}
    raise _Pause(pause)


def write_gate(ctx, phase, g, title, handoff=None, name=None):
    name = name or f"phase{phase}_gate_decision"
    ctx.out(name, "md", gates.write_verdict(g, title))
    body = {"run_id": ctx.run_id, "gate": g.to_dict()}
    if handoff is not None:
        body["handoff"] = handoff
    ctx.out(name, "json", body)
    ctx.gates.append({"phase": phase, **g.to_dict()})
    ctx.log("gate", g.gate, outcome=g.outcome, numbers=g.numbers, reasons=g.reasons)


def gate_pause(ctx, phase, g, pid, extra_options=(), allow_override=True):
    opts = []
    if g.outcome == "go":
        opts.append("continue")
    if g.outcome == "repeat":
        opts.append("retry")
    if g.outcome == "pivot_back":
        opts.append("pivot")
    if g.outcome != "go" and g.overridable and allow_override:
        opts.append("override")
    opts += list(extra_options)
    opts.append("stop")
    return need(ctx, pid, {"kind": "gate", "phase": phase, "gate": g.to_dict(), "verdict": g.verdict, "options": opts})


def record_choice(ctx, phase, ans):
    ctx.log("founder", "gate_decision", approved_by="founder", phase=phase, choice=ans.get("choice"))


def finish(ctx, outcome, why):
    ctx.finished = True
    ctx.final_outcome = outcome
    ctx.stage = "done"
    ctx.log("orchestrator", "end_run", outcome=outcome, reason=why, system_time_s=round(ctx.system_time_s, 1))


def approval_step(ctx, pid, action, content, destination, effect):
    """Request (once), pause for the founder, then execute through the executor only."""
    aid = once(ctx, pid + ":aid", lambda: approval.request(action, content, destination, 0, "USD", ctx.run_id))
    ans = need(ctx, pid, {"kind": "approval", "approval_id": aid, "action": action, "content": content,
                          "destination": destination, "amount_minor": 0, "currency": "USD",
                          "content_sha256": approval.binding(action, content, destination, 0, "USD", ctx.run_id)[0]["content_sha256"],
                          "note": "Approving authorizes only this named internal action. Nothing is signed, paid or sent; publishing is STUBBED."})
    if ans.get("choice") != "approve":
        once(ctx, pid + ":rejected", lambda: ctx.log("orchestrator", "action_not_executed", requested_action=action, reason="founder rejected"))
        return None
    return once(ctx, pid + ":done", lambda: approval.execute(aid, action, content, destination, 0, "USD", ctx.run_id, effect))


# ====================================================================== Phase 1
def phase1(ctx, prog):
    att = ctx.data.setdefault("p1_attempt", 1)
    k = f"p1.{att}."
    r = once(ctx, k + "research", lambda: researcher.run(ctx))
    ctx.data["p1_thresholds"] = r["thresholds"]
    th = r["thresholds"]
    if r.get("excluded") or r.get("missing"):
        g = gates.discover_gate(missing_fields=r.get("missing"), excluded=r.get("excluded"), values_conflict=None,
                                coverage={"sources_ok": 0, "items_screened": 0, "failed": [], "retry_used": False},
                                relevant={"count": 0, "sources": []}, fit=0, alternatives=[], thresholds=th)
        once(ctx, k + "gate_written", lambda: write_gate(ctx, 1, g, "Phase 1 gate: Discover") or True)
        if g.outcome == "stop":
            finish(ctx, "stop", g.verdict)
            return
        ans = gate_pause(ctx, 1, g, f"p1.{att}.gate", allow_override=False)
        return _p1_answer(ctx, g, ans, None)
    cov = r["coverage"]
    thin = cov["sources_ok"] < th["min_sources_ok"] or cov["items_screened"] < th["min_items_screened"]
    relevant = [] if thin else once(ctx, k + "relevant", lambda: opportunity_analyst.screen(ctx, r["to_screen"], prog))
    scored = None if thin else once(ctx, k + "score", lambda: opportunity_analyst.score(ctx, relevant, prog))
    idea = scored["idea"] if scored else {"fit": 0, "values": {"score": 3}}
    values_conflict = "values fit rated 1 of 5" if scored and idea["values"]["score"] == 1 else None
    g = gates.discover_gate(missing_fields=[], excluded=None, values_conflict=values_conflict, coverage=cov,
                            relevant={"count": len(relevant), "sources": [x["source"] for x in relevant]},
                            fit=idea["fit"], alternatives=(scored or {}).get("alternatives", []), thresholds=th)
    questions = None
    if g.outcome in ("go", "pivot_back") and scored:
        questions = once(ctx, k + "interview", lambda: interview_planner.run(ctx, scored["segment"]["text"], prog))

    def outputs():
        _p1_outputs(ctx, r, relevant, scored, questions, g)
        return True
    once(ctx, k + "outputs", outputs)
    if g.outcome == "stop" and not g.overridable:
        finish(ctx, "stop", g.verdict)
        return
    ans = gate_pause(ctx, 1, g, f"p1.{att}.gate", allow_override=scored is not None)
    return _p1_answer(ctx, g, ans, scored)


def _p1_answer(ctx, g, ans, scored):
    once(ctx, f"p1.{ctx.data['p1_attempt']}.choice", lambda: record_choice(ctx, 1, ans) or True)
    c = ans.get("choice")
    if c == "stop":
        return finish(ctx, g.outcome if g.outcome != "go" else "stop", "founder chose stop at Phase 1")
    if c == "retry":
        ctx.data["p1_attempt"] += 1
        return
    if c == "pivot" and scored:
        if ctx.data.get("p1_pivots", 0) >= 2:
            return finish(ctx, "stop", "pivot limit (2) reached")
        alt = scored["alternatives"][0]
        ctx.data["p1_pivots"] = ctx.data.get("p1_pivots", 0) + 1
        ctx.brief["idea"] = f"{alt['name']}: {alt['description']}"
        ctx.brief.pop("search_terms", None)
        ctx.log("orchestrator", "pivot_back", from_phase=1, to_phase=1, new_idea=alt["name"], approved_by="founder")
        ctx.data["p1_attempt"] += 1
        return
    if c == "override":
        approval.override(ctx, 1, g.outcome, ans.get("reason", ""))
    if c in ("continue", "override"):
        if not scored:
            return finish(ctx, "stop", "no scored idea to continue with")
        ctx.handoffs["H1"] = _h1(ctx, scored, g)
        ctx.stage = "p2"


def _h1(ctx, scored, g):
    rel = ctx.data.get(f"p1.{ctx.data['p1_attempt']}.relevant", [])
    return {"idea_name": scored["idea"]["name"], "idea_description": scored["idea"]["description"],
            "segment": scored["segment"]["text"], "fit": scored["idea"]["fit"], "evidence": rel,
            "alternatives": [{"name": a["name"], "description": a["description"], "fit": a["fit"]} for a in scored["alternatives"]],
            "gate_outcome": g.outcome, "gate_ref": ctx.ref("phase1_gate_decision", "json")}


def _p1_outputs(ctx, r, relevant, scored, questions, g):
    from agents import render_claim
    cov = r["coverage"]
    lines = ["# Phase 1 · Step 1 · Opportunities (pain points found)", "",
             f"Query: `{cov['query']}` · sources answered: {cov['sources_ok']} · items screened: {cov['items_screened']} · "
             f"broadened retry used: {cov['retry_used']} · failed: {', '.join(cov['failed']) or 'none'}", ""]
    if relevant:
        for x in relevant:
            lines.append(f"- {render_claim(ctx, {'text': x['pain_point'], 'source_ids': [x['source_id']]})}")
    else:
        lines.append("- No relevant pain points were found in the screened items. This is a statement about the search, not about the market.")
    ctx.out("phase1_step1_opportunities", "md", "\n".join(lines) + "\n")
    ctx.out("phase1_step2_evidence", "json", {"run_id": ctx.run_id, "coverage": cov, "registry": list(ctx.sources.values()),
                                               "relevant": relevant, "note": "Source IDs are assigned by code; excerpts are untrusted data."})
    if scored:
        rows = ["# Phase 1 · Step 3 · Idea vs alternatives", "",
                f"**Segment:** {render_claim(ctx, scored['segment'])}", "",
                f"**Market:** {render_claim(ctx, scored['market_note'])} Market size is unknown unless a source above states it.", "",
                "Fit is weighted in code: skills 35 %, budget 25 %, time 25 %, values 15 % (weights are an ASSUMPTION).", "",
                "| Option | Skills | Budget | Time | Values | Weighted fit (1-5) | Cites relevant evidence |", "|---|---|---|---|---|---|---|"]
        for o in [scored["idea"]] + scored["alternatives"]:
            rows.append(f"| {o['name']} | {o['skills']['score']} | {o['budget']['score']} | {o['time']['score']} | {o['values']['score']} | {o['fit']} | {len(o['cited_relevant'])} |")
        rows += ["", "## Reasons", ""]
        for o in [scored["idea"]] + scored["alternatives"]:
            rows.append(f"**{o['name']}**: {o['description']}")
            for kk in ("skills", "budget", "time", "values"):
                rows.append(f"- {kk}: {o[kk]['reason']}")
            rows.append("")
        ctx.out("phase1_step3_comparison", "md", "\n".join(rows) + "\n")
    if questions:
        qs, dropped = questions
        body = ["# Phase 1 · Step 4 · Interview script (Mom Test)", "",
                "Ask about past behaviour only. No answers are invented; record real answers yourself.", ""]
        body += [f"{i}. {q['question']}  \n   _Why:_ {q['why']}" for i, q in enumerate(qs, 1)]
        body += ["", f"Hypothetical or leading questions removed by code: {dropped}."]
        ctx.out("phase1_step4_interview_script", "md", "\n".join(body) + "\n")
    write_gate(ctx, 1, g, "Phase 1 gate: Discover (coverage, evidence, fit)",
               handoff={"idea": scored["idea"]["name"] if scored else ctx.brief.get("idea"),
                        "alternatives": [a["name"] for a in (scored or {}).get("alternatives", [])],
                        "evidence_ids": [x["source_id"] for x in relevant]})


# ====================================================================== Phase 2
def phase2(ctx, prog):
    att = ctx.data.setdefault("p2_attempt", 1)
    canvas = once(ctx, "p2.canvas", lambda: strategist.canvas(ctx, prog))
    plan, lock = once(ctx, "p2.plan", lambda: strategist.plan_and_lock(ctx))
    try:
        copy = once(ctx, f"p2.{att}.landing", lambda: landing_writer.run(ctx, canvas, prog))
    except landing_writer.GuardrailBlocked as e:
        g = gates.GateResult("phase2_gate", "repeat", f"The landing page draft was refused by guardrails ({e}). Nothing was published.",
                             ["guardrail_refusal"], {}, overridable=False)
        once(ctx, f"p2.{att}.blocked", lambda: write_gate(ctx, 2, g, "Phase 2 gate: landing page refused") or True)
        ans = gate_pause(ctx, 2, g, f"p2.{att}.blocked_gate")
        if ans.get("choice") == "retry":
            ctx.data["p2_attempt"] = att + 1
            return
        return finish(ctx, "stop", "founder stopped after guardrail refusal")
    html = once(ctx, f"p2.{att}.html", lambda: landing_writer.render(ctx, copy))

    def outs():
        from agents import render_claim
        lines = ["# Phase 2 · Step 1 · Lean Canvas", "", "Every box cites source IDs or is labelled ASSUMPTION.", ""]
        for b in strategist.BOXES:
            lines += [f"## {b.replace('_', ' ').title()}", "", render_claim(ctx, canvas[b]), ""]
        ctx.out("phase2_step1_lean_canvas", "md", "\n".join(lines))
        ctx.out("phase2_step2_locked_plan", "json", {"plan": plan, "lock": lock})
        ctx.out("phase2_step3_landing_page", "html", html)
        return True
    once(ctx, f"p2.{att}.outs", outs)
    approval_step(ctx, f"p2.{att}.publish", "publish_landing_page", html, "none: publishing is STUBBED",
                  lambda: approval.publish_stub(ctx.run_id, "publish_landing_page", "none: publishing is STUBBED",
                                                hashlib.sha256(html.encode()).hexdigest()))

    ps = need(ctx, f"p2.{att}.persona", {"kind": "input", "phase": 2, "form": "persona_test",
                                         "help": "Optional: run a SIMULATED persona stress test of the page (1 model call). Its numbers never count as sign-ups."})
    if ps.get("run"):
        personas = once(ctx, f"p2.{att}.personas", lambda: persona_simulator.run(ctx, copy, prog))

        def pout():
            md, n = persona_simulator.report_md(personas)
            ctx.out("phase2_step4_persona_stress_test", "md", md)
            ctx.data["p2_simulated_joins"] = n
            return True
        once(ctx, f"p2.{att}.personas_out", pout)

    def kit():
        ctx.out("phase2_step6_experiment_plan", "md", validation_kit.plan_md(ctx, plan, lock))
        ctx.out("phase2_step6_tracking", "csv", validation_kit.tracking_csv(plan))
        ctx.out("phase2_step6_results_form", "json", validation_kit.results_form())
        return True
    once(ctx, "p2.kit", kit)
    rnd = ctx.data.setdefault("p2_round", 1)
    counts = need(ctx, f"p2.counts.{rnd}", {"kind": "input", "phase": 2, "form": "real_counts",
                                            "fields": validation_kit.results_form(),
                                            "help": "Enter REAL results only. Default: not_started (the gate will wait; nothing is decided)."})
    counts = _clean_counts(counts)
    if ctx.data.get("p2_simulated_joins") is not None:
        counts["simulated_signups"] = ctx.data["p2_simulated_joins"]
    once(ctx, f"p2.counts_logged.{rnd}", lambda: ctx.log("founder", "enter_real_counts", approved_by="founder", counts=counts) or True)
    alts_left = len(ctx.handoffs["H1"].get("alternatives", [])) > ctx.data.get("p1_pivots", 0)
    g = gates.validate_gate(plan=plan, lock=lock, counts=counts, attempt=ctx.data.get("p2_quality_attempt", 1),
                            max_attempts=config.validate_max_attempts(), alternatives_left=alts_left, floor=config.validate_repeat_floor())
    h2 = {**{k: counts.get(k) for k in ("experiment_status", "started_at", "ended_at", "visitors", "signups")},
          "attempt": ctx.data.get("p2_quality_attempt", 1), "min_visitors": plan["min_visitors"],
          "value_proposition": canvas["unique_value_proposition"]["text"],
          "validation_status": "VALIDATED" if g.outcome == "go" else ("AWAITING_EVIDENCE" if g.outcome == gates.PAUSE else "NOT_VALIDATED"),
          "landing_ref": ctx.ref("phase2_step3_landing_page"), "plan_ref": ctx.ref("phase2_step2_locked_plan")}
    once(ctx, f"p2.gate.{rnd}", lambda: write_gate(ctx, 2, g, "Phase 2 gate: demand (locked target vs real results)", handoff=h2) or True)
    ctx.handoffs["H2"] = h2
    extra = ("enter_results",) if g.outcome in (gates.PAUSE, "repeat") else ()
    ans = gate_pause(ctx, 2, g, f"p2.answer.{rnd}", extra_options=extra)
    once(ctx, f"p2.choice.{rnd}", lambda: record_choice(ctx, 2, ans) or True)
    c = ans.get("choice")
    if c == "stop":
        return finish(ctx, g.outcome if g.outcome in gates.OUTCOMES else "awaiting_evidence", "founder chose stop at Phase 2")
    if c in ("retry", "enter_results"):
        if "near_miss" in g.reasons:
            ctx.data["p2_quality_attempt"] = ctx.data.get("p2_quality_attempt", 1) + 1
        ctx.data["p2_round"] = rnd + 1
        return
    if c == "pivot":
        alts = ctx.handoffs["H1"]["alternatives"]
        alt = alts[min(ctx.data.get("p1_pivots", 0), len(alts) - 1)]
        ctx.data["p1_pivots"] = ctx.data.get("p1_pivots", 0) + 1
        ctx.data["p1_attempt"] = ctx.data.get("p1_attempt", 1) + 1
        ctx.brief["idea"] = f"{alt['name']}: {alt['description']}"
        ctx.brief.pop("search_terms", None)
        for k in [k for k in ctx.data if k.startswith("p2")]:
            ctx.data.pop(k)
        ctx.log("orchestrator", "pivot_back", from_phase=2, to_phase=1, new_idea=alt["name"], approved_by="founder")
        ctx.stage = "p1"
        return
    if c == "override":
        approval.override(ctx, 2, g.outcome, ans.get("reason", ""))
        ctx.handoffs["H2"]["validation_status"] = "UNVALIDATED_FOUNDER_OVERRIDE"
        ctx.stage = "p3"
        return
    if c == "continue":
        ctx.validation_status = "VALIDATED"
        ctx.stage = "p3"


def _clean_counts(c):
    st = c.get("experiment_status", "not_started")
    if st not in ("not_started", "running", "completed", "abandoned"):
        st = "not_started"
    vis = c.get("visitors")
    return {"experiment_status": st, "started_at": c.get("started_at"), "ended_at": c.get("ended_at"),
            "visitors": int(vis) if vis not in (None, "") else None, "signups": int(c.get("signups") or 0),
            "simulated_signups": c.get("simulated_signups")}


# ====================================================================== Phase 3
P3_FILES = [("checklist", "phase3_step3_product_checklist", "md"), ("tracker", "phase3_step3_product_tracker", "csv"),
            ("license", "phase3_step3_product_license", "txt"), ("docs", "phase3_step4_user_docs", "md")]


def phase3(ctx, prog):
    h2 = ctx.handoffs.get("H2", {})
    if h2.get("validation_status") == "VALIDATED":
        mode = "mvp"
    elif ctx.validation_status == "UNVALIDATED_FOUNDER_OVERRIDE":
        mode = "minimal"
    else:
        ctx.log("orchestrator", "skip_phase", phase=3, reason="awaiting evidence" if h2.get("validation_status") == "AWAITING_EVIDENCE" else "phase 2 not go")
        return finish(ctx, "awaiting_evidence", "Phase 3 needs Phase 2 go or a founder override")
    plan = once(ctx, "p3.plan", lambda: mvp_planner.run(ctx, mode, prog))
    once(ctx, "p3.plan_out", lambda: ctx.out("phase3_step1_mvp_definition", "md", _plan_md(plan)) and True)
    while True:
        a = ctx.data.setdefault("p3_attempt", 1)
        slots = once(ctx, f"p3.{a}.slots", lambda: builder.fill(ctx, plan, ctx.data.get("p3_feedback"), prog, a))
        if f"p3.{a}.files" not in ctx.data:
            rendered = builder.render(ctx, plan, slots)
            files = {}
            for role, name, ext in P3_FILES[:3]:
                rec = ctx.out(name, ext, rendered[role])
                files[role] = {"path": rec["path"], "text": open(os.path.join(os.path.dirname(config.outputs_dir()), rec["path"]), encoding="utf-8").read()}
            ctx.data[f"p3.{a}.partial"] = files
            docs = doc_writer.run(ctx, plan, files["checklist"]["path"], prog, a)
            rec = ctx.out("phase3_step4_user_docs", "md", docs)
            files["docs"] = {"path": rec["path"], "text": open(os.path.join(os.path.dirname(config.outputs_dir()), rec["path"]), encoding="utf-8").read()}
            ctx.data[f"p3.{a}.files"] = files
        files = ctx.data[f"p3.{a}.files"]
        res = once(ctx, f"p3.{a}.qa", lambda: qa.run(ctx, plan, files))
        once(ctx, f"p3.{a}.qa_log", lambda: ctx.log("qa", "run_checks", passed=sum(c["status"] == "pass" for c in res),
                                                     failed=[c["id"] for c in res if c["status"] == "fail"], attempt=a) or True)
        once(ctx, f"p3.{a}.report", lambda: ctx.out("phase3_step5_test_report", "md", qa.report_md(plan, res, a)) and True)
        g = gates.build_gate(qa=res, attempt=a, max_attempts=config.max_build_attempts(), rescope_left=ctx.data.get("p3_pivots", 0) < 1)
        if g.outcome == "repeat":
            once(ctx, f"p3.{a}.gate", lambda: write_gate(ctx, 3, g, f"Phase 3 test gate (attempt {a})") or True)
            ctx.data["p3_feedback"] = [f"{c['id']} {c['name']}: {c['evidence']}" for c in res if c["status"] == "fail"]
            ctx.data["p3_attempt"] = a + 1
            continue
        once(ctx, f"p3.{a}.gate", lambda: write_gate(ctx, 3, g, f"Phase 3 test gate (attempt {a})") or True)
        if g.outcome == "stop":
            return finish(ctx, "stop", g.verdict)
        if g.outcome == "pivot_back":
            ans = gate_pause(ctx, 3, g, f"p3.{a}.rescope")
            once(ctx, f"p3.{a}.rescope_choice", lambda: record_choice(ctx, 3, ans) or True)
            if ans.get("choice") != "pivot":
                return finish(ctx, "stop", "founder stopped after failed build checks")
            n = ctx.data.get("p3_pivots", 0) + 1
            ctx.log("orchestrator", "pivot_back", from_phase=3, to_phase=3, step="3.1 re-plan MVP", approved_by="founder")
            reset(ctx, "p3")
            ctx.data["p3_pivots"] = n
            return
        break
    man, man_json = once(ctx, "p3.manifest", lambda: packager.manifest(ctx, [{"role": r, "name": n, "ext": e} for r, n, e in P3_FILES]))
    rel = approval_step(ctx, "p3.release", "release_product", man_json, "none: STUBBED (internal release to Phase 4)",
                        lambda: {"released": True, "status": "internal release; nothing published"})
    if not rel:
        return finish(ctx, "repeat", "founder rejected the release; nothing released")
    h3 = {"manifest": man, "manifest_sha256": approval.binding("release_product", man_json, "", 0, "USD", ctx.run_id)[0]["content_sha256"],
          "build_mode": mode, "validation_status": ctx.validation_status, "product_type": "checklist", "archetype": "A1",
          "test_report_ref": ctx.ref("phase3_step5_test_report")}
    once(ctx, "p3.h3", lambda: ctx.out("phase3_step6_handoff", "json", h3) and True)
    ctx.handoffs["H3"] = h3
    ctx.stage = "p4"


def _plan_md(plan):
    lines = ["# Phase 3 · Step 1 · MVP definition (archetype A1 checklist pack)", "", f"**Mode:** {plan['mode']}", "",
             f"**User story:** {plan['user_story']}", "", "## Must features", ""]
    lines += [f"- {f['name']}: {f['description']} (evidence: {', '.join(f['source_ids'])})" for f in plan["must_features"]]
    lines += ["", "## Acceptance criteria", ""] + [f"{i}. Given {c['given']}, when {c['when']}, then {c['then']}" for i, c in enumerate(plan["acceptance_criteria"], 1)]
    lines += ["", "## Journey", ""] + [f"J{i}. {s}" for i, s in enumerate(plan["journey"], 1)]
    lines += ["", "## Mocked integrations", ""] + [f"- {m}" for m in plan["mocked"]]
    lines += ["", "## Traceability", "", "| Feature | Evidence | Criteria | Checks |", "|---|---|---|---|"]
    lines += [f"| {m['feature']} | {', '.join(m['evidence'])} | {m['criteria']} | {', '.join(m['checks'])} |" for m in plan["matrix"]]
    return "\n".join(lines) + "\n"


# ====================================================================== Phase 4
def phase4(ctx, prog):
    att = ctx.data.setdefault("p4_attempt", 1)
    quotes = need(ctx, f"p4.{att}.quotes", {"kind": "input", "phase": 4, "form": "price_quotes",
                                            "help": "Enter at least 3 competitor products with URL, price, currency and kind (one_time | subscription | free). Each URL is fetched; a URL that does not load is not counted."})
    once(ctx, f"p4.{att}.quotes_logged", lambda: ctx.log("founder", "enter_price_quotes", approved_by="founder", count=len(quotes.get("quotes", []))) or True)
    pr = once(ctx, f"p4.{att}.price", lambda: pricer.run(ctx, quotes.get("quotes", [])))
    price, currency, basis = pr["price"], pr["currency"] or "USD", "median of sourced competitor prices"
    if price is None:
        g = gates.commercial_gate(quotes_ok=pr["paid_quotes"], price=None, policies_missing=[], overridden_price=False)
        once(ctx, f"p4.{att}.gate_thin", lambda: write_gate(ctx, 4, g, "Phase 4 gate: price evidence") or True)
        ans = gate_pause(ctx, 4, g, f"p4.{att}.thin")
        once(ctx, f"p4.{att}.thin_choice", lambda: record_choice(ctx, 4, ans) or True)
        if ans.get("choice") == "retry":
            ctx.data["p4_attempt"] = att + 1
            return
        if ans.get("choice") != "override":
            return finish(ctx, "repeat", "no price evidence; founder stopped")
        approval.override(ctx, 4, "repeat", ans.get("reason", ""))
        price, currency, basis = float(ans.get("experimental_price") or 0), ans.get("currency", "USD"), "ASSUMPTION: experimental price set by founder override"
        if price <= 0:
            return finish(ctx, "repeat", "experimental price missing")
    docs, missing = once(ctx, "p4.policies", lambda: policy_drafter.run(ctx, price, currency, prog))

    def outs():
        rows = ["# Phase 4 · Step 1 · Price", "", f"**Price:** {price} {currency} one-time · basis: {basis}", "",
                "| Competitor | URL | Amount | Currency | Kind | Page loaded | Price text on page | Counted |", "|---|---|---|---|---|---|---|---|"]
        for r in pr["rows"]:
            counted = bool(r["registered"]) and r["kind"] == "one_time" and r["currency"] == pr["currency"]
            rows.append(f"| {r['name']} | {r['url']} | {r['amount']} | {r['currency']} | {r['kind']} | {r['http_status'] == 200} | {r['price_text_on_page']} | {counted} |")
        rows += ["", "Prices are founder-entered quotes; a quote counts only if its page loaded (registered as a source). No payment of any kind is set up."]
        ctx.out("phase4_step1_pricing", "md", "\n".join(rows) + "\n")
        for key in ("terms", "privacy", "refund", "delivery"):
            ctx.out(f"phase4_step2_policy_{key}", "md", docs[key])
        return True
    once(ctx, "p4.outs", outs)
    g = gates.commercial_gate(quotes_ok=pr["paid_quotes"], price=price, policies_missing=missing, overridden_price=basis.startswith("ASSUMPTION"))
    once(ctx, "p4.gate", lambda: write_gate(ctx, 4, g, "Phase 4 gate: price and DRAFT policies") or True)
    if g.outcome != "go":
        ans = gate_pause(ctx, 4, g, "p4.gate_answer")
        return finish(ctx, g.outcome, "commercial gate not passed")
    content = json.dumps({"price": price, "currency": currency, "basis": basis, "policies": {k: v for k, v in docs.items()}}, sort_keys=True)
    ok = approval_step(ctx, "p4.commercial", "commercial_setup", content, "none: STUBBED (internal hand-off to Phase 5; nothing signed)",
                       lambda: {"handoff": "H4 released internally", "signed": False})
    if not ok:
        g = gates.commercial_rejected_gate(price=price, currency=currency)
        once(ctx, "p4.rejected_gate", lambda: write_gate(ctx, 4, g, "Phase 4 gate: offer rejected by the founder") or True)
        ans = gate_pause(ctx, 4, g, "p4.rejected_answer", extra_options=("retry",))
        once(ctx, "p4.rejected_choice", lambda: record_choice(ctx, 4, ans) or True)
        c = ans.get("choice")
        if c == "retry":
            reset(ctx, "p4")
            return
        if c == "pivot" and ctx.data.get("p4_pivots", 0) < 1:
            n = ctx.data.get("p4_pivots", 0) + 1
            ctx.log("orchestrator", "pivot_back", from_phase=4, to_phase=3, approved_by="founder")
            reset(ctx, "p3", "p4")
            ctx.data["p4_pivots"] = n
            ctx.stage = "p3"
            return
        return finish(ctx, "stop", "founder stopped after rejecting the commercial setup")
    h4 = {"price": price, "currency": currency, "price_basis": basis, "policies": {k: ctx.ref(f"phase4_step2_policy_{k}") for k in docs},
          "policy_status": "DRAFT · FOUNDER REVIEW REQUIRED · Not legal advice", "payments": "none: MOCKED ledger only"}
    once(ctx, "p4.h4", lambda: ctx.out("phase4_step3_handoff", "json", h4) and True)
    ctx.handoffs["H4"] = h4
    ctx.stage = "p5"


# ====================================================================== Phase 5
def phase5(ctx, prog):
    try:
        page = once(ctx, "p5.store", lambda: launcher.store_page(ctx, prog))
        post = once(ctx, "p5.post", lambda: launcher.launch_post(ctx, prog))
    except launcher.Blocked as e:
        g = gates.GateResult("phase5_gate", "repeat", f"Launch copy refused by guardrails ({e}); nothing published.", ["guardrail_refusal"], {}, overridable=False)
        once(ctx, "p5.blocked", lambda: write_gate(ctx, 5, g, "Phase 5 gate: launch copy refused", name="phase5_gate_launch") or True)
        return finish(ctx, "repeat", str(e))
    once(ctx, "p5.outs", lambda: (ctx.out("phase5_step1_store_page", "md", page), ctx.out("phase5_step2_launch_post", "md", post)) and True)
    s_ok = approval_step(ctx, "p5.store_appr", "publish_store_page", page, "none: store publishing is STUBBED",
                         lambda: approval.publish_stub(ctx.run_id, "publish_store_page", "none: store publishing is STUBBED", "store"))
    p_ok = approval_step(ctx, "p5.post_appr", "post_launch_message", post, "none: social posting is STUBBED",
                         lambda: approval.publish_stub(ctx.run_id, "post_launch_message", "none: social posting is STUBBED", "post"))
    sim = need(ctx, "p5.mock_sale", {"kind": "input", "phase": 5, "form": "mock_sale",
                                     "help": "Simulate one purchase (MOCKED local event: no payment of any kind runs). Optionally simulate a refund."})
    res = once(ctx, "p5.ledger", lambda: _mock_sale(ctx, sim))
    once(ctx, "p5.sale_out", lambda: ctx.out("phase5_step3_mock_sale", "md", _sale_md(res)) and True)
    g = gates.launch_gate(store_approved=bool(s_ok), post_approved=bool(p_ok), mock_ok=res["ok"], offer_left=ctx.data.get("p5_pivots", 0) < 1)
    if g.outcome == "pivot_back":
        once(ctx, "p5.rejected_gate", lambda: write_gate(ctx, 5, g, "Phase 5 launch gate: drafts rejected", name="phase5_gate_launch") or True)
        ans = gate_pause(ctx, 5, g, "p5.rejected_answer", extra_options=("retry",))
        once(ctx, "p5.rejected_choice", lambda: record_choice(ctx, 5, ans) or True)
        c = ans.get("choice")
        n = ctx.data.get("p5_pivots", 0) + 1
        if c == "retry":
            reset(ctx, "p5")
            ctx.data["p5_pivots"] = n
            return
        if c == "pivot":
            ctx.log("orchestrator", "pivot_back", from_phase=5, to_phase=4, approved_by="founder")
            reset(ctx, "p4", "p5")
            ctx.data["p5_pivots"] = n
            ctx.stage = "p4"
            return
        return finish(ctx, "stop", "founder stopped after rejecting the launch drafts")
    h5 = {"launch": "mock run only", "store_page_ref": ctx.ref("phase5_step1_store_page"), "post_ref": ctx.ref("phase5_step2_launch_post"),
          "ledger_summary": res.get("reconcile", {}), "store_approved": bool(s_ok), "post_approved": bool(p_ok),
          "validation_status": ctx.validation_status}
    once(ctx, "p5.gate", lambda: write_gate(ctx, 5, g, "Phase 5 launch gate (mock run only)", handoff=h5, name="phase5_gate_launch") or True)
    ctx.handoffs["H5"] = h5
    ctx.stage = "p6"


def _mock_sale(ctx, sim):
    out = {"ok": True, "lines": []}
    if not sim.get("simulate_purchase"):
        out["lines"].append("MOCKED · no purchase simulated by the founder")
        out["reconcile"] = {}
        return out
    rnd = ctx.data.get("p5_pivots", 0)
    con = payments.connect(os.path.join(config.state_dir(), f"ledger-{ctx.run_id}-{rnd}.sqlite"))
    man = ctx.handoffs["H3"]["manifest"]
    root = os.path.dirname(config.outputs_dir())
    blobs = [open(os.path.join(root, f["path"]), "rb").read() for f in man["files"]]
    pkg = delivery.package_hash(blobs)
    amount = int(round(float(ctx.handoffs["H4"]["price"]) * 100))
    ev = {"event_id": f"evt_{ctx.run_id}_1", "order_id": f"ord_{ctx.run_id}_1", "product_id": man["product"], "amount_minor": amount,
          "currency": ctx.handoffs["H4"]["currency"]}
    r1 = payments.handle_mock_payment(con, ev, pkg, run_id=ctx.run_id)
    out["lines"].append(f"MOCKED · payment event {ev['event_id']} → order {r1['order_id']} status {r1['status']}, fee {r1['fee_minor']} minor units")
    ok_hash = delivery.verify_product(blobs, pkg)
    out["lines"].append(f"MOCKED · product files re-hashed before grant: {'match' if ok_hash else 'MISMATCH'}")
    d1 = delivery.download(con, r1["token"], run_id=ctx.run_id)
    out["lines"].append(f"MOCKED · download with token → allowed={d1['allowed']}")
    r2 = payments.handle_mock_payment(con, ev, pkg, run_id=ctx.run_id)
    out["lines"].append(f"MOCKED · same event replayed → duplicate={r2.get('duplicate', False)}, no second entitlement")
    if sim.get("simulate_refund"):
        rf = refunds.handle_mock_refund(con, {"event_id": f"evt_{ctx.run_id}_rf", "order_id": ev["order_id"]}, run_id=ctx.run_id)
        d2 = delivery.download(con, r1["token"], run_id=ctx.run_id)
        out["lines"].append(f"MOCKED · refund → {rf['status']}; download afterwards allowed={d2['allowed']} ({d2.get('reason')})")
        out["ok"] &= not d2["allowed"]
    rec = reconcile.reconcile(con, run_id=ctx.run_id, currency=ev["currency"])
    out["lines"].append(f"MOCKED · reconcile: gross {rec['gross_minor']}, fees {rec['fees_minor']}, refunds {rec['refunds_minor']}, net {rec['net_minor']}; "
                        f"matched={rec['matched']}; payout {rec['payout_batch']} {rec['payout_status']}")
    out["ok"] &= d1["allowed"] and r2.get("duplicate", False) and rec["matched"] and ok_hash
    out["reconcile"] = {k: rec[k] for k in ("orders", "gross_minor", "fees_minor", "refunds", "refunds_minor", "net_minor")}
    con.close()
    return out


def _sale_md(res):
    return "# Phase 5 · Step 3 · Sale to cash (MOCKED)\n\nNo payment of any kind runs: these are local mock events.\n\n" + \
        "\n".join(f"- {l}" for l in res["lines"]) + "\n"


# ====================================================================== Phase 6
def phase6(ctx, prog):
    tg = need(ctx, "p6.targets", {"kind": "input", "phase": 6, "form": "targets",
                                  "help": "Set Phase 6 targets BEFORE entering any metric. They cannot change afterwards."})
    targets = {k: float(v) for k, v in (tg.get("targets") or {}).items()}
    once(ctx, "p6.targets_logged", lambda: ctx.log("founder", "set_phase6_targets", approved_by="founder", targets=targets) or True)
    mt = need(ctx, "p6.metrics", {"kind": "input", "phase": 6, "form": "metrics",
                                  "help": "Enter REAL post-launch metrics with an evidence link each, or leave empty. Values without a link are treated as SIMULATED."})
    rows = analyst.metrics(ctx, ctx.handoffs.get("H5", {}).get("ledger_summary", {}), mt.get("metrics", []))
    docs_ref = ctx.final("phase3_step4_user_docs", "md")
    docs_txt = open(os.path.join(os.path.dirname(config.outputs_dir()), docs_ref["path"]), encoding="utf-8").read() if docs_ref else ""
    items = once(ctx, "p6.faq", lambda: support_agent.faq(ctx, docs_txt, prog))
    once(ctx, "p6.faq_out", lambda: ctx.out("phase6_step2_support_faq", "md", support_agent.faq_md(items)) and True)
    h2 = ctx.handoffs.get("H2", {})
    alt_left = len(ctx.handoffs.get("H1", {}).get("alternatives", [])) > ctx.data.get("p1_pivots", 0)
    g = gates.operate_gate(targets=targets, metrics=rows, phase2_completed=h2.get("experiment_status") == "completed", alternative_left=alt_left)
    once(ctx, "p6.memo", lambda: ctx.out("phase6_step1_memo", "md", analyst.memo(ctx, rows, g, targets)) and True)
    once(ctx, "p6.gate_log", lambda: ctx.log("gate", g.gate, outcome=g.outcome, numbers=g.numbers, reasons=g.reasons) or True)
    ans = need(ctx, "p6.decision", {"kind": "gate", "phase": 6, "gate": g.to_dict(), "verdict": g.verdict,
                                    "options": ["persevere", "pivot", "stop"],
                                    "help": "Your decision is logged with approved_by: founder. If it differs from the recommendation, both are kept."})
    dec = {"choice": ans.get("choice")}
    once(ctx, "p6.decision_logged", lambda: ctx.log("founder", "phase6_decision", approved_by="founder", choice=dec["choice"],
                                                    recommendation=g.outcome) or True)
    once(ctx, "p6.gate_out", lambda: ctx.out("phase6_gate_decision", "md", gates.write_verdict(g, "Phase 6 gate: persevere or pivot") +
                                             f"\n## Founder decision\n\n**{dec['choice']}** (recommendation: `{g.outcome}`; both kept).\n") and True)
    finish(ctx, {"persevere": "go", "pivot": "pivot_back", "stop": "stop"}.get(dec["choice"], "stop"), "Phase 6 decision recorded")


PHASES = {"p1": phase1, "p2": phase2, "p3": phase3, "p4": phase4, "p5": phase5, "p6": phase6}


# ====================================================================== driver
def run_until_gate(ctx, on_progress=None, clock=time.monotonic):
    if ctx.finished:
        return {"id": "done", "kind": "done", "outcome": ctx.final_outcome}
    ctx.start_segment(clock)
    try:
        while not ctx.finished:
            stage = ctx.stage
            try:
                PHASES[stage](ctx, on_progress)
            except _Pause as p:
                ctx.data["pause"] = p.pause
                ctx.model_errors.pop(stage, None)
                return p.pause
            except llm.ModelError as e:
                n = ctx.model_errors.get(stage, 0) + 1
                ctx.model_errors[stage] = n
                why = "time budget used; nothing decided" if e.kind == "budget" else "model unavailable; nothing decided"
                ctx.log("orchestrator", "phase_repeat", phase=stage, outcome="repeat", reason=e.kind, detail=e.reasons[-4:])
                pause = {"id": f"err.{stage}.{n}", "kind": "error", "phase": int(stage[1]), "outcome": "repeat",
                         "verdict": f"{why}. " + " · ".join(e.reasons[-4:]), "options": ["try_again", "stop"],
                         "consecutive_errors": n}
                ctx.data["pause"] = pause
                return pause
    finally:
        ctx.end_segment(clock)
        ctx.save()
    return {"id": "done", "kind": "done", "outcome": ctx.final_outcome}


def respond(ctx, answer, founder_action):
    """Store the founder's answer to the current pause. `founder_action` is 'button' (UI) or 'typed' (CLI)."""
    if founder_action not in ("button", "typed"):
        raise approval.ApprovalError("founder answers need an explicit founder action")
    pause = ctx.data.get("pause")
    if not pause:
        return
    if pause["kind"] == "error":
        if answer.get("choice") == "stop":
            finish(ctx, "repeat", "founder stopped after a model error; nothing decided")
        ctx.data.pop("pause", None)
        return
    if pause["kind"] == "approval":
        if answer.get("choice") == "approve":
            approval.approve(pause["approval_id"], founder_action=founder_action)
        else:
            approval.reject(pause["approval_id"], founder_action=founder_action)
    if pause["kind"] == "gate" and answer.get("choice") not in pause["options"]:
        raise ValueError(f"choice must be one of {pause['options']}")
    if answer.get("choice") == "override" and len((answer.get("reason") or "").strip()) < 20:
        raise approval.ApprovalError("override needs a typed reason of at least 20 characters")
    if answer.get("request"):
        r = guardrails.check_request(answer["request"])
        if r:
            ctx.log("guardrails", "guardrail_refusal", rule=r.rule, match=r.match, where="founder_request")
    ctx.founder[pause["id"]] = answer
    ctx.data.pop("pause", None)
    ctx.save()


# ====================================================================== CLI
B, G, Y, R, C, X = "\033[1m", "\033[32m", "\033[33m", "\033[31m", "\033[36m", "\033[0m"
OPTION_HELP = {"continue": "go on to the next phase", "retry": "run this step again", "pivot": "go back and try the recommended alternative",
               "override": "continue anyway (you type a reason; every later file is stamped UNVALIDATED)", "stop": "end this run here",
               "enter_results": "type experiment results again", "try_again": "repeat the step that failed",
               "persevere": "keep going with this product", "approve": "allow this exact action", "reject": "do not allow it"}
PHASE_NAMES = {1: "Discover", 2: "Validate", 3: "Build", 4: "Commercial setup", 5: "Launch", 6: "Operate and learn"}


def _ask(prompt, allowed=None, default=None):
    while True:
        v = input(f"{B}{prompt}{X} ").strip()
        if not v and default is not None:
            return default
        if allowed is None or v in allowed:
            return v
        print(f"{R}Please type one of: {', '.join(allowed)}{X}")


def _cli_answer(ctx, pause, prefill):
    kind, phase = pause["kind"], pause.get("phase")
    print("\n" + "─" * 78)
    head = f"Phase {phase} · {PHASE_NAMES.get(phase, '')}" if phase else "Run"
    if kind in ("gate", "error"):
        outcome = (pause.get("gate") or {}).get("outcome") or pause.get("outcome")
        col = {"go": G, "stop": R}.get(outcome, Y)
        print(f"{B}{head} · {'GATE DECISION' if kind == 'gate' else 'MODEL PROBLEM'}{X}   result: {col}{B}{str(outcome).upper()}{X}")
        print(f"\n{pause.get('verdict')}\n")
        opts = pause["options"]
        print("What you can type:")
        for o in opts:
            print(f"  {C}{o:<14}{X} {OPTION_HELP.get(o, '')}")
        c = _ask("Your choice:", opts)
        ans = {"choice": c}
        if c == "override":
            default_reason = (prefill.get("override_reasons") or {}).get(str(phase), "")
            if default_reason:
                print(f"Prepared reason: \"{default_reason}\"")
            r = ""
            while len(r) < 20:
                r = _ask("Type your reason (at least 20 characters), or press Enter to use the prepared one:", default=default_reason)
            ans["reason"] = r
            if phase == 4:
                ans["experimental_price"] = _ask("Experimental price in USD (labelled ASSUMPTION), e.g. 19:")
                ans["currency"] = "USD"
        return ans
    if kind == "approval":
        print(f"{B}{head} · APPROVAL NEEDED{X}  (nothing happens unless you type approve)")
        print(f"  Action:       {pause['action']}\n  Destination:  {pause['destination']}\n"
              f"  Amount:       {pause['amount_minor']} {pause['currency']} (no money ever moves)\n  Run ID:       {pause['run_id']}\n"
              f"  Content hash: {pause['content_sha256'][:24]}…")
        print(f"\n{pause['note']}\n--- content preview ---\n{pause['content'][:900]}\n--- end of preview ---")
        return {"choice": _ask("Type approve or reject:", ["approve", "reject"])}
    if kind == "input":
        form = pause["form"]
        key = {"real_counts": "p2_counts", "persona_test": "p2_persona_test", "price_quotes": "p4_quotes", "mock_sale": "p5_mock_sale",
               "targets": "p6_targets", "metrics": "p6_metrics"}[form]
        title = {"real_counts": "REAL EXPERIMENT RESULTS", "persona_test": "OPTIONAL SIMULATED PERSONA TEST",
                 "price_quotes": "COMPETITOR PRICES", "mock_sale": "MOCKED SALE", "targets": "PHASE 6 TARGETS",
                 "metrics": "REAL POST-LAUNCH METRICS"}[form]
        print(f"{B}{head} · {title}{X}\n{pause.get('help', '')}")
        val = prefill.get(key)
        if val is not None:
            print("Prepared values from the brief file:\n" + json.dumps(val, indent=1))
            if _ask("Use these values? Type y or n:", ["y", "n"]) == "y":
                return _shape(form, val)
        raw = _ask("Paste JSON for this form, or press Enter for the default (empty / not started):", default="")
        return _shape(form, json.loads(raw) if raw else None)


def _shape(form, v):
    if form == "real_counts":
        return v or {"experiment_status": "not_started"}
    if form == "price_quotes":
        return {"quotes": v or []}
    if form == "persona_test":
        return v or {"run": False}
    if form == "mock_sale":
        return v or {"simulate_purchase": False}
    if form == "targets":
        return {"targets": v or {}}
    if form == "metrics":
        return {"metrics": v or []}
    return v


def main(argv=None):
    ap = argparse.ArgumentParser(description="Run the venture-builder pipeline headless (CLI founder control).")
    ap.add_argument("--brief", required=True)
    ap.add_argument("--label", default="x")
    ap.add_argument("--until-gate", type=int, default=0, help="stop at the first founder pause of this phase (stage tests)")
    ap.add_argument("--log", help="decision log path (scratch logs for stage tests)")
    a = ap.parse_args(argv)
    if a.log:
        os.environ["DECISION_LOG_PATH"] = os.path.abspath(a.log)
    brief = json.load(open(a.brief, encoding="utf-8"))
    prefill = brief.pop("founder_inputs", {}) or {}
    ctx = new_run(brief, a.label)

    def prog(ev):
        print(f"  {C}[agent]{X} call {ev.get('call')} {ev.get('agent')} tier={ev.get('tier')} {ev.get('status')}"
              f"{' (' + str(ev.get('reason')) + ')' if ev.get('reason') else ''} elapsed={ev.get('elapsed_s')}s budget_left={ev.get('budget_left_s')}s",
              flush=True)
    while True:
        pause = run_until_gate(ctx, prog)
        if pause["kind"] == "done":
            print(f"\n{G}{B}Run {ctx.run_id} finished with outcome: {ctx.final_outcome}{X}. Agents worked {ctx.system_time_s:.1f} s.")
            return 0
        if a.until_gate and pause.get("phase") == a.until_gate and pause["kind"] in ("gate", "error"):
            print(json.dumps({"run_id": ctx.run_id, "pause": {k: v for k, v in pause.items() if k != "content"}}, indent=1, default=str))
            return 0
        if not sys.stdin.isatty() and not os.environ.get("ALLOW_PIPED_FOUNDER"):
            print("No interactive founder: failing closed (nothing approved).", file=sys.stderr)
            print(json.dumps({"run_id": ctx.run_id, "pause": {k: v for k, v in pause.items() if k != "content"}}, indent=1, default=str))
            return 2
        ans = _cli_answer(ctx, pause, prefill)
        try:
            respond(ctx, ans, "typed")
        except (approval.ApprovalError, ValueError) as e:
            print(f"{R}Refused: {e}{X}")


if __name__ == "__main__":
    sys.exit(main())
