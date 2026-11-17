"""Policy drafter (Phase 4). One call drafts Terms, Privacy, Refund and Delivery; code adds the
banner "DRAFT · FOUNDER REVIEW REQUIRED · Not legal advice", checks required sections and blocks
compliance claims and promises (COM-2, LEG-2)."""
import re

import guardrails
import llm
from agents import prompt, schema

BANNER = "DRAFT · FOUNDER REVIEW REQUIRED · Not legal advice"
TITLES = {"terms": "Terms of use", "privacy": "Privacy policy", "refund": "Refund policy", "delivery": "Delivery policy"}
COMPLIANCE = re.compile(r"\b(fully compliant|compliant with|gdpr[- ]compliant|certified|legally binding|guaranteed compliance)\b", re.I)


def run(ctx, price, currency, on_progress=None):
    h1 = ctx.handoffs["H1"]
    user = (f"Product: {h1['idea_name']} (digital download: Markdown checklist and CSV tracker, MIT licence).\n"
            f"Price: {price} {currency} one-time. Delivery: MOCKED download link that expires after "
            "the configured hours; a refund revokes future access only (copies already downloaded cannot be revoked). "
            "The seller collects only an email address. No accounts, no passwords, no card data are stored by this system.")
    d = llm.run_task(ctx, f"{ctx.run_id}:policies", lambda tid: llm.ask(
        prompt("policy_drafter"), user, schema("policies"), "policy_drafter", "draft_policies", ctx=ctx, max_tokens=3000,
        task_id=tid, on_progress=on_progress, call_no="4.1"))
    missing, docs = [], {}
    for key, title in TITLES.items():
        body = [BANNER, "", f"# {title} (DRAFT)", ""]
        for sec, text in d[key].items():
            if not text.strip():
                missing.append(f"{key}.{sec}")
            if COMPLIANCE.search(text) or guardrails.check(text):
                missing.append(f"{key}.{sec} (compliance claim or banned content)")
            body += [f"## {sec.replace('_', ' ').capitalize()}", "", text, ""]
        docs[key] = "\n".join(body) + "\n"
    return docs, missing
