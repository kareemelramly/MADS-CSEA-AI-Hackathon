# Requirements traceability

Every rule from the organizers' `CLAUDE.md` (Hard Requirements) and the key requirements of our Software Requirements Specification (SRS v1.4, IDs such as `APR-2`) mapped to the code that enforces it and the offline test that proves it. Run all tests with `pytest -q` (no network, no keys).

## Hard Requirements → code → test

| Rule | Enforced in | Proved by |
|---|---|---|
| Open-source licence, one-command setup | `LICENSE` (MIT, full text), `docker-compose.yml` | `tests/test_repo_layout.py::test_license_is_full_mit`, `::test_required_paths_exist` |
| Free open-weight model, no paid API | `llm.py` tiers: local Gemma 4 (llama.cpp) always on; optional free NVIDIA Build tier; any GPT model rejected at start | `tests/test_llm_cascade.py::test_no_keys_uses_local_only`, `::test_no_gpt_model_allowed` |
| No payments of any kind, mocks only | `payments.py`, `delivery.py`, `refunds.py`, `reconcile.py`: local SQLite events, no SDK, no network, card fields rejected | `tests/test_phase5_mock.py::test_ledger_modules_make_no_network_calls`, `::test_card_fields_rejected`, `tests/test_phase4_commercial.py::test_requirements_have_no_payment_sdk` |
| Founder approval for each action, in code | `approval.py`: binding of action, content SHA-256, destination, amount, run ID; single use; only `execute()` causes an effect | `tests/test_backbone.py::test_approval_refused_after_any_field_change` (5 cases), `::test_consumed_approval_cannot_run_twice`, `::test_execute_without_approval_refused`, `::test_no_default_approval` |
| Approval cannot override a prohibition | `approval.PROHIBITED`, amount must be 0, overrides refused for exclusions, guardrails, test gate | `::test_prohibited_actions_cannot_be_requested`, `::test_nonzero_amount_cannot_be_requested`, `::test_override_rules` |
| Cite every claim or label ASSUMPTION | `sources.py` registry (model sees IDs, code renders URLs), `validate.py` rejects unknown IDs and unlabelled unsourced claims, QA-10 | `tests/test_validate.py`, `tests/test_phase1_discover.py::test_unknown_source_id_from_model_is_rejected` |
| Label every mock | MOCKED/STUBBED/SIMULATED on landing page, store page, ledger log, persona report, UI chips, README table | `tests/test_phase5_mock.py::test_payment_test_run_script_all_mocked`, `tests/test_pivot_routes.py::test_persona_test_is_simulated_and_excluded` |
| Report cost per run, observed vs estimated | `log.py` records `cost`, tokens, tier per call; `scripts/cost_per_run.py` counts a run as complete only with Phase 6 files | `docs/cost_report.md` (generated) |
| Never promise income, fake reviews or urgency, impersonate | `guardrails.py` on every generated text and every founder request; QA-08 on the product | `tests/test_guardrails_eval.py` (35-case eval set), `tests/test_phase3_build.py::test_income_promise_repeats_then_stops` |
| Never hold, move or refund money; never store credentials | Prohibited actions cannot be queued; refunds only revoke a local token | `tests/test_phase5_mock.py::test_refund_revokes_and_second_refund_refused` |
| Excluded products | `guardrails.excluded()` before any search; non-overridable stop | `tests/test_e2e_pipeline.py::test_brief_e_stops_on_exclusion` |
| Weak evidence → stop, never spin | `gates.py`: coverage → evidence → fit → founder; thin data is `repeat`, never `stop` | `tests/test_phase1_discover.py`, `tests/test_phase2_validate.py::test_gate_covers_all_branches` |

## SRS requirements (selected) → code → test

| SRS ID | Requirement in one line | Code | Test |
|---|---|---|---|
| CORE-3, CORE-4 | Every phase ends in a gate computed by code | `gates.py` | `tests/test_phase2_validate.py::test_gate_covers_all_branches` |
| CORE-7 | Write-once outputs with run label and attempt number | `run_context.RunContext.out` | `tests/test_backbone.py::test_write_once_and_attempts` |
| CORE-9 | Model errors give `repeat`, never a business verdict, and use no quality attempt | `orchestrator.run_until_gate`, `llm.ModelError` | `tests/test_phase3_build.py::test_model_error_uses_no_build_attempt` |
| MOD-4, MOD-5 | Remote failure falls back to local; one tier per task | `llm.ask`, `llm.run_task`, `llm.probe_remote` | `tests/test_llm_cascade.py` (15 cases) |
| MOD-8, PERF-2 | Bounded attempts and time budget | `llm.ask` deadline checks | `tests/test_llm_cascade.py::test_budget_bounds_hanging_tiers` |
| DIS-2 | Thresholds logged before the first search | `agents/researcher.py` | `tests/test_phase1_discover.py::test_thresholds_logged_before_first_search` |
| DIS-6, DIS-7 | Thin coverage repeats; weak evidence on adequate coverage stops | `gates.discover_gate` | `::test_thin_coverage_repeats_never_stops`, `::test_adequate_coverage_weak_evidence_no_alternative_stops` |
| VAL-2 | Demand target locked by SHA-256 before any page | `gates.lock_target` | `tests/test_phase2_validate.py::test_target_tamper_stops` |
| VAL-6, VAL-7 | Eight ordered demand-gate rules; 12 of 100 fails | `gates.validate_gate` | `::test_twelve_of_hundred_fails`, `::test_final_attempt_near_miss` |
| BLD-4, BLD-5 | 14 QA checks; founder cannot pass a failed check | `agents/qa.py`, `gates.build_gate` | `tests/test_phase3_build.py` |
| COM-1 | Price = median of at least 3 sourced paid quotes | `agents/pricer.py` | `tests/test_phase4_commercial.py::test_median_of_three_in_code` |
| LCH-4, LCH-5, LCH-6 | Idempotent delivery, refund revokes, reconcile to the cent | ledger modules | `tests/test_phase5_mock.py` |
| OPS-3, OPS-4 | Mock or simulated data never gives persevere | `gates.operate_gate` | `tests/test_phase6_operate.py::test_mock_only_never_persevere` |
| UI-3, UI-4 | Verdict before buttons; approval shows five fields | `app.py` | `tests/test_ui_smoke.py` |
| LOG-1, LOG-4 | Five keys plus run ID; no key strings | `log.py` | `tests/test_backbone.py::test_log_entries_have_required_keys`, `::test_log_never_contains_keys` |
