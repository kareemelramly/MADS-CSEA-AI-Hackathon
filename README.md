# Agentic Venture Builder · Team Delulu

**An open-source AI venture team that tells first-time founders the truth: build it, change it, or stop.**

Most AI business tools promise income, lock founders into a closed platform and stop at a generic business plan. This one takes a founder's brief (idea, skills, budget, hours per week, target market, values) through the six phases a careful startup coach would use (Discover, Validate, Build, Commercial setup, Launch, Operate and learn) and attaches sourced evidence to every recommendation. Code, not the model, decides every gate. The founder approves every action that could leave the machine. It runs on an open-weight model on the founder's own laptop for **$0.00 per run**.

| | |
|---|---|
| **Customer** | First-time and student founders selling a *digital* product (templates, guides, toolkits): one person, a budget near $200, about 10 hours a week, often outside the US (our demo market is Egypt) |
| **Their problem** | They build first and test demand later, if at all. Generic AI tools flatter the idea, invent market numbers and push them to pay for a platform |
| **What they get** | For a weak idea: a reasoned **STOP** or **pivot** with the numbers behind it. For an idea worth testing: a Lean Canvas, a locked demand target, a landing page draft, a tested product pack, priced against real competitors, DRAFT policies, a store page, a MOCKED sale-to-cash ledger and a persevere-or-pivot memo, in one report (Markdown, web page, PDF) |
| **Why open beats closed** | MIT licence, local model, the founder's brief never goes to a model provider, every gate and threshold is readable code, and nothing is behind a paywall |
| **Business model** | None charged to founders: the full system stays free and open. Sustainability comes from maintainers, community contributions and grants (see the last section) |

**Results of the committed demo runs** (real runs with Gemma 4 26B A4B; files in [`outputs/`](outputs/), log in [`decision_log.json`](decision_log.json)):

| Brief | What the system decided | Why |
|---|---|---|
| **R**: Notion wedding-planning templates for Egypt | Phase 1 **GO**; Phase 2 **waits for real evidence**; the founder overrode it (and a thin Phase 4 price check) with typed reasons to complete all six phases, so every file after Phase 2 is stamped UNVALIDATED | 4 relevant pain points across 2 sources met the locked threshold of 3 from 2, fit 4.75 of 5 ([gate](outputs/phase1_gate_decision_r_a1.md)); no real experiment has run, so Phase 6 refuses to recommend persevering ([memo](outputs/phase6_step1_memo_r_a1.md)) |
| **W**: habit-tracking app, founder without matching skills | **PIVOT BACK** at Phase 1 to a better-fitting alternative | Founder fit 1.6 of 5, below the locked threshold of 3; the alternative 'Habit-Building Digital Guide' passes evidence and fit ([gate](outputs/phase1_gate_decision_w_a1.md)) |
| **E**: crypto trading-signal bot | **STOP** that cannot be overridden | Excluded product category, stopped before any search ([gate](outputs/phase1_gate_decision_e_a1.md)) |

Proof of control and honesty: a single-use approval bound to action, content hash, destination, amount ($0) and run ID for every publish, send or release; a MOCKED payment, delivery, refund and reconciliation run ([payment_test_log.md](outputs/payment_test_log.md)); and trick-prompt results on prompts the rules were never tuned on, weaknesses included ([guardrail_eval.md](docs/guardrail_eval.md)).

## Quickstart

```bash
docker compose up
```

Open **http://localhost:8501**. Pick an example brief (R, W or E) or write your own, press **Start the agents**, and answer each checkpoint with a button. At the end the page shows the full report with a **Download the report (PDF)** button.

- No key, account or payment. The first start downloads the default model once (Qwen3 4B Instruct 2507, under 3 GB) into a Docker volume.
- With an NVIDIA GPU: `docker compose -f docker-compose.yml -f docker-compose.gpu.yml up` (Gemma 4 26B A4B).
- Offline tests: `docker compose run --rm --no-deps app pytest -q`. Command line: `python -m orchestrator --brief tests/fixtures/brief_r.json --label r`. Troubleshooting: [docs/how_to_run.md](docs/how_to_run.md).

## What works and what is mocked

