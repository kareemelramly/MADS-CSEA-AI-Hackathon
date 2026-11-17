"""Gate decisions, computed by code only (SRS CORE-3 to CORE-5, ADR-06).

Every gate checks, in this order: (1) hard rules (exclusion, guardrail, tamper) ->
(2) data completeness (did the search or experiment happen and cover enough) ->
(3) locked thresholds -> (4) founder action (handled by the orchestrator).
Outcomes: go | repeat | pivot_back | stop. `awaiting_evidence` is a pause, not a verdict.
A lack of data is never reported as a negative result (BR-4).
"""
import hashlib
import json
from dataclasses import dataclass, field, asdict

import log as logmod

OUTCOMES = ("go", "repeat", "pivot_back", "stop")
PAUSE = "awaiting_evidence"


@dataclass
class GateResult:
    gate: str
    outcome: str
    verdict: str
    reasons: list = field(default_factory=list)
    numbers: dict = field(default_factory=dict)
    overridable: bool = True
    nothing_decided: bool = False

    def __post_init__(self):
        assert self.outcome in OUTCOMES + (PAUSE,), self.outcome

    def to_dict(self):
        return asdict(self)


def canonical(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


# ------------------------------------------------------------------ Phase 1
def discover_gate(*, missing_fields, excluded, values_conflict, coverage, relevant, fit, alternatives, thresholds):
    """coverage: {sources_ok, items_screened, failed:[...], retry_used}
    relevant: {count, sources:[names]}; fit: weighted score 1-5 with parts;
    alternatives: [{name, fit, passes_evidence}]"""
    n = {"sources_answered": coverage["sources_ok"], "items_screened": coverage["items_screened"],
         "relevant_items": relevant["count"], "relevant_sources": len(set(relevant["sources"])),
         "fit_score": fit, **{"threshold_" + k: v for k, v in thresholds.items()}}
    if excluded:
        return GateResult("phase1_gate", "stop", f"Excluded product category ({excluded}). This rule cannot be overridden; start a new run with a different idea.",
                          [f"exclusion: {excluded}"], n, overridable=False)
    if values_conflict:
        return GateResult("phase1_gate", "stop", f"The idea conflicts with the founder's stated values ({values_conflict}).", ["values_conflict"], n, overridable=False)
    if missing_fields:
        return GateResult("phase1_gate", "repeat", "The brief is missing: " + ", ".join(missing_fields) + ". Supply them and run again.",
                          ["missing_fields"], n, nothing_decided=True)
    alt_pass = [a for a in alternatives if a.get("fit", 0) >= thresholds["min_fit"] and a.get("passes_evidence")]
    if coverage["sources_ok"] < thresholds["min_sources_ok"] or coverage["items_screened"] < thresholds["min_items_screened"]:
        failed = ", ".join(coverage.get("failed") or []) or "none"
        return GateResult("phase1_gate", "repeat",
                          f"The search found too little to judge either way: {coverage['sources_ok']} sources answered "
                          f"(minimum {thresholds['min_sources_ok']}), {coverage['items_screened']} items screened "
                          f"(minimum {thresholds['min_items_screened']}). Sources that failed: {failed}. "
                          "This is inconclusive, not a weak idea. Add founder evidence URLs or broader terms and run again.",
                          ["coverage_thin"], n, nothing_decided=True)
    if relevant["count"] < thresholds["min_relevant"] or len(set(relevant["sources"])) < thresholds["min_relevant_sources"]:
        out = "pivot_back" if alt_pass else "stop"
        tail = f" Ranked alternative '{alt_pass[0]['name']}' passes, so the system recommends pivoting to it." if alt_pass else \
            " No ranked alternative passes evidence and fit, so the system recommends stopping."
        return GateResult("phase1_gate", out,
                          f"{relevant['count']} relevant of {coverage['items_screened']} screened across "
                          f"{len(set(relevant['sources']))} sources; threshold {thresholds['min_relevant']} across "
                          f"{thresholds['min_relevant_sources']} sources. This means not enough public evidence of the pain, "
                          f"not proof that no market exists.{tail} What would change it: founder evidence URLs showing the pain.",
                          ["evidence_weak"], n)
    if fit < thresholds["min_fit"]:
        out = "pivot_back" if alt_pass else "stop"
        tail = f" Alternative '{alt_pass[0]['name']}' passes evidence and fit." if alt_pass else " No alternative passes."
        return GateResult("phase1_gate", out,
                          f"Founder fit {fit:.2f} of 5 is below the threshold {thresholds['min_fit']}.{tail} "
                          "What would change it: more time, budget or matching skills in the brief.", ["fit_weak"], n)
    return GateResult("phase1_gate", "go",
                      f"{relevant['count']} relevant items across {len(set(relevant['sources']))} sources (threshold "
                      f"{thresholds['min_relevant']}); fit {fit:.2f} of 5 (threshold {thresholds['min_fit']}). "
                      "The idea may continue to a validation experiment. Demand is NOT validated yet, and this public-source sample does not independently establish demand in the founder's target country or region. Validate locally before treating fit as evidence of local demand.", ["pass"], n)


# ------------------------------------------------------------------ Phase 2
def lock_target(plan):
    """plan: {signups_target N, days D, min_visitors}. Returns the lock record."""
    body = canonical({k: plan[k] for k in ("signups_target", "days", "min_visitors")})
    return {"sha256": hashlib.sha256(body.encode()).hexdigest(), "locked_at": logmod.now_iso(), "plan": json.loads(body)}


def target_intact(plan, lock):
    body = canonical({k: plan[k] for k in ("signups_target", "days", "min_visitors")})
    return hashlib.sha256(body.encode()).hexdigest() == lock["sha256"]


def validate_gate(*, plan, lock, counts, attempt, max_attempts, alternatives_left, floor=0.5):
    """VAL-6, first match wins. counts: {experiment_status, visitors(None=unknown), signups, simulated_signups}"""
    N = plan["signups_target"]
    sim = counts.get("simulated_signups")
    n = {"target_signups": N, "days": plan["days"], "min_visitors": plan["min_visitors"],
         "experiment_status": counts.get("experiment_status"), "visitors": counts.get("visitors"),
         "real_signups": counts.get("signups", 0), "simulated_signups_excluded": sim, "attempt": attempt,
         "max_attempts": max_attempts, "repeat_floor": floor}
    if not target_intact(plan, lock):
        return GateResult("phase2_gate", "stop", "The demand target was changed after it was locked. The result cannot be judged honestly.", ["target_tampered"], n, overridable=False)
    st = counts.get("experiment_status", "not_started")
    if st in ("not_started", "running"):
        return GateResult("phase2_gate", PAUSE, f"No completed experiment yet (status: {st}). Real demand is unknown, so nothing is decided. "
                          f"Run the experiment: {N} sign-ups in {plan['days']} days, at least {plan['min_visitors']} visitors.",
                          ["no_completed_experiment"], n, nothing_decided=True)
    if st == "abandoned":
        return GateResult("phase2_gate", "repeat", "The experiment did not finish, so there is no conclusion. This does not use an attempt.", ["abandoned"], n, nothing_decided=True)
    vis = counts.get("visitors")
    if vis is not None and vis < plan["min_visitors"]:
        return GateResult("phase2_gate", "repeat", f"Too few people saw the page to judge ({vis} of {plan['min_visitors']} expected). This does not use an attempt.", ["low_exposure"], n, nothing_decided=True)
    s = counts.get("signups", 0)
    r = s / N if N else 0
    n["ratio"] = round(r, 3)
    sim_txt = f" Simulated count ({sim}) was excluded." if sim else ""
    if r >= 1:
        return GateResult("phase2_gate", "go", f"{s} real sign-ups of the locked target {N} (ratio {r:.2f} >= 1).{sim_txt} Demand signal met for this experiment.", ["target_met"], n)
    if floor <= r < 1 and attempt < max_attempts:
        return GateResult("phase2_gate", "repeat", f"{s} of {N} real sign-ups (ratio {r:.2f}, between {floor} and 1). Attempt {attempt} of {max_attempts}: change the copy or channel and repeat.{sim_txt}", ["near_miss"], n)
    if alternatives_left:
        return GateResult("phase2_gate", "pivot_back", f"{s} of {N} real sign-ups (ratio {r:.2f}) misses the locked target. The system recommends pivoting back to the next ranked alternative instead of spinning the result.{sim_txt}", ["target_missed"], n)
    return GateResult("phase2_gate", "stop", f"{s} of {N} real sign-ups (ratio {r:.2f}) misses the locked target and no alternative is left. The system recommends stopping.{sim_txt}", ["target_missed_no_alternative"], n)


# ------------------------------------------------------------------ Phase 3
def build_gate(*, qa, attempt, max_attempts, rescope_left=False):
    failed = [c for c in qa if c["status"] == "fail"]
    n = {"checks_applicable": sum(1 for c in qa if c["status"] != "n/a"), "checks_failed": len(failed), "attempt": attempt, "max_attempts": max_attempts}
    if not failed:
        return GateResult("phase3_gate", "go", f"All {n['checks_applicable']} applicable checks pass (QA-07 not applicable to A1). Release needs founder approval.", ["qa_pass"], n, overridable=False)
    ids = ", ".join(c["id"] for c in failed)
    if attempt < max_attempts:
        return GateResult("phase3_gate", "repeat", f"Failed checks: {ids}. Attempt {attempt} of {max_attempts}; failures are fed back to the builder.", ["qa_fail"], n, overridable=False)
    if rescope_left and not ({"QA-08", "QA-09"} & {c["id"] for c in failed}):
        return GateResult("phase3_gate", "pivot_back", f"Checks still failing after {max_attempts} attempts: {ids}. The plan cannot be traced to a working product, so the system recommends going back to re-plan the MVP from the evidence (once). The founder cannot pass a failed check.",
                          ["qa_exhausted_rescope"], n, overridable=False)
    return GateResult("phase3_gate", "stop", f"Checks still failing after {max_attempts} attempts: {ids}. The founder cannot pass a failed check.", ["qa_exhausted"], n, overridable=False)


# ------------------------------------------------------------------ Phase 4
def commercial_rejected_gate(*, price, currency):
    return GateResult("phase4_gate", "pivot_back", f"The founder rejected the commercial setup (price {price} {currency} and DRAFT policies). Nothing was signed. "
                      "Options: re-price (retry) or go back to Phase 3 to change the product (pivot).", ["founder_rejected_offer"],
                      {"price": price, "currency": currency}, overridable=False)


def commercial_gate(*, quotes_ok, price, policies_missing, overridden_price):
    n = {"paid_quotes": quotes_ok, "required_quotes": 3, "price": price}
    if policies_missing:
        return GateResult("phase4_gate", "repeat", "Policy drafts are missing required sections: " + ", ".join(policies_missing), ["policies_incomplete"], n, nothing_decided=True)
    if quotes_ok < 3 and not overridden_price:
        return GateResult("phase4_gate", "repeat", f"Only {quotes_ok} verified paid one-time competitor prices (need 3). No price is set; add quotes or override with an experimental price labelled ASSUMPTION.",
                          ["price_evidence_thin"], n, nothing_decided=True)
    src = "ASSUMPTION (founder override, experimental)" if overridden_price else f"median of {quotes_ok} sourced competitor prices"
    return GateResult("phase4_gate", "go", f"Price {price} set from {src}. Policies are DRAFT. Commercial approval authorizes the internal hand-off only; nothing is signed.", ["ok"], n)


# ------------------------------------------------------------------ Phase 5
def launch_gate(*, store_approved, post_approved, mock_ok, offer_left=False):
    n = {"store_page_approved": store_approved, "launch_post_approved": post_approved, "mock_ledger_checks": mock_ok}
    if mock_ok and not (store_approved and post_approved) and offer_left:
        return GateResult("phase5_gate", "pivot_back", "The founder rejected the launch drafts. Nothing was published. Options: redraft them (retry) or go back to Phase 4 to change the offer (pivot).",
                          ["drafts_rejected"], n, overridable=False)
    if not mock_ok:
        return GateResult("phase5_gate", "repeat", "MOCKED sale-to-cash checks failed; fix before continuing.", ["mock_fail"], n, overridable=False)
    if not (store_approved and post_approved):
        return GateResult("phase5_gate", "repeat", "Store page and launch post each need their own founder approval. Nothing was published.", ["approval_missing"], n, nothing_decided=True)
    return GateResult("phase5_gate", "go", "Mock run only: store page and post approved as STUBBED drafts (NOT PUBLISHED); MOCKED pay, deliver, refund and reconcile passed.", ["ok"], n)


# ------------------------------------------------------------------ Phase 6
def operate_gate(*, targets, metrics, phase2_completed, alternative_left):
    """metrics: [{name, value, label: real|MOCKED|SIMULATED, evidence}]. Only real values count (OPS-1)."""
    real = {m["name"]: m["value"] for m in metrics if m.get("label") == "real" and m.get("value") is not None}
    n = {"targets": targets, "real_metrics": real, "phase2_completed": phase2_completed,
         "ignored_mock_or_simulated": [m["name"] for m in metrics if m.get("label") != "real"]}
    if not real and not phase2_completed:
        return GateResult("phase6_gate", "repeat", "No real demand data yet (Phase 2 never completed an experiment and no real post-launch metrics were entered). No persevere recommendation is possible. Run the Phase 2 experiment first.",
                          ["no_real_data"], n, nothing_decided=True)
    if not real:
        return GateResult("phase6_gate", "repeat", "Only MOCKED or SIMULATED numbers exist; they never justify persevere. Enter real metrics with evidence links.", ["mock_only"], n, nothing_decided=True)
    missed = [k for k, v in targets.items() if real.get(k) is None or real[k] < v]
    if not missed:
        return GateResult("phase6_gate", "go", "Every pre-set target is met by real values: persevere is recommended. This is not a promise of income.", ["targets_met"], n)
    if alternative_left:
        return GateResult("phase6_gate", "pivot_back", "Real values miss targets: " + ", ".join(missed) + ". Recommend pivoting to an alternative or fixing the product.", ["targets_missed"], n)
    return GateResult("phase6_gate", "stop", "Real values miss targets: " + ", ".join(missed) + ", and no alternative is left. Recommend stopping.", ["targets_missed"], n)


def write_verdict(g, title):
    lines = [f"# {title}", "", f"**Outcome:** `{g.outcome}`" + ("  (pause: nothing decided)" if g.outcome == PAUSE else ""), "",
             g.verdict, "", "| Measure | Value |", "|---|---|"]
    for k, v in g.numbers.items():
        lines.append(f"| {k} | {v} |")
    lines += ["", f"Founder override allowed: {'yes (typed reason, at least 20 characters)' if g.overridable and g.outcome != 'go' else 'no'}",
              "", "Thresholds are planning values (ASSUMPTION) fixed before the run and logged as criteria before any data."]
    return "\n".join(lines) + "\n"
