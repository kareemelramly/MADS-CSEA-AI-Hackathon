"""Support agent (Phase 6). One call drafts a FAQ from the product docs and DRAFT policies. Code
labels every answer "DRAFT · AI-written for founder review", forces escalation for legal, health,
financial and refund questions (no advice, no promises), and runs guardrails. Sending a reply is
STUBBED behind approval (OPS-6, OPS-7)."""
import re

import guardrails
import llm
from agents import prompt, schema

ESCALATE = re.compile(r"\b(refund|money back|chargeback|legal|lawyer|sue|contract|tax|invest|loan|medical|health|diagnos|therapy|medication)\w*", re.I)
LABEL = "DRAFT · AI-written for founder review"


def faq(ctx, docs_excerpt, on_progress=None, policies=None):
    pol = "\n\n".join(f"[{k}]\n{v[:600]}" for k, v in (policies or {}).items() if v)
    user = (f"Product: {ctx.handoffs['H1']['idea_name']}\nProduct docs excerpt:\n{docs_excerpt[:1500]}\n\n"
            + (f"DRAFT policies (answer factual questions such as link expiry and updates from these):\n{pol}"
               if pol else "Policies exist as DRAFT documents: terms, privacy, refund, delivery."))
    d = llm.run_task(ctx, f"{ctx.run_id}:faq", lambda tid: llm.ask(
        prompt("support_agent"), user, schema("support_faq"), "support_agent", "draft_support_faq", ctx=ctx,
        task_id=tid, on_progress=on_progress, call_no="6.1"))
    return [answer_policy(item) for item in d["faq"]]


def answer_policy(item):
    q, a = item["question"], item["answer"]
    if ESCALATE.search(q) or ESCALATE.search(a) or item.get("escalate"):
        return {"question": q, "answer": "Escalated to the founder. This assistant gives no legal, health, financial or refund decisions or promises.",
                "escalate": True, "label": LABEL, "cites": item.get("cites", [])}
    r = guardrails.check(a)
    if r:
        return {"question": q, "answer": f"Removed by guardrails ({r.rule}). Escalated to the founder.", "escalate": True, "label": LABEL, "cites": []}
    return {"question": q, "answer": a, "escalate": False, "label": LABEL, "cites": item.get("cites", [])}


def faq_md(items):
    lines = ["# Support FAQ", "", f"Every answer: {LABEL}. Sending any reply is STUBBED behind founder approval.", ""]
    for it in items:
        tag = "ESCALATED" if it["escalate"] else "cites: " + ", ".join(it["cites"]) + (" (ASSUMPTION)" if "assumption" in it["cites"] else "")
        lines += [f"**Q: {it['question']}**", "", f"A: {it['answer']}", "", f"_{tag}_", ""]
    return "\n".join(lines)
