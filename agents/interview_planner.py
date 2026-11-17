"""Interview planner (Phase 1). One call: a Mom Test interview script about past behaviour only.
Code drops hypothetical or leading questions ("Would you buy...") and never invents answers."""
import re

import llm
from agents import prompt, schema, brief_text

HYPOTHETICAL = re.compile(r"^\s*(would|will|could|do you think|if we|how much would|would you pay|do you like)\b", re.I)


def run(ctx, segment, on_progress=None):
    user = brief_text(ctx.brief) + f"\n\nCustomer segment: {segment}\nWrite the interview script."
    out = llm.run_task(ctx, f"{ctx.run_id}:interview:{ctx.data.get('p1_attempt', 1)}", lambda tid: llm.ask(
        prompt("interview_planner"), user, schema("interview"), "interview_planner", "write_interview_script",
        ctx=ctx, task_id=tid, on_progress=on_progress, call_no="1.6"))
    kept = [q for q in out["questions"] if not HYPOTHETICAL.search(q["question"])]
    dropped = len(out["questions"]) - len(kept)
    ctx.log("interview_planner", "filter_mom_test", kept=len(kept), dropped_hypothetical=dropped)
    return kept, dropped
