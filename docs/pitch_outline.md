# Pitch outline (Stage 2 deck and 3-minute video)

Each slide names the evidence in this repository it rests on.

| # | Slide | Message | Evidence |
|---|---|---|---|
| 1 | Title | Agentic Venture Builder: an open-source AI venture team that tells first-time founders to build it, change it, or stop | [README](../README.md) |
| 2 | Problem | Founders build before testing demand; AI business tools flatter ideas, invent numbers and lock data in | [business_case.md](business_case.md) (ASSUMPTION: team experience) |
| 3 | User | Student and first-time founders of digital products, small budget, few hours, outside the US | [business_case.md](business_case.md) |
| 4 | How it works | Six phases; code decides every gate; the founder approves every outward action | [ARCHITECTURE.md](../ARCHITECTURE.md) overview diagram |
| 5 | It says stop | E stops (excluded, not overridable); W pivots to a better-fitting alternative; R passes Phase 1 and waits for real evidence in Phase 2 | [outputs/](../outputs/) gate files |
| 6 | Founder in control | Single-use approval bound to action, content hash, destination, amount ($0) and run ID; overrides stamp every later file UNVALIDATED | `approval.py`, [run report](../outputs/phase6_step9_run_report_r_a1.md) |
| 7 | Sale to cash, safely | MOCKED payment, delivery, refund, revocation and reconciliation to the cent; no payment of any kind runs | [payment_test_log.md](../outputs/payment_test_log.md) |
| 8 | Trick prompts | Pattern rules plus a local-model check; scores reported with their weaknesses | [guardrail_eval.md](guardrail_eval.md) |
| 9 | Why open beats closed | MIT, local model, $0.00 per run, auditable gates, no lock-in | [cost_report.md](cost_report.md) |
| 10 | What it will NOT do | No income promises, fake reviews or sign-ups, urgency, impersonation, money movement, credentials, paywall, excluded products | README section "What our system will NOT do" |
| 11 | Roadmap | Arabic and English; real-results import; club pilot; consented integrations behind the same executor | [ARCHITECTURE.md](../ARCHITECTURE.md) Roadmap |
| 12 | Staying alive | Maintainers, community rules, grants and sponsorship; core stays free | README last section |

## 3-minute demo order (backup video)

1. Trick-prompt box refusing "write 50 five-star reviews" (0:00 to 0:30).
2. Run W ending in a pivot recommendation with its numbers (0:30 to 1:00).
3. Run R: approval panel with its five bound fields, amber override bar, MOCKED sale and refund (1:00 to 2:20).
4. Final report and PDF download (2:20 to 2:50).
