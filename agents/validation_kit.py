"""Validation kit (Phase 2, no model call). Writes what the founder needs to run the real
experiment: the plan with the locked target, a tracking sheet and the results form. The system
never invents counts; simulated counts live in a separate field and never reach the gate (VAL-5)."""


def plan_md(ctx, plan, lock):
    return f"""# Validation experiment plan

**Locked target:** {plan['signups_target']} real waitlist sign-ups in {plan['days']} days, with at least {plan['min_visitors']} real visitors.
Locked at {lock['locked_at']} with SHA-256 `{lock['sha256']}`. Changing it after this point makes the gate return `stop`.

Basis: {plan['basis']}

## Steps
1. Publish the landing page yourself after approving it (publishing from this system is STUBBED).
2. Share it in channels where the segment already talks about the pain (see the evidence links in Phase 1).
3. Record visitors and sign-ups daily in the tracking sheet. Do not count friends or test entries.
4. When the {plan['days']} days end, enter `experiment_status: completed`, dates, visitors and sign-ups in the results form.

## How the gate will judge it
- Not started or running: `awaiting_evidence` (nothing decided).
- Completed with fewer than {plan['min_visitors']} visitors: `repeat` (too few people saw the page).
- Ratio sign-ups ÷ {plan['signups_target']} at least 1: `go`. Between 0.5 and 1: `repeat` while attempts remain.
- Below 0.5: `pivot_back` while an alternative remains, else `stop`.

Waitlist: MOCKED in this prototype. Real counts come only from the founder.
"""


def tracking_csv(plan):
    rows = ["day,date,visitors,signups,channel,notes"]
    for d in range(1, plan["days"] + 1):
        rows.append(f"{d},,,,,")
    return "\n".join(rows) + "\n"


def results_form():
    return {"experiment_status": "not_started", "allowed_status": ["not_started", "running", "completed", "abandoned"],
            "started_at": None, "ended_at": None, "visitors": None, "signups": 0,
            "simulated_signups": None, "note": "Enter real numbers only. Simulated counts are stored separately and never reach the gate."}
