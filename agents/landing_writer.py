"""Landing writer (Phase 2). One call fills headline, benefits and FAQ; code renders the Jinja2
template (autoescape on) with an email-only waitlist labelled "Waitlist: MOCKED". Guardrails run
on every string; no counts, testimonials, ratings or countdowns can appear (VAL-3)."""
import os

from jinja2 import Environment, FileSystemLoader, select_autoescape

import guardrails
import llm
from agents import ROOT, prompt, schema, brief_text

ENV = Environment(loader=FileSystemLoader(os.path.join(ROOT, "templates")), autoescape=select_autoescape(["html", "j2"]))


class GuardrailBlocked(Exception):
    def __init__(self, refusal):
        super().__init__(str(refusal))
        self.refusal = refusal


def run(ctx, canvas, on_progress=None):
    h1 = ctx.handoffs["H1"]
    ids = [e["source_id"] for e in h1.get("evidence", [])]
    user = (brief_text(ctx.brief) + f"\n\nProduct: {h1['idea_name']}: {h1['idea_description']}\n"
            f"Value proposition: {canvas['unique_value_proposition']['text']}\nPains with source IDs:\n" +
            "\n".join(f"[{e['source_id']}] {e['pain_point']}" for e in h1.get("evidence", [])))
    out = llm.run_task(ctx, f"{ctx.run_id}:landing:{ctx.data.get('p2_attempt', 1)}", lambda tid: llm.ask(
        prompt("landing_writer"), user, schema("landing"), "landing_writer", "write_landing_page", ctx=ctx,
        sources=ids, task_id=tid, on_progress=on_progress, call_no="2.2"))
    ref = guardrails.check_obj(out)
    if ref:
        ctx.log("guardrails", "guardrail_refusal", rule=ref.rule, match=ref.match, where="landing_page")
        raise GuardrailBlocked(ref)
    return out


def render(ctx, copy):
    benefits = []
    for b in copy["benefits"]:
        links = [(s, ctx.sources[s]["url"]) for s in b.get("source_ids", []) if s in ctx.sources]
        benefits.append({"text": b["text"], "links": links, "assumption": not links})
    html = ENV.get_template("landing/page.html.j2").render(
        c=copy, benefits=benefits, run_id=ctx.run_id, override=ctx.overridden,
        product=ctx.handoffs["H1"]["idea_name"])
    return html
