# Safety case: how each hard rule is enforced

Each rule names the code that enforces it and the offline test that proves it (`pytest -q`). Full mapping: [requirements_traceability.md](requirements_traceability.md).

| Rule | Enforced by | Proven by |
|---|---|---|
| Nothing is published, sent or spent without founder approval | `approval.py`: single-use binding of action, content SHA-256, destination, amount and run ID | `test_approval_refused_after_any_field_change`, `test_consumed_approval_cannot_run_twice`, `test_publish_blocked_without_approval` |
| No payment of any kind | `payments.py`, `delivery.py`, `refunds.py`, `reconcile.py` are a MOCKED SQLite ledger; the executor cannot queue payments | `test_refund_revokes_and_second_refund_refused`, `test_reconcile_matches_and_flags_one_cent` |
| A changed product is never delivered | Phase 5 checks files against the released manifest before any mock payment event | `test_tampered_product_file_is_not_delivered` |
| No fake reviews, sign-ups, urgency or income promises | `guardrails.py` on every generated text and request; `agents/rule_checker.py` as a second layer | `test_every_banned_case_refused_and_benign_allowed`, `test_model_layer_refuses_a_paraphrase_the_patterns_miss` |
| Excluded products stop and cannot be overridden | `guardrails.excluded()` before any search | `test_excluded_brief_stops_not_overridable` |
| Weak evidence is not spun | `gates.py` decides from thresholds logged before data; simulated sign-ups never count | `test_adequate_coverage_weak_evidence_no_alternative_stops`, `test_persona_test_is_simulated_and_excluded`, `test_mock_only_never_persevere` |
| A target cannot be moved after the data | SHA-256 lock of the Phase 2 target | `test_target_tamper_stops` |
| Every claim is sourced or ASSUMPTION | Models cite source IDs only; code renders URLs | `test_canvas_boxes_sourced_or_assumption` |