**Working** = built and covered by an offline test (`pytest -q`, fake model and fake sources). **MOCKED** = a local stand-in for a real service. **STUBBED** = never connected; it only records what it would do after founder approval. Persona tests are model-made, labelled SIMULATED and never counted as demand.

| Phase | Step | Status | What happens | Proof |
|---|---|---|---|---|
| 1 Discover | Find opportunities (core step) | **Working** | Thresholds logged before search; keyless search of HN, Stack Exchange and GitHub issues; every item registered as a source; duplicates, ads and hobby repos do not count | `test_thresholds_logged_before_first_search`, [opportunities](outputs/phase1_step1_opportunities_r_a1.md) |
| 1 Discover | Score idea vs two alternatives, define the market | **Working** | Model scores skills, budget, time and values; code weights them; a region no source mentions is ASSUMPTION | [comparison](outputs/phase1_step3_comparison_r_a1.md) |
| 1 Discover | Customer interviews (Mom Test) | **Working** | Past-behaviour questions only; code drops hypothetical ones | [script](outputs/phase1_step4_interview_script_r_a1.md) |
| 1 Discover | Evidence gate | **Working** | go / repeat / pivot_back / stop from coverage, evidence and fit | `test_adequate_coverage_weak_evidence_no_alternative_stops` |
| 2 Validate | Design the business: Lean Canvas (core step) | **Working** | Nine boxes, each sourced or ASSUMPTION | [canvas](outputs/phase2_step1_lean_canvas_r_a1.md) |
| 2 Validate | Demand target | **Working** | 100 sign-ups in 14 days, 200 visitors, locked by SHA-256 before any page exists | `test_target_tamper_stops` |
| 2 Validate | Landing page draft | **Working** | Template has no slot for reviews, counts or countdowns; guardrails check the text | [page](outputs/phase2_step3_landing_page_r_a1.html) |
| 2 Validate | Publishing the landing page | **STUBBED** | Approval only logs `would_publish` | `test_publish_blocked_without_approval` |
| 2 Validate | Waitlist form | **MOCKED** | Submits nowhere | landing page footer |
| 2 Validate | Demand gate | **Working** | Waits (`awaiting_evidence`) until a real experiment finishes; simulated sign-ups excluded | [gate](outputs/phase2_gate_decision_r_a1.md) |
| 3 Build | Build the product (core step) | **Working** | MVP definition, checklist and tracker pack, user docs | [MVP](outputs/phase3_step1_mvp_definition_r_a1.md) |
| 3 Build | Test gate and release approval | **Working** | 14 automated QA checks; release bound to the file hashes | [test report](outputs/phase3_step5_test_report_r_a1.md) |
| 4 Commercial | Set the price (core step) | **Working** | Median of at least 3 competitor prices whose pages loaded; otherwise `repeat` | [pricing](outputs/phase4_step1_pricing_r_a1.md) |
| 4 Commercial | Policies (core step) | **Working** | DRAFT Terms, Privacy, Refund, Delivery; not legal advice | [terms](outputs/phase4_step2_policy_terms_r_a1.md) |
| 5 Launch | Open the store (core step) | **Working** | Store page and launch post drafts, each with its own approval | [store page](outputs/phase5_step1_store_page_r_a1.md) |
| 5 Launch | Publishing and posting | **STUBBED** | Nothing is posted anywhere | `test_brief_r_full_run_with_override` |
| 5 Launch | Payment triggers delivery (core step) | **MOCKED** | Product files are re-hashed against the released manifest first; then a local SQLite payment event issues a download token. No payment of any kind runs | [mock sale](outputs/phase5_step3_mock_sale_r_a1.md) |
| 5 Launch | Refund revokes access; replayed event is not delivered twice | **MOCKED** | Idempotent events; second refund refused | `test_refund_revokes_and_second_refund_refused` |
| 5 Launch | Reconciliation of orders, payments, fees, payout | **MOCKED** | Matches to the cent; a 1-cent mismatch is flagged | [payment test log](outputs/payment_test_log.md) |
| 6 Operate | Support FAQ drafts | **Working** | Legal, health, financial and refund questions escalated to the founder | [FAQ](outputs/phase6_step2_support_faq_r_a1.md) |
| 6 Operate | Sending support replies | **STUBBED** | No send path is wired; the founder copies an approved draft by hand | `test_support_refuses_advice_and_promises` |
| 6 Operate | Metrics and persevere-or-pivot memo | **Working** | Only real metrics count; MOCKED and SIMULATED values are shown but ignored | `test_mock_only_never_persevere` |
| All | Founder approval executor | **Working** | Single use; any change to action, content, destination, amount or run ID is refused | `test_approval_refused_after_any_field_change` |
| All | Trick-prompt defence | **Working** | Pattern rules, then a local-model rule check that can only add refusals. Held-out set: 12/12 banned requests refused, 3/10 honest ones wrongly refused | [eval](docs/guardrail_eval.md) |
| All | Decision log and run report | **Working** | One log entry per agent action; report in Markdown, HTML and PDF | `test_full_run_writes_report_in_three_forms` |

