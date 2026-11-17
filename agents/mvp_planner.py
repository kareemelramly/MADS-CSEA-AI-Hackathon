"""MVP planner (Phase 3, Core step: build the product). One call: user story, at most 3 Must
features each with an evidence ID, 3-6 Given/When/Then criteria and the user journey.
Archetype, manifest and traceability matrix come from the A1 template in code (BLD-0, BLD-1)."""
import config
import llm
from agents import prompt, schema, brief_text

ARCHETYPE = "A1"
MOCKED_INTEGRATIONS = ["Reminders, sync or sharing with other apps: MOCKED (not built; the pack is static files)"]


def thresholds():
    return {"archetype": ARCHETYPE, "max_must_features": 3, "criteria": "3-6", "max_build_attempts": config.max_build_attempts(),
            "max_file_bytes": 100_000, "max_total_bytes": 300_000, "applicable_checks": 14, "qa07": "not applicable to A1"}


def run(ctx, mode, on_progress=None):
    ctx.log("mvp_planner", "set_phase3_thresholds", thresholds=thresholds(), mode=mode)
    h1, h2 = ctx.handoffs["H1"], ctx.handoffs.get("H2", {})
    ev = h1.get("evidence", [])
    ids = [e["source_id"] for e in ev]
    user = (brief_text(ctx.brief) + f"\n\nProduct: {h1['idea_name']}: {h1['idea_description']}\nArchetype: A1 checklist pack "
            f"(a Markdown checklist and a CSV tracker; no code, no scripts).\nMode: {mode} "
            f"({'exactly one Must feature' if mode == 'minimal' else 'at most three Must features'}).\n"
            f"Value proposition: {h2.get('value_proposition', '')}\nEvidence:\n" +
            "\n".join(f"[{e['source_id']}] {e['pain_point']}" for e in ev))
    plan = llm.run_task(ctx, f"{ctx.run_id}:mvp_plan", lambda tid: llm.ask(
        prompt("mvp_planner"), user, schema("mvp_plan"), "mvp_planner", "define_mvp", ctx=ctx, sources=ids,
        task_id=tid, on_progress=on_progress, call_no="3.1"))
    if mode == "minimal":
        plan["must_features"] = plan["must_features"][:1]
    plan["archetype"] = ARCHETYPE
    plan["mode"] = mode
    plan["mocked"] = list(MOCKED_INTEGRATIONS)
    plan["manual_criteria"] = ["A real target user completes the core workflow using only the docs (MANUAL, not checked)"]
    plan["matrix"] = [{"feature": f["name"], "evidence": f["source_ids"], "criteria": [i + 1 for i in range(len(plan["acceptance_criteria"]))],
                       "checks": ["QA-04", "QA-05", "QA-14"]} for f in plan["must_features"]]
    return plan
