"""Strategist (Phase 2, Core step: design the business). One call: the 9-box Lean Canvas.
The demand plan "N sign-ups in D days" with min_visitors comes from locked config values
(ASSUMPTION planning values), never from the model, and is locked before any page exists."""
import config
import gates
import llm
from agents import prompt, schema, brief_text

BOXES = ["problem", "customer_segments", "unique_value_proposition", "solution", "channels",
         "revenue_streams", "cost_structure", "key_metrics", "unfair_advantage"]


def canvas(ctx, on_progress=None):
    h1 = ctx.handoffs.get("H1", {})
    ev = h1.get("evidence", [])
    ids = [e["source_id"] for e in ev]
    user = (brief_text(ctx.brief) + f"\n\nChosen idea: {h1.get('idea_name')}: {h1.get('idea_description')}\n"
            f"Segment: {h1.get('segment')}\nEvidence (source IDs):\n" +
            "\n".join(f"[{e['source_id']}] {e['pain_point']}" for e in ev))
    out = llm.run_task(ctx, f"{ctx.run_id}:canvas", lambda tid: llm.ask(
        prompt("strategist"), user, schema("canvas"), "strategist", "lean_canvas", ctx=ctx, sources=ids,
        task_id=tid, on_progress=on_progress, call_no="2.1"))
    forced = 0
    for b in BOXES:
        box = out["boxes"][b]
        if not box["source_ids"] and not box.get("assumption"):
            box["assumption"] = True
            forced += 1
    ctx.log("strategist", "canvas_self_check", forced_assumption=forced)
    return out["boxes"]


def plan_and_lock(ctx):
    plan = {"signups_target": config.validate_target_signups(), "days": config.validate_target_days(),
            "min_visitors": config.validate_min_visitors(),
            "basis": "ASSUMPTION: planning values set before any data (problem statement example: 100 sign-ups in 14 days)"}
    lock = gates.lock_target(plan)
    ctx.log("strategist", "lock_target", target=lock["plan"], sha256=lock["sha256"], locked_at=lock["locked_at"])
    return plan, lock