<!-- runs:start -->
Committed demo runs (generated from `decision_log.json` by `scripts/index_runs.py`):

- `20261117T210325Z-r` (Notion templates for wedding planners in Egypt: a planning checklist and vendor tracker pack): artifacts in phases 1, 2, 3, 4, 5, 6/6; final outcome `stop`; gates: phase1_gate: `go`; phase2_gate: `awaiting_evidence`; phase3_gate: `go`; phase4_gate: `repeat`; phase4_gate: `go`; phase5_gate: `go`; phase6_gate: `repeat`.
- `20261117T211039Z-w` (A mobile app that gamifies daily habit tracking with streaks and badges): artifacts in phases 1/6; final outcome `pivot_back`; gates: phase1_gate: `pivot_back`.
- `20261117T211229Z-e` (A crypto trading signal bot that posts buy and sell alerts): artifacts in phases 1/6; final outcome `stop`; gates: phase1_gate: `stop`.

At least one committed run has recorded artifacts in all six phases.
<!-- runs:end -->

Every hard rule is mapped to code and a test in [docs/requirements_traceability.md](docs/requirements_traceability.md).

**Known limits, stated plainly:** offline tests use a fake model, so real-model quality is shown only by the committed runs. Live search results change between runs; in the committed R run Stack Exchange answered HTTP 400 and was recorded as failed, so its evidence came from HN and GitHub only. The trick-prompt defence still refuses some honest requests (3 of 10 held out). Policies are DRAFT, not legal advice. No real experiment has been run, so no run recommends persevering. The CPU model setup was not timed.

## Architecture

A fixed Python state machine (`orchestrator.py`) runs the six phases in order and pauses whenever the founder must decide. Eighteen agent roles are functions (`agents/<role>.py`), each with one prompt in `prompts/` and a JSON schema per call in `schemas/`; they cite fetched sources by ID and code turns IDs into URLs, so the model cannot invent a link. Gates (`gates.py`) check hard rules, then data completeness, then thresholds locked before the data, then the founder's choice. Every business action goes through the single-use approval executor (`approval.py`), and sale to cash is a MOCKED SQLite ledger (`payments.py`, `delivery.py`, `refunds.py`, `reconcile.py`). Diagrams, gate rules and data flow: [ARCHITECTURE.md](ARCHITECTURE.md); design choices and rejected alternatives: [docs/design_decisions.md](docs/design_decisions.md).

## Models and free resources

No paid service, API key or account is needed. Everything runs on your machine.

