# Agentic Venture Builder · Team Delulu

An open-source team of AI agents that takes a founder's brief (idea, skills, budget, time, market, values) through six gated phases toward a validated, sellable **digital** product, and says **stop** when the evidence is weak. Code decides every gate; the founder approves every external action; publishing is STUBBED and payments are MOCKED.

## Quickstart

```bash
docker compose up
```

Open http://localhost:8501. The page shows a model status line and a local-model readiness line; pick a demo brief (r, w or e) or write your own and press **Run**.

- No keys needed: a clone without `.env` uses the local model only. If `models/gemma-4-26B-A4B-it-UD-Q4_K_M.gguf` exists (or `LOCAL_MODEL_DIR` in `.env` points at a folder holding it), nothing is downloaded; otherwise the `llm` container downloads it once (about 17 GB) into a Docker volume.
- NVIDIA GPU: `docker compose -f docker-compose.yml -f docker-compose.gpu.yml up`.
- Check your machine first: `bash scripts/doctor.sh`. Step-by-step guide: [docs/how_to_run.md](docs/how_to_run.md).
- Tests (offline, no keys): `docker compose run --rm app pytest -q`.
- Optional free remote tier: copy `.env.example` to `.env` and add an NVIDIA Build key.
- Headless CLI with typed founder answers: `python -m orchestrator --brief tests/fixtures/brief_r.json --label r`.

## What works and what is mocked

Status rule: **Working** means the code exists and the named offline test passes (`pytest -q`); **MOCKED** = fake service or data in place of a real one; **STUBBED** = never connected, only logs what it would do; **SIMULATED** = model-made stand-in for people, never counted as evidence.

| Step | Status | Verified by |
|---|---|---|
| 1 Discover: exclusion check, criteria logged before search, HN Algolia / Stack Exchange / GitHub search, source registry | Working | `test_thresholds_logged_before_first_search`, `test_excluded_brief_stops_not_overridable` |
| 1 Discover: coverage → evidence → fit gate, two ranked alternatives, Mom Test script | Working | `test_thin_coverage_repeats_never_stops`, `test_adequate_coverage_weak_evidence_no_alternative_stops` |
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
| Model chain NVIDIA Build → local llama.cpp, sticky per task, time budget | Working (fake HTTP) | `test_llm_cascade` |
| Guardrails against trick prompts (35-case eval set) | Working | `test_every_banned_case_refused_and_benign_allowed` |
| Streamlit UI: verdict before buttons, approval panel, amber override bar, readiness line | Working | `test_approval_panel_shows_five_fields`, `test_amber_bar_after_override` |

<!-- runs:start -->
Committed demo runs (generated from `decision_log.json` by `scripts/index_runs.py`):

- `20261117T180747Z-w` (A mobile app that gamifies daily habit tracking with streaks): reached Phase 1 of 6; final outcome `stop`; gates: phase1_gate: `stop`.
- `20261117T180902Z-e` (A crypto trading signal bot that posts buy and sell alerts): reached Phase 1 of 6; final outcome `stop`; gates: phase1_gate: `stop`.
- `20261117T180903Z-r` (Notion templates for wedding planners in Egypt: a planning c): reached Phase 1 of 6; final outcome `stop`; gates: phase1_gate: `go`.

No committed run has reached Phase 6 yet, so the committed evidence does not demonstrate a complete six-phase run.
<!-- runs:end -->

## Architecture

A fixed Python state machine (`orchestrator.py`) runs Discover, Validate, Build, Commercial setup, Launch and Operate in order, pausing whenever the founder must decide. Agents are role functions (`agents/<role>.py`) with one prompt each (`prompts/`) and a JSON schema per call (`schemas/`); they cite fetched sources only by ID, and code renders the URLs. Gates (`gates.py`) are plain code that checks hard rules, then data completeness, then thresholds locked before the data, so thin search, an unrun experiment or a model outage gives `repeat` or `awaiting_evidence`, never a false `stop`. Every external effect goes through one approval executor (`approval.py`), and the sale-to-cash flow is a MOCKED SQLite ledger. Full design, diagrams and gate rules: [ARCHITECTURE.md](ARCHITECTURE.md). Every hard rule is traced to the code that enforces it and the test that proves it in [docs/requirements_traceability.md](docs/requirements_traceability.md); the choices we rejected are in [docs/design_decisions.md](docs/design_decisions.md).

## Models and free resources

No paid service is needed. A fresh clone with no `.env` runs entirely on the local model.

| Tier | Model and runtime | Licence (source) | Cost and access (source) |
|---|---|---|---|
| Local (default, always on) | Google Gemma 4 26B A4B instruction-tuned, GGUF Q4_K_M (unsloth `UD-Q4_K_M`, about 17 GB), served by llama.cpp `llama-server` | Weights Apache 2.0 ([Gemma 4 model card](https://ai.google.dev/gemma/docs/core/model_card_4)); llama.cpp MIT ([repository](https://github.com/ggml-org/llama.cpp)) | $0; runs on your machine |
| Remote (optional) | NVIDIA Build hosted `google/gemma-4-31b-it`, OpenAI-compatible | Same Gemma 4 Apache 2.0 terms ([model card](https://ai.google.dev/gemma/docs/core/model_card_4)) | Free developer key, no card; prototyping use with rate limits ([NVIDIA NIM FAQ via build.nvidia.com](https://build.nvidia.com)). Exact limits vary by account (ASSUMPTION) |

- **Measured local speed:** <!-- speed:start -->measured 2026-11-17T20:07:46 on the team laptop through llama.cpp: 10/10 schema-valid (correctness pass), about 81.6 tokens/s, slowest call 3.3 s (performance fast against the 40 tokens/s and 30 s planning limits).<!-- speed:end -->
- CPU-only machines run the same default compose file, slowly; the default 1800 s per-segment budget (ASSUMPTION) keeps a slow machine from being cut off.
- The remote tier is optional: add `NVIDIA_API_KEY` to `.env`. If it fails, lags or runs out of quota, calls fall back to the local model automatically (tested in `tests/test_llm_cascade.py`). Remote calls receive prompt text, so use demo briefs only. No GPT-family model is used on any tier.
- Evidence sources are keyless public APIs: [HN Algolia search](https://hn.algolia.com/api), [Stack Exchange API](https://api.stackexchange.com/docs), [GitHub issue search](https://docs.github.com/en/rest/search/search); [Wikipedia](https://www.mediawiki.org/wiki/API:Search) for background only. Reddit is not used because its [data API terms](https://support.reddithelp.com/hc/en-us/articles/16160319875092-Reddit-Data-API-Wiki) require registered credentials.
- All gate thresholds (20 items screened, 3 relevant items, fit 3 of 5, 100 sign-ups in 14 days, 200 visitors) are planning values labelled ASSUMPTION and logged before any data.

## Cost per run

<!-- cost:start -->
About $0.00 per run expected (local model and free tiers only; no paid API, no payment of any kind). The observed figure from the logged demo run R replaces this line when `scripts/cost_per_run.py` runs. Electricity not included (ASSUMPTION).
<!-- cost:end -->

## Demo video

Not recorded yet. The video (at most 3 minutes) will show a STOP verdict, the approval screen with its five bound fields, the override banner and the MOCKED payment run.

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
- **Funding:** none today. Running costs stay at $0 because the default path is local and open-weight.
