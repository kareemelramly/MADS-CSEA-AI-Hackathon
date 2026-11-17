"""Persona simulator (Phase 2, optional, SRS VAL-9). One call produces five SIMULATED persona
reactions to the landing page, to find weak spots in the copy. Everything it writes is labelled
SIMULATED; its "would join" count is stored apart and never reaches the demand gate."""
import llm
from agents import prompt, schema, brief_text

LABEL = "SIMULATED · model-generated personas, not real people, not evidence, never counted as sign-ups"


def run(ctx, copy, on_progress=None):
    user = (brief_text(ctx.brief) + f"\n\nLanding page headline: {copy['headline']}\nSubheadline: {copy['subheadline']}\n"
            "Benefits:\n" + "\n".join(f"- {b['text']}" for b in copy["benefits"]))
    out = llm.run_task(ctx, f"{ctx.run_id}:personas", lambda tid: llm.ask(
        prompt("persona_simulator"), user, schema("personas"), "persona_simulator", "simulate_personas", ctx=ctx,
        task_id=tid, on_progress=on_progress, call_no="2.3"))
    return out["personas"]


def report_md(personas):
    n = sum(1 for p in personas if p["would_join_waitlist"])
    lines = [f"# Phase 2 · Step 4 · Persona stress test ({LABEL})", "",
             f"SIMULATED would-join count: {n} of {len(personas)}. This number is excluded from the demand gate.", ""]
    for i, p in enumerate(personas, 1):
        lines += [f"## Persona {i} (SIMULATED)", "", f"- Who: {p['persona']}", f"- Context: {p['context']}",
                  f"- Likely reaction: {p['likely_reaction']}", f"- Would plausibly join: {p['would_join_waitlist']}",
                  f"- Main doubt: {p['main_doubt']}", ""]
    lines.append("Use the doubts to improve the page copy. Only real visitors and sign-ups can validate demand.")
    return "\n".join(lines) + "\n", n
