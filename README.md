# Agentic Venture Builder · Team Delulu

An open-source team of AI agents that takes a founder's brief (idea, skills, budget, time, market, values) through six gated phases toward a validated, sellable **digital** product, and says **stop** when the evidence is weak. Code decides every gate; every business effect needs the founder's approval of that exact action. Publishing is STUBBED and payments are MOCKED. Every run ends with a report (Markdown, web page and PDF) built from the decision log.

**Model provider:** a local [llama.cpp](https://github.com/ggml-org/llama.cpp) `llama-server` on your own machine. No hosted or paid model API is called, so no API key exists anywhere in this project. **Models:** Qwen3 4B Instruct 2507 (Q4_K_M) by default in Docker (runs on a laptop CPU); Gemma 4 26B A4B (Q4_K_M) on an NVIDIA GPU, which is the model behind the committed demo runs. The decision log names the model the server actually loaded on every call.

**At a glance (all evidence is in this repository):**

- **It says stop.** The weak idea (W) ends in `pivot_back`, the excluded crypto idea (E) in a stop no one can override, and even the reasonable idea (R) gets a Phase 1 **STOP** on thin public evidence: [outputs/phase1_gate_decision_r_a1.md](outputs/phase1_gate_decision_r_a1.md).
- **The founder stays in control.** Every publish, send or release needs a single-use approval bound to the action, content hash, destination, amount ($0) and run ID; overrides need a typed reason and stamp every later file UNVALIDATED.
- **Nothing real moves.** The sale → delivery → refund → revoke → reconcile chain is MOCKED in local SQLite: [outputs/payment_test_log.md](outputs/payment_test_log.md). Publishing and sending are STUBBED.
- **Honest numbers.** Every claim links a fetched source or says ASSUMPTION; guardrail scores are reported on a held-out set, weaknesses included: [docs/guardrail_eval.md](docs/guardrail_eval.md).
- **$0.00 per run** on an open-weight model on your own machine; offline tests: `pytest -q`.

## Quickstart

```bash
docker compose up
```

Open http://localhost:8501. Pick an example brief (R: reasonable idea, W: weak idea, E: excluded idea) or write your own, then press **Start the agents**. At every checkpoint you read a plain verdict and press a button. When the run ends, the page shows the full report with a **Download the report (PDF)** button.

- **No keys, no account, no payment.** The first start downloads the default model once (Qwen3 4B Instruct 2507, Q4_K_M, under 3 GB) into a Docker volume. If the `.gguf` is already in `./models` (or in `LOCAL_MODEL_DIR` from `.env`), nothing is downloaded.
- **NVIDIA GPU (bigger model, faster):** `docker compose -f docker-compose.yml -f docker-compose.gpu.yml up` serves Gemma 4 26B A4B instead.
- Check your machine first: `bash scripts/doctor.sh`. Step-by-step guide with fixes for common errors: [docs/how_to_run.md](docs/how_to_run.md).
- Tests (offline, no model, no network): `docker compose run --rm app pytest -q`.
- Command line with typed founder answers: `python -m orchestrator --brief tests/fixtures/brief_r.json --label r`.
- Rebuild the committed demo evidence on a GPU laptop: `bash scripts/demo_runs.sh` (it never commits).

## What works and what is mocked

Status rule: **Working** means the code exists and the named offline test passes (`pytest -q`, with a fake model and fake sources, so it proves the workflow, not the quality of real model output). What a real model produced is in the committed demo runs listed under the table. **MOCKED** = fake service or data in place of a real one; **STUBBED** = never connected, only logs what it would do; **SIMULATED** = model-made stand-in for people, never counted as evidence.

| Step | Status | Verified by |
|---|---|---|
| 1 Discover: exclusion check, criteria logged before search, HN Algolia / Stack Exchange / GitHub search, source registry | Working | `test_thresholds_logged_before_first_search`, `test_excluded_brief_stops_not_overridable` |
| 1 Discover: coverage → evidence → fit gate, two ranked alternatives, Mom Test script | Working | `test_thin_coverage_repeats_never_stops`, `test_adequate_coverage_weak_evidence_no_alternative_stops` |
| 1 Discover: evidence hygiene (duplicates and repeated pain points count once; launches, ads and developer-exercise repos are not demand; a target country no source mentions is ASSUMPTION) | Working | `test_launches_and_duplicates_do_not_count_as_demand`, `test_hobby_repos_and_repeated_pain_points_do_not_count` |
| 2 Validate: Lean Canvas (sourced or ASSUMPTION), target locked by SHA-256 before any page | Working | `test_canvas_boxes_sourced_or_assumption`, `test_target_tamper_stops` |
| 2 Validate: landing page with guardrails | Working | `test_banned_landing_elements_refused` |
| 2 Validate: waitlist form | **MOCKED** (submits nowhere) | landing template footer "Waitlist: MOCKED" |
| 2 Validate: publishing the page | **STUBBED** behind approval | `test_publish_blocked_without_approval` |
| 2 Validate: demand gate (`awaiting_evidence` until a completed real experiment) | Working | `test_gate_covers_all_branches`, `test_not_started_awaits_evidence` |
| 2 Validate: persona stress test (optional, founder chooses) | Working; output **SIMULATED**, never counted as sign-ups | `test_persona_test_is_simulated_and_excluded` |
| 3 Build: A1 checklist pack, user docs, 14 QA checks, test gate, release approval | Working | `test_fixture_passes_all_applicable_checks`, `test_income_promise_repeats_then_stops` |
| 4 Commercial: median of ≥ 3 sourced competitor prices; DRAFT Terms, Privacy, Refund, Delivery | Working (drafts, not legal advice) | `test_median_of_three_in_code`, `test_policies_start_with_draft_banner` |
| 5 Launch: store page and launch post drafts, each with its own approval | Working (drafts); publishing **STUBBED** | `test_brief_r_full_run_with_override` |
| 5 Launch: pay → deliver → refund → revoke → reconcile → payout | **MOCKED** (local SQLite events; no payment of any kind) | `test_refund_revokes_and_second_refund_refused`, `test_reconcile_matches_and_flags_one_cent` |
| 6 Operate: support FAQ drafts (escalates legal, health, financial, refund) | Working (drafts); sending **STUBBED** | `test_support_refuses_advice_and_promises` |
| 6 Operate: metrics labelled real / MOCKED / SIMULATED, template memo, founder decision | Working | `test_mock_only_never_persevere`, `test_founder_decision_logged` |
| `pivot_back` routes: Build re-plan, Commercial → Build, Launch → Commercial | Working | `test_g3_rescope_once_then_stop`, `test_g4_rejected_offer_pivots_to_phase3`, `test_g5_rejected_drafts_retry` |
| Founder approval executor (action, content, destination, amount, run ID; single use) | Working | `test_approval_refused_after_any_field_change`, `test_consumed_approval_cannot_run_twice` |
| Local model client: JSON-schema output, one repair retry, time budget, failures become `repeat` (never `stop`) | Working (fake HTTP and a fake llama-server on 127.0.0.1) | `test_llm_cascade`, `test_full_run_over_local_http` |
| Trick-prompt defence, two layers: fixed pattern rules, then a local-model rule check that can only add refusals | Working. Patterns: 60/60 refused on the main set (in-sample, they were written from it) but only 3/12 on a held-out set written afterwards, with 2/10 honest questions wrongly refused. Model layer and full numbers: [docs/guardrail_eval.md](docs/guardrail_eval.md) | `test_every_banned_case_refused_and_benign_allowed`, `test_model_layer_refuses_a_paraphrase_the_patterns_miss` |
| Final run report: Markdown and HTML in `outputs/`, PDF download in the app | Working | `test_full_run_writes_report_in_three_forms`, `test_finished_run_shows_final_report_and_no_raw_json` |
| Streamlit UI: plain verdict before buttons, approval panel, amber override bar, readable tables (no raw JSON) | Working | `test_approval_panel_shows_five_fields`, `test_amber_bar_after_override` |

<!-- runs:start -->
Committed demo runs (generated from `decision_log.json` by `scripts/index_runs.py`):

- `20261117T194739Z-r` (Notion templates for wedding planners in Egypt: a planning checklist and vendor tracker pack): artifacts in phases 1, 2, 3, 4, 5, 6/6; final outcome `stop`; gates: phase1_gate: `stop`; phase2_gate: `awaiting_evidence`; phase3_gate: `go`; phase4_gate: `repeat`; phase4_gate: `go`; phase5_gate: `go`; phase6_gate: `repeat`.
- `20261117T195109Z-w` (A mobile app that gamifies daily habit tracking with streaks and badges): artifacts in phases 1/6; final outcome `pivot_back`; gates: phase1_gate: `pivot_back`.
- `20261117T195149Z-e` (A crypto trading signal bot that posts buy and sell alerts): artifacts in phases 1/6; final outcome `stop`; gates: phase1_gate: `stop`.

At least one committed run has recorded artifacts in all six phases.
<!-- runs:end -->

## Architecture

A fixed Python state machine (`orchestrator.py`) runs Discover, Validate, Build, Commercial setup, Launch and Operate in order, pausing whenever the founder must decide. Agents are role functions (`agents/<role>.py`) with one prompt each (`prompts/`) and a JSON schema per call (`schemas/`); they cite fetched sources only by ID, and code renders the URLs. Gates (`gates.py`) check hard rules, data completeness and thresholds locked before the data. The only model is a local llama.cpp server, and only idea-derived search words leave the machine. Business actions use a single-use approval executor (`approval.py`), and the sale-to-cash flow is a MOCKED SQLite ledger. Full design, diagrams and gate rules: [ARCHITECTURE.md](ARCHITECTURE.md). Hard rules and tested behavior are mapped in [docs/requirements_traceability.md](docs/requirements_traceability.md); the design choices are in [docs/design_decisions.md](docs/design_decisions.md).

## Models and free resources

No paid service, API key or account is needed. Everything runs on your machine.

| Setup | Model (open weights) | Runtime / provider | Licence (source) | Cost |
|---|---|---|---|---|
| `docker compose up` (default, CPU) | Qwen3 4B Instruct 2507, GGUF Q4_K_M ([model](https://huggingface.co/Qwen/Qwen3-4B-Instruct-2507), [GGUF](https://huggingface.co/unsloth/Qwen3-4B-Instruct-2507-GGUF)) | llama.cpp `llama-server`, local | Apache 2.0 ([model card](https://huggingface.co/Qwen/Qwen3-4B-Instruct-2507)) | $0 |
| GPU override, and the committed demo runs | Gemma 4 26B A4B instruction-tuned, GGUF `UD-Q4_K_M` ([GGUF](https://huggingface.co/unsloth/gemma-4-26B-A4B-it-GGUF)) | llama.cpp `llama-server` with CUDA, local | Apache 2.0 ([Gemma 4 model card](https://ai.google.dev/gemma/docs/core/model_card_4)) | $0 |

- llama.cpp is MIT-licensed ([repository](https://github.com/ggml-org/llama.cpp)). Qwen is one of the free model families the organizers list.
- **Measured local speed (Gemma 4 26B A4B, team laptop, 16 GB GPU):** <!-- speed:start -->measured 2026-11-17T20:07:46 on the team laptop through llama.cpp: 10/10 schema-valid (correctness pass), about 81.6 tokens/s, slowest call 3.3 s (performance fast against the 40 tokens/s and 30 s planning limits).<!-- speed:end --> The speed limits are team planning assumptions, not hackathon requirements. The Qwen3 4B CPU setup is slower and was not timed (ASSUMPTION: a run takes noticeably longer on CPU).
- **What leaves your machine:** only search words built from the idea, sent to keyless public APIs: [HN Algolia](https://hn.algolia.com/api), [Stack Exchange](https://api.stackexchange.com/docs), [GitHub issue search](https://docs.github.com/en/rest/search/search), and [Wikipedia](https://www.mediawiki.org/wiki/API:Search) for background only. A link the founder adds is fetched. The model, the brief and every draft stay local. Reddit is not used because its [data API terms](https://support.reddithelp.com/hc/en-us/articles/16160319875092-Reddit-Data-API-Wiki) require registered credentials.
- All gate thresholds (20 items screened, 3 relevant demand items from 2 sources, fit 3 of 5, 100 sign-ups in 14 days, 200 visitors) are planning values labelled ASSUMPTION and logged before any data.

## Cost per run

<!-- cost:start -->
$0.00 in model/API charges observed for complete six-phase run 20261117T194739Z-r (15 model calls, 18411 tokens; 77.1 s system time). Electricity and hardware are excluded (ASSUMPTION). Details: [docs/cost_report.md](docs/cost_report.md).
<!-- cost:end -->

## Demo video

Not recorded yet. The video (at most 3 minutes) shows run W ending in a STOP recommendation, the approval screen with its five bound fields, the amber override banner, the MOCKED sale and refund, the "Try to make the system break a rule" box refusing a fake-review request, and the final PDF report.

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

- **Maintainers:** the four members of Team Delulu, who built it, keep triaging issues and reviewing pull requests on `main`.
- **Roadmap:** product shapes A2 (HTML guide) and A3 (template pack); Arabic and English output for MENA founders; consented real integrations behind the same approval executor (see ARCHITECTURE.md, Roadmap).
- **Community:** contributions through issues and pull requests; every new agent needs a prompt file, a schema and an offline test, and `pytest -q` must pass without keys.
- **Funding:** none committed. Running it costs $0.00 in model or API charges because the model is local; electricity and hardware are excluded (ASSUMPTION).
