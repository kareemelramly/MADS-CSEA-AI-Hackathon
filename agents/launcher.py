"""Launcher (Phase 5, Core step: open the store). Two calls: the store page and one launch post.
Each needs its own founder approval and ends in a STUBBED publish ("STUBBED · NOT PUBLISHED").
Guardrails block testimonials, counts, urgency and income claims (LCH-1)."""
import guardrails
import llm
from agents import prompt, schema


class Blocked(Exception):
    pass


def _ctx_text(ctx):
    h1, h4 = ctx.handoffs["H1"], ctx.handoffs.get("H4", {})
    return (f"Product: {h1['idea_name']}: {h1['idea_description']}\nFormat: Markdown checklist + CSV tracker (A1), MIT licence.\n"
            f"Price: {h4.get('price')} {h4.get('currency')} one-time ({h4.get('price_basis')}).\n"
            f"Segment: {h1.get('segment')}\nValidation status: {ctx.validation_status}\n"
            f"Files in the product (describe only these): {', '.join(f['role'] for f in (ctx.handoffs.get('H3') or {}).get('manifest', {}).get('files', []))}")


WHAT = {"checklist": "Planning checklist (Markdown, imports into Notion)", "tracker": "Tracker spreadsheet (CSV, imports into Notion or any spreadsheet)",
        "license": "Licence file (MIT)", "docs": "User guide (Markdown)"}


def _what_you_get(ctx):
    """The file list is written by code from the released manifest, never by the model, so the store
    page cannot promise a file the product does not contain (an earlier real run listed a budget
    template and a guest list that were never built)."""
    files = (ctx.handoffs.get("H3") or {}).get("manifest", {}).get("files", [])
    return [f"- {WHAT.get(f['role'], f['role'])}: `{f['path'].split('/')[-1]}`" for f in files] or ["- (no released files)"]


def store_page(ctx, on_progress=None):
    d = llm.run_task(ctx, f"{ctx.run_id}:store", lambda tid: llm.ask(
        prompt("launcher") + "\n\nTASK: store page", _ctx_text(ctx), schema("store_page"), "launcher",
        "write_store_page", ctx=ctx, task_id=tid, on_progress=on_progress, call_no="5.1"))
    r = guardrails.check_obj(d)
    if r:
        ctx.log("guardrails", "guardrail_refusal", rule=r.rule, match=r.match, where="store_page")
        raise Blocked(str(r))
    h4 = ctx.handoffs.get("H4", {})
    lines = ["STUBBED · NOT PUBLISHED", "", f"# {d['title']}", "", d["short_description"], "",
             f"**Price:** {h4.get('price')} {h4.get('currency')} one-time · Checkout: MOCKED (no payment of any kind runs)", "",
             "## What you get", "", *_what_you_get(ctx), "", "## Who it is for", "", d["who_its_for"], "",
             "## FAQ", "", *[f"**{f['q']}**  \n{f['a']}\n" for f in d["faq"]],
             "", "Policies: Terms, Privacy, Refund and Delivery are DRAFT documents awaiting founder review."]
    return "\n".join(lines) + "\n"


def launch_post(ctx, on_progress=None):
    d = llm.run_task(ctx, f"{ctx.run_id}:post", lambda tid: llm.ask(
        prompt("launcher") + "\n\nTASK: launch post", _ctx_text(ctx), schema("launch_post"), "launcher",
        "write_launch_post", ctx=ctx, task_id=tid, on_progress=on_progress, call_no="5.2"))
    r = guardrails.check(d["text"])
    if r:
        ctx.log("guardrails", "guardrail_refusal", rule=r.rule, match=r.match, where="launch_post")
        raise Blocked(str(r))
    return f"STUBBED · NOT PUBLISHED\n\nSuggested channel: {d['channel_suggestion']}\n\n{d['text']}\n"
