"""Doc writer (Phase 3). One call; code assembles six fixed headings in order. "What is mocked"
is copied from the plan by code, and Quick start lists the journey steps J1..Jn in order with
links to the checklist anchors (QA-04, QA-05, QA-12)."""
import os

import llm
from agents import prompt, schema

HEADINGS = ["Overview", "Quick start", "How to use", "What is mocked", "Troubleshooting", "Limitations"]


def run(ctx, plan, checklist_path, on_progress=None, attempt=1):
    user = (f"Product: {ctx.handoffs['H1']['idea_name']} (A1 checklist pack: a Markdown checklist and a CSV tracker)\n"
            f"User story: {plan['user_story']}\nJourney:\n" + "\n".join(f"J{i + 1}. {s}" for i, s in enumerate(plan["journey"])) +
            f"\nWrite one quick-start line per journey step ({len(plan['journey'])} lines, same order).")
    d = llm.run_task(ctx, f"{ctx.run_id}:docs:{attempt}", lambda tid: llm.ask(
        prompt("doc_writer"), user, schema("docs"), "doc_writer", "write_user_docs", ctx=ctx, task_id=tid,
        on_progress=on_progress, call_no=f"3.3.{attempt}"))
    fname = os.path.basename(checklist_path)
    qs = []
    for i, step in enumerate(plan["journey"]):
        extra = d["quick_start"][i] if i < len(d["quick_start"]) else ""
        qs.append(f"{i + 1}. [J{i + 1}. {step}]({fname}#j{i + 1}): {extra}")
    lines = [f"# {ctx.handoffs['H1']['idea_name']}: user guide", "",
             "## Overview", "", d["overview"], "",
             "## Quick start", "", *qs, "",
             "## How to use", "", d["how_to_use"], "", "The tracker CSV has one row per checklist item; open it in any spreadsheet app.", "",
             "## What is mocked", "", *[f"- {m}" for m in plan["mocked"]], "",
             "## Troubleshooting", "", *[f"- {t}" for t in d["troubleshooting"]], "",
             "## Limitations", "", d["limitations"], "", "This pack does not promise any income or result."]
    return "\n".join(lines) + "\n"
