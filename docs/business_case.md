# Business case: Agentic Venture Builder

One page for founders, partners and contributors. Every figure below is either measured in this repository or labelled ASSUMPTION.

## The problem

First-time founders of small digital products (templates, guides, toolkits) usually build first and test demand later, if at all. The AI business tools they reach for tend to promise income, flatter the idea, invent market numbers, keep the founder's data on a closed platform and stop at a generic plan. The result is wasted weeks on products nobody asked for (ASSUMPTION: based on the team's own experience as student founders, not on a survey).

## The customer

| Segment | Profile | Why they care |
|---|---|---|
| Primary | Student and first-time founders selling a digital product, budget near $200, about 10 hours a week, outside the US (demo market: Egypt) | Cannot afford to build the wrong thing; cannot pay for closed tools |
| Secondary | University entrepreneurship clubs and incubators | Need a repeatable, honest first-pass validation for many ideas at once |
| Tertiary | Mentors and coaches | Want a sourced, auditable starting point instead of a generic plan |

## The product, in one line

A brief goes in; six gated phases come out with sourced evidence, a code-decided verdict at every gate (go, repeat, pivot back, stop), founder approval for every outward action, and a report, all on a local open-weight model for $0.00 per run (measured: see [cost_report.md](cost_report.md)).

## What the demo runs show

| Brief | Outcome | Evidence |
|---|---|---|
| R: Notion wedding-planning templates (Egypt) | Phase 1 go; Phase 2 waits for a real experiment | [gate](../outputs/phase1_gate_decision_r_a1.md), [memo](../outputs/phase6_step1_memo_r_a1.md) |
| W: habit app, founder lacks the skills | Pivot back to a better-fitting alternative | [gate](../outputs/phase1_gate_decision_w_a1.md) |
| E: crypto trading-signal bot | Non-overridable stop (excluded category) | [gate](../outputs/phase1_gate_decision_e_a1.md) |

## Why open beats closed

| | Closed AI business tools (typical) | This project |
|---|---|---|
| Cost to the founder | Subscription (ASSUMPTION) | $0.00 per run, measured |
| Where the founder's idea goes | A vendor's servers | Stays on the founder's machine; only search words leave |
| How a verdict is reached | Opaque | Readable code with thresholds logged before the data |
| Honesty about weak ideas | Rarely says stop (ASSUMPTION) | Says stop or pivot with the numbers behind it |
| Lock-in | Account and data on the platform | MIT licence, runs offline except for search |

## Competition and positioning

Generic chat assistants, business-plan generators and no-code store builders each cover one slice: ideas, documents or a storefront. None of the ones the team tried combined sourced evidence, code-decided gates and founder approval in one local, free tool (ASSUMPTION: an informal comparison, not a systematic market scan). Positioning: the honest first step before a founder spends money, not a replacement for real customers.

## Sustainability

- **Cost structure:** no hosting and no model bill; contributors' time is the main cost.
- **Revenue:** none charged to founders. Core features stay free and open (no paywall).
- **Funding paths (planned, none committed):** university innovation grants, open-source sponsorship, and partnerships with incubators who run it for their cohorts.

## Milestones and how we will measure them

| When | Milestone | Measure |
|---|---|---|
| Month 1 | Arabic and English output; real-results import for Phase 2 | Phase 2 gates decided on real experiments, not overrides |
| Month 3 | Pilot with one university entrepreneurship club | Number of briefs run and how many reached a real experiment (target set before the pilot) |
| Month 6 to 12 | Consented integrations (form provider, store, email) behind the same approval executor | Zero actions without founder approval, checked by the log |

## Risks and what limits them

| Risk | Mitigation already in the code |
|---|---|
| Model invents evidence | Models cite source IDs only; code renders URLs; unsourced claims become ASSUMPTION |
| Tool spins weak results | Gates decided by code against thresholds locked before data; mock and simulated values never count |
| Unsafe or dishonest output | Pattern rules plus a local-model rule check; every output checked again before approval ([guardrail_eval.md](guardrail_eval.md)) |
| Money or accounts touched | Payments are MOCKED; the executor cannot queue payments, account creation or credential storage |