| Setup | Model (open weights) | Runtime | Licence | Cost |
|---|---|---|---|---|
| `docker compose up` (default, CPU) | Qwen3 4B Instruct 2507, GGUF Q4_K_M ([model](https://huggingface.co/Qwen/Qwen3-4B-Instruct-2507), [GGUF](https://huggingface.co/unsloth/Qwen3-4B-Instruct-2507-GGUF)) | llama.cpp `llama-server`, local | Apache 2.0 | $0 |
| GPU override, used for the committed demo runs | Gemma 4 26B A4B instruction-tuned, GGUF `UD-Q4_K_M` ([GGUF](https://huggingface.co/unsloth/gemma-4-26B-A4B-it-GGUF)) | llama.cpp `llama-server` with CUDA, local | Apache 2.0 ([model card](https://ai.google.dev/gemma/docs/core/model_card_4)) | $0 |

- llama.cpp is MIT-licensed ([repository](https://github.com/ggml-org/llama.cpp)). Qwen is one of the free model families the organizers list.
- **Measured speed (Gemma 4 26B A4B, team laptop, 16 GB GPU):** <!-- speed:start -->measured 2026-11-17T20:07:46 on the team laptop through llama.cpp: 10/10 schema-valid (correctness pass), about 81.6 tokens/s, slowest call 3.3 s (performance fast against the 40 tokens/s and 30 s planning limits).<!-- speed:end --> The Qwen3 4B CPU setup was not timed (ASSUMPTION: noticeably slower).
- **What leaves your machine:** only search words built from the idea, sent to keyless public APIs ([HN Algolia](https://hn.algolia.com/api), [Stack Exchange](https://api.stackexchange.com/docs), [GitHub search](https://docs.github.com/en/rest/search/search), [Wikipedia](https://www.mediawiki.org/wiki/API:Search) for background only), plus any link the founder adds. Reddit is not used because its [data API terms](https://support.reddithelp.com/hc/en-us/articles/16160319875092-Reddit-Data-API-Wiki) require registered credentials.
- Gate thresholds (20 items screened, 3 relevant items from 2 sources, fit 3 of 5, 100 sign-ups in 14 days, 200 visitors) are planning values labelled ASSUMPTION and logged before any data.

## Cost per run

**About $0.00 per run** (local open-weight model; the complete six-phase run used 16 model calls and about 19k tokens).

<!-- cost:start -->
$0.00 in model/API charges observed for complete six-phase run 20261117T210325Z-r (16 model calls, 19963 tokens; 239.5 s system time). Electricity and hardware are excluded (ASSUMPTION). Details: [docs/cost_report.md](docs/cost_report.md).
<!-- cost:end -->

| Cost item | Per run | Basis |
|---|---|---|
| Model calls | $0.00 | Observed: local llama.cpp, `cost` field in the decision log |
| Search APIs | $0.00 | Keyless public endpoints |
| Payments, hosting, publishing | $0.00 | MOCKED or STUBBED; nothing is charged or hosted |
| Electricity and hardware | not counted | ASSUMPTION: excluded |

## Demo video

**Watch (under 3 minutes):** https://drive.google.com/file/d/1SvaCZNoWQElYm35QG2vma8ybXCSM0CCa/view?usp=drivesdk

## What our system will NOT do

- Promise income, sales or success, or guarantee any result.
- Write fake reviews, testimonials, ratings, sign-up counts, countdown timers or false urgency.
- Pose as the founder, a customer or another brand.
- Hold, move, charge or refund real money, run sandbox or test-mode payments, create accounts, or store passwords or card numbers.
- Publish, post, send, spend or release anything without the founder approving that exact action; even then publishing and sending stay STUBBED.
- Help with excluded products: physical goods; financial, investment or crypto products; health or legal advice products.
- Treat missing data as a negative result, or let a model decide a gate.
- Hide core features behind a paywall: everything here is MIT-licensed and runs locally.

## How the project stays alive after the hackathon

| | Plan |
|---|---|
| **Maintainers** | The four members of Team Delulu triage issues and review pull requests on `main`; every change needs a passing `pytest -q` and keeps the approval executor untouched |
| **Next 3 months** | Arabic and English output for MENA founders; two more product shapes (HTML guide, template pack); a real-results import so Phase 2 and Phase 6 can judge actual experiments |
| **6 to 12 months** | Consented real integrations (form provider, store, email) behind the same approval executor, still with no payment handled by the system; a public evaluation set of briefs and trick prompts |
| **Community** | Issues and pull requests; each new agent ships with a prompt file, a schema and an offline test; university entrepreneurship clubs as the first users and testers |
| **Business case** | Customer, positioning, sustainability and milestones in one page: [docs/business_case.md](docs/business_case.md) |
| **Safety case** | Each hard rule, the code that enforces it and the test that proves it: [docs/safety_case.md](docs/safety_case.md) |
| **Pitch and FAQ** | Slide-by-slide pitch with its evidence: [docs/pitch_outline.md](docs/pitch_outline.md); questions founders ask: [docs/faq.md](docs/faq.md) |
| **Funding** | None committed today. Running it costs $0.00 in model or API charges, so the project survives on volunteer time; we will apply to university innovation grants and open-source sponsorship. Core features stay free |
