"""Agents are role functions (SRS 2.5): each has one prompt file in prompts/<role>.md, one JSON
schema per call in schemas/, and logs every action. Agents propose; gate code decides."""
import json
import re
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def prompt(role):
    with open(os.path.join(ROOT, "prompts", role + ".md"), encoding="utf-8") as f:
        return f.read().strip()


def schema(name):
    with open(os.path.join(ROOT, "schemas", name + ".json"), encoding="utf-8") as f:
        s = json.load(f)
    s.pop("$schema", None)
    return s


def brief_text(b):
    return (f"Idea: {b.get('idea')}\nSkills: {b.get('skills')}\nBudget: {b.get('budget_amount')} {b.get('budget_currency')}\n"
            f"Time: {b.get('hours_per_week')} hours per week\nTarget market: {b.get('target_market')} ({b.get('countries')})\n"
            f"Values: {b.get('values')}")


def excerpts_text(ctx, ids):
    lines = []
    for sid in ids:
        r = ctx.sources[sid]
        lines.append(f"[{sid}] ({r['source']}) {r['excerpt']}")
    return "\n".join(lines)


def render_claim(ctx, c):
    """Code renders source IDs as URLs; a claim without IDs is printed as ASSUMPTION (DIS-4)."""
    ids = [s for s in c.get("source_ids", []) if s in ctx.sources]
    if not ids:
        return f"{c['text']} (ASSUMPTION)"
    out = c["text"] + " " + " ".join(f"[{s}]({ctx.sources[s]['url']})" for s in ids)
    # A place named in the claim must appear in a cited excerpt, or that part is labelled.
    places = [p.strip() for p in re.split(r"[,;/]| and ", (ctx.brief or {}).get("countries") or "") if p.strip()]
    named = [p for p in places if p.lower() in c["text"].lower()]
    cited = " ".join((ctx.sources[s].get("excerpt", "") + " " + ctx.sources[s].get("title", "")).lower() for s in ids)
    missing = [p for p in named if p.lower() not in cited]
    if missing:
        out += f" ({', '.join(missing)}: ASSUMPTION, no cited source mentions it)"
    return out


def urls(ctx, ids):
    return [ctx.sources[s]["url"] for s in ids if s in ctx.sources]
