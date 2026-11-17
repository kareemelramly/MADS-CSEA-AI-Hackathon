"""Builder (Phase 3). One slot-fill call; code renders the team-written A1 template with Jinja2
(autoescape on). The model fills text slots only: it never writes code, and the builder never
calls eval, exec or subprocess (BLD-2, BLD-8). Failing QA messages are fed back on a retry."""
import csv
import io
import os

from jinja2 import Environment, FileSystemLoader, select_autoescape

import llm
from agents import ROOT, prompt, schema, brief_text

ENV = Environment(loader=FileSystemLoader(os.path.join(ROOT, "templates")),
                  autoescape=select_autoescape(["html", "j2", "md"]), keep_trailing_newline=True)

LICENSE_TXT = """SPDX-License-Identifier: MIT

MIT License

Copyright (c) {year} the founder of {product}

Permission is hereby granted, free of charge, to any person obtaining a copy of this checklist pack
and associated documentation files (the "Software"), to deal in the Software without restriction,
including without limitation the rights to use, copy, modify, merge, publish, distribute,
sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or
substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT
NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES
OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""


def fill(ctx, plan, feedback=None, on_progress=None, attempt=1):
    journey = plan["journey"]
    user = (brief_text(ctx.brief) + f"\n\nProduct: {ctx.handoffs['H1']['idea_name']}\nUser story: {plan['user_story']}\n"
            "Must features:\n" + "\n".join(f"- {f['name']}: {f['description']}" for f in plan["must_features"]) +
            "\nJourney steps (write exactly one section per step, same order):\n" +
            "\n".join(f"J{i + 1}. {s}" for i, s in enumerate(journey)))
    if feedback:
        user += "\n\nThe previous build failed these checks; fix them:\n" + "\n".join(f"- {m}" for m in feedback)
    return llm.run_task(ctx, f"{ctx.run_id}:build:{attempt}", lambda tid: llm.ask(
        prompt("builder"), user, schema("build_slots"), "builder", "fill_template_slots", ctx=ctx, task_id=tid, max_tokens=2500,
        on_progress=on_progress, call_no=f"3.2.{attempt}"))


def render(ctx, plan, slots):
    journey = plan["journey"]
    sections = []
    for i, step in enumerate(journey):
        items = slots["sections"][i]["items"] if i < len(slots["sections"]) else []
        sections.append({"n": i + 1, "anchor": f"j{i + 1}", "step": step, "entries": items})
    md = ENV.get_template("a1_checklist/checklist.md.j2").render(
        title=slots["title"], intro=slots["intro"], sections=sections, mocked=plan["mocked"], run_id=ctx.run_id)
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(["journey_step", "item", "done", "due_date", "notes"])
    for s in sections:
        for it in s["entries"]:
            w.writerow([f"J{s['n']} {s['step']}", it, "", "", ""])
    lic = LICENSE_TXT.format(year=2026, product=ctx.handoffs["H1"]["idea_name"])
    return {"checklist": md, "tracker": buf.getvalue(), "license": lic}
