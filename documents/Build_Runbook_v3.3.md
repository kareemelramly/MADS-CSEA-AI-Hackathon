MADS × CSEA AI Hackathon · Build guide · 17 Nov 2026 · Version 3.4 (3.3 + implementation changes, section 0.5)

# Build Runbook v3.3: Empty Repo to Submission

v2 as the base, with the research report's useful parts merged in and ten review findings fixed, so every step from 14:00 to the 23:59 push has exact files, commands and a check that ends it.

## 0. What changed in v3 and why

*Source: Review of v2 · research report (17 Nov) · CLAUDE.md · problem statement*

**In one line:** v2's order, gates and Groq → NVIDIA → local cascade stay. v3 fixes ten places where v2 could give a wrong verdict, lose evidence, overrun the demo or overload one person, and takes nine design rules from the research report.

### 0.1 Review fixes

| #  | Problem in v2                                                                             | Fix in v3                                                                                                                                                                 | Where                  |
|-----|-------------------------------------------------------------------------------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------|------------------------|
| 1   | Validate: the default count of 0 always gives pivot or stop, even when no experiment ran. | New `experiment_status`. Not started or running → `awaiting_evidence` (nothing decided). Completed → completeness check, then the failure rules.                          | Steps 2, 4, 7          |
| 2   | Discover: "little public discussion" was the suggested STOP demo.                         | Search coverage is measured separately from evidence. Thin coverage → `repeat` (inconclusive). Only adequate coverage with too few relevant items can give pivot or stop. | Steps 3, 9             |
| 3   | Docker: "as in v1" with no config.                                                        | Full `docker-compose.yml`, GPU override, `Dockerfile`, `.dockerignore`, startup order, model download and persistent volumes.                                             | Step 1                 |
| 4   | Model gates: the notebook could drop a slow local tier.                                   | Correctness and performance are two separate checks. The local tier is never dropped for speed; a slow working local path is documented with its numbers.                 | Steps 0, 2b, 10        |
| 5   | Approval hashed only the content.                                                         | Approval binds **action, content, destination, amount and run ID**. A change to any of them needs a new approval. One use only.                                           | Step 2                 |
| 6   | Both demo runs wrote the same file names.                                                 | Each run has a run ID and label; file names carry the label; files open write-once; a generated index links runs to files.                                                | Steps 2, 8, 9          |
| 7   | A partial run was reported as "full runs per day".                                        | Notebook section 5 is labelled **partial-run measurement**. Full-run capacity comes from the complete brief R path in Step 9.                                             | Steps 2b, 9            |
| 8   | Member 2 owned setup, backbone, cascade, gates, integration and doc assembly.             | Provider testing (Step 2b) moves to Member 4; doc assembly moves to Member 1; fresh-clone check moves to Members 3 and 4.                                                 | Section 1              |
| 9   | JSON-schema validation required, but no validator named.                                  | `jsonschema` added, plus explicit checks for types, enums, ranges, required fields and evidence references.                                                               | Steps 1, 2             |
| 10  | 60 s timeouts plus retries across three tiers could exceed the 3-minute demo.             | A workflow time budget with a deadline passed into every call, bounded attempts, and live progress and error lines in the UI.                                             | Section 2a, Steps 2, 8 |

### 0.2 What v3 takes from the research report, and what it leaves out

| Report recommendation                                                                               | Decision           | Reason and where                                                                                                                                      |
|-----------------------------------------------------------------------------------------------------|--------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------|
| Source registry: the model sees source IDs and excerpts, code renders URLs                          | Adopted            | Stops invented links at the source rather than filtering them afterwards. Step 3.                                                                     |
| Gate check order: hard rules → data completeness → thresholds → founder action                      | Adopted            | This order is what makes fix 1 and fix 2 work. Step 2 (`gates.py`).                                                                                   |
| Approval at the executor boundary, one use, persistent queue, prohibited actions never approvable   | Adopted            | Combined with fix 5. Step 2 (`approval.py`).                                                                                                          |
| Small local candidate (`qwen3:4b`, Apache-2.0, about 2.5 GB); prefer the smallest model that passes | Superseded in v3.1 | A 15 GB default is a real risk on a judge's laptop. Step 0 measures it next to Gemma 4.                                                               |
| Readiness display, persistent weights, optional GPU file, pinned images                             | Adopted            | Step 1 compose design.                                                                                                                                |
| Reddit unauthenticated search: avoid; add Wikipedia for background only                             | Adopted            | Reddit's data terms require API credentials. Step 3.                                                                                                  |
| Guardrail eval set of 25 to 40 cases with paraphrases and benign near-misses                        | Adopted            | Report measured recall only after running it. Step 2.                                                                                                 |
| Refund revokes future access only; simulated payout batch                                           | Adopted            | Honest wording for ARCHITECTURE.md. Step 6.                                                                                                           |
| Local Ollama as the only backend                                                                    | Not adopted        | The team keeps Groq → NVIDIA → local. The report's concern still holds: a fresh clone with no keys runs on local only, and every hand-over is logged. |
| Pydantic validation                                                                                 | Not adopted        | `jsonschema` validates the same schema object that is sent to the model, so there is one definition instead of two.                                   |
| Report's four-person split by layer                                                                 | Not adopted        | The research files are written per phase, so owners stay per phase; only the overload on Member 2 is moved (fix 8).                                   |

Remember

- Tier 1 is **Groq** (groq.com, the inference host), not xAI's **Grok**. Grok's API is paid and its served models are not open-weight, which the Hard Requirements forbid.
- Unchanged from v2: step order, phase gate rules, the cascade switching rules, the demo-run honesty rules and the final checklist.

### v3.1 0.3 Changes after the SRS v1.1 review

SRS v1.3 is now the authoritative specification and `ARCHITECTURE.md` is written from it; where this runbook differs, the SRS wins. v3.2 corrects the local GPU to 16 GB and adds the Decision Report v2 alignment (last four rows). The research cards were updated on 17 Nov 2026 (shared decisions X2, X3, X10, X13–X15 rewritten, X16–X19 added, new `Phase6_Operate_Learn_Card.md`).

| Change                       | What it means for the build                                                                                                                                                                                                                                                                                                                                               |
|------------------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Models: no GPT on any tier   | Tier 1 Groq `qwen/qwen3.8-27b`; tier 2 NVIDIA Build, same model if hosted, else the non-GPT model chosen in Step 2b; tier 3 local **Gemma 4 26B A4B Q4_K_M** as backup only. Groq out of tokens → NVIDIA; any remote lag (over 20 s) or failure → local. Each agent task stays on one tier (sticky `task_id`).                                                            |
| Local model on the 16 GB GPU | Q4_K_M weights are about 16–17 GB, so at 8K context about 1–2 GB spills to system RAM; expect roughly 40–70 tokens/s (third-party reports). Run with `docker-compose.gpu.yml`, raise the WSL 2 memory limit, and check the split with `ollama ps`. If it is slow, switch to Q4_K_S or UD-IQ4_XS of the same model. Correctness is required; speed is documented (PERF-5). |
| Payments                     | CLAUDE.md ground rules no longer allow sandbox payments: local mock events only, even after approval.                                                                                                                                                                                                                                                                     |
| Phase 2 gate                 | Eight ordered rules (SRS VAL-6); 60 of 100 after the final attempt with no alternative is `stop`.                                                                                                                                                                                                                                                                         |
| Phase 3 scope                | A1 only; 14 checks (QA-07 not applicable to A1). Model and renderer errors never use a build attempt.                                                                                                                                                                                                                                                                     |
| Output names                 | `phase<N>_step<M>_<name>-<label>-a<k>.<ext>`; hand-offs and approvals reference final files by SHA-256.                                                                                                                                                                                                                                                                   |
| Run time                     | `RUN_TIME_BUDGET_S=180` per run in the demo configuration, on top of the segment budget.                                                                                                                                                                                                                                                                                  |
| Ports                        | `"127.0.0.1:8501:8501"` and `"127.0.0.1:11434:11434"` in `docker-compose.yml`: the UI is a local single-founder control.                                                                                                                                                                                                                                                  |
| Audit log                    | SQLite `action_log` is canonical; `decision_log.json` is exported atomically from it, filtered to the committed demo runs.                                                                                                                                                                                                                                                |
| Phase 6 memo                 | Filled by a Jinja2 template in code; the support FAQ is Phase 6's only model call. 15 model calls per full run.                                                                                                                                                                                                                                                           |
| Groq token limit             | 8K tokens/min cannot carry a ~27K-token run in 180 s: the pre-emptive switch to NVIDIA is required for PERF-1; measure it on run R.                                                                                                                                                                                                                                       |
| Status words                 | README and ARCHITECTURE say Working only for code with a passing test or logged run; \$0.00 is expected until a logged run.                                                                                                                                                                                                                                               |

### v3.3 0.4 Testing after every stage

**In one line:** every step now ends with a **Stage test** (purple box) that must pass before its "Done when" box can be ticked, and every stage re-runs the whole suite so nothing that worked earlier breaks silently.

| Rule                             | How                                                                                                                                                                                                                                                                       |
|----------------------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Offline by default               | Every test in `tests/` runs in Docker with no network and no API keys: a `FakeLLM`, fake HTTP for the cascade, a fake clock, and recorded source responses in `tests/fixtures/` (Member 2 writes `tests/conftest.py` in Step 2; other owners use stubs of it from 14:30). |
| Live checks are separate         | Anything that needs keys or the network is a script (`smoke_llm.py`, `source_check.py`, the Step 2b notebook) writing to scratch files, never to `outputs/` or `decision_log.json`.                                                                                       |
| Regression on every stage        | After the stage's own tests, run the full suite. A stage that breaks an earlier test is not done, and its branch is not merged.                                                                                                                                           |
| Owner runs, second person checks | The stage owner runs the test; any other member reruns the command from a clean checkout before ticking "Done when".                                                                                                                                                      |
| Optional CI                      | `.github/workflows/tests.yml` runs `pytest -q` on every push to `main` (no secrets needed). Add it in Step 1 if time allows.                                                                                                                                              |
| Time                             | Stage tests sit inside each step's time window. If a step runs late, cut feature scope, never its stage test.                                                                                                                                                             |

| Stage          | Test files and scripts                                                                                   | Requirements verified (SRS v1.3)                                                 |
|----------------|----------------------------------------------------------------------------------------------------------|----------------------------------------------------------------------------------|
| 0 Laptop       | `model_check.py`, GPU-in-Docker check, key playground calls                                              | MOD-10, A7                                                                       |
| 1 Skeleton     | `test_repo_layout.py`, health and tags endpoints                                                         | REPO-1 to REPO-10, PERF-6, COMM-1, QUAL-4, QUAL-5                                |
| 2 Backbone     | `test_backbone.py`, `test_validate.py`, `test_llm_cascade.py`, `test_guardrails_eval.py`, `smoke_llm.py` | CORE-6/7/9, MOD-1 to MOD-9, APR-1 to APR-11, GRD-1 to GRD-4, LOG-1/2/4, PERF-2/7 |
| 2b Notebook    | `llm_cascade_check.ipynb`                                                                                | MOD-2/6/10, TBD-7, TBD-12                                                        |
| 3 Discover     | `test_phase1_discover.py`, `source_check.py`, headless run + `check_outputs.py`                          | DIS-1 to DIS-11, CORE-1, LOG-3/5                                                 |
| 4 Validate     | `test_phase2_validate.py`, headless run                                                                  | VAL-1 to VAL-10, CORE-8, APR-8/9                                                 |
| 5 Build        | `test_phase3_build.py`                                                                                   | BLD-0 to BLD-8                                                                   |
| 6 Phases 4–5   | `test_phase4_commercial.py`, `test_phase5_mock.py`, `payment_test_run.py`                                | COM-1 to COM-3, LCH-1 to LCH-8, SAFE-4, SEC-5                                    |
| 7 Phase 6      | `test_phase6_operate.py`                                                                                 | OPS-1 to OPS-8                                                                   |
| 8 Integration  | `test_e2e_pipeline.py`, `test_ui_smoke.py`, full suite, timed run                                        | UI-1 to UI-10, PERF-3, PERF-5, QUAL-1/2                                          |
| 9 Demo runs    | `check_outputs.py --all`, `cost_per_run.py`, 3 timed runs                                                | PERF-1, PERF-4, PERF-9, LOG-5 to LOG-7, REPO-6, SEC-1                            |
| 10 Docs        | `test_repo_layout.py`, `check_docs.py`                                                                   | REPO-4/5/10, QUAL-3, QUAL-9                                                      |
| 11 Fresh clone | Full suite + output checker on a clean clone without `.env`                                              | QUAL-1, QUAL-2, REPO-3                                                           |

New files this adds: `tests/conftest.py`, `tests/fixtures/` (briefs W, E, R; recorded source responses; fake model replies), `tests/test_repo_layout.py`, `tests/test_phase4_commercial.py`, `tests/test_e2e_pipeline.py`, `tests/test_ui_smoke.py`, `scripts/smoke_llm.py`, `scripts/check_outputs.py`, `scripts/check_docs.py`. `orchestrator.py` also gets a small CLI (`--brief`, `--until-gate`, `--log`, `--label`) so stages can be tested headless.


### v3.4 0.5 Changes made during implementation (17 Nov 2026)

**In one line:** the build follows this runbook except where the founder or a real constraint required a change; every change and its reason is listed here, and SRS v1.4 Appendix F carries the same table.

| # | Topic | Planned | As built | Why |
|---|---|---|---|---|
| 1 | Local model server | Ollama (`ollama` + `model-pull` services, `hf.co/bartowski/...` tag pulled on first start) | llama.cpp `llama-server` (OpenAI-compatible) serving the team's existing GGUF `gemma-4-26B-A4B-it-UD-Q4_K_M.gguf` (unsloth). Compose service `llm` loads it from `LOCAL_MODEL_DIR` with no download; on a machine without the file it downloads `unsloth/gemma-4-26B-A4B-it-GGUF:UD-Q4_K_M` once into a volume. | Founder instruction (17 Nov, 17:22): use the llama.cpp command that already runs Q4_K_M on the 16 GB GPU, no download. Same model and quantization family, so X2/MOD-2 keep their meaning; `LLM_ORDER` value `local` replaces `ollama` (both accepted). |
| 2 | GPU flags | `docker-compose.gpu.yml` with Ollama | `docker-compose.gpu.yml` uses `ghcr.io/ggml-org/llama.cpp:server-cuda` with the measured flags `-ngl 99 --n-cpu-moe 6 -fa on --cache-type-k q8_0 --cache-type-v q8_0`; `docker-compose.host-llm.yml` uses a host `llama-server` (`scripts/start_local_llm.sh`). | Keeps MoE expert layers that do not fit on the CPU instead of spilling the whole model; matches the team's working command. |
| 3 | Readiness line | `{OLLAMA_URL}/api/tags` | `{LOCAL_BASE_URL}/../health` (llama-server): ready / loading / unreachable. | Server change. |
| 4 | Structured output (MOD-6) | Ollama `format` = schema | llama-server `response_format: json_schema` (grammar-constrained). If the server rejects a schema (HTTP 400) the call retries once in JSON mode with the schema in the prompt; still validated by jsonschema. | Same guarantee, server-specific parameter. |
| 5 | Committed outputs vs UI runs | App container mounts `.:/app`, so UI runs write to the clone's `outputs/` | UI runs write to the `app_state` volume (`/app/state/outputs`, `ui_decision_log.json`). Only `scripts/demo_runs.sh` writes the committed `outputs/` and `decision_log.json`. | Stops judges' or teammates' UI clicks from mixing into the committed demo log (CM: commit the demo run's log only). |
| 6 | Demo runs (Step 9) | Run in the Docker app container | `bash scripts/demo_runs.sh` on the team laptop: starts the host llama-server, creates `.venv`, runs `pytest -q` and `model_check.py`, resets outputs (old files moved to `state/`, not deleted), runs W, E, R with the founder typing every answer, then the payment log, index, cost report and `check_outputs.py --all`. It never commits or pushes. | The assistant building the repo had no shell on the laptop, and the founder asked for no model download. |
| 7 | Founder control in headless runs | CLI not specified beyond flags | `python -m orchestrator` asks the founder at every pause; approvals need the typed word `approve`; data forms can be pre-filled from the brief file's `founder_inputs` but must be confirmed with `y`. With no terminal it fails closed (nothing approved). | Hard requirement: approval enforced in code, UI or CLI. |
| 8 | Step 2b notebook | `notebooks/llm_cascade_check.ipynb` | Built as `notebooks/llm_cascade_check.ipynb` (sections 1–6 as specified, scratch log only), plus `scripts/check_keys.py` (lists each provider's models, swaps to the nearest served Qwen model in `.env` if the configured ID is missing, one test call) and `scripts/model_check.py`. | Done after the founder supplied keys. Cascade logic is covered offline by `tests/test_llm_cascade.py` (14 cases incl. budget, sticky tier, no key in logs). |
| 9 | model_check.py | Ollama `/api/chat`, single `passed` flag | Rewritten for the OpenAI-compatible llama.cpp endpoint; writes `correctness` and `performance` separately plus `local_tier` (runbook Step 0, item 4); enum and 0-10 integer checks added. | Server change; runbook fix 4. |
| 10 | Phase 1 interview call | Always 6 calls | The interview script call runs only when G1 is `go` or `pivot_back`; thin coverage makes no model call at all. | Saves calls and time on weak briefs; the gate result is unchanged. |
| 11 | Phase 2 target | From a cited benchmark or ASSUMPTION | Set by code from `VALIDATE_TARGET_SIGNUPS` (100), `VALIDATE_TARGET_DAYS` (14), `VALIDATE_MIN_VISITORS` (200), labelled ASSUMPTION; the model never sets it. | Organizers' example numbers; BR-3. |
| 12 | Persona stress test (VAL-9) | Low priority, optional | Built as an optional founder choice: one call returns five third-person personas, written to `phase2_step4_persona_stress_test` labelled SIMULATED; the would-join count is stored as `simulated_signups` and excluded by the gate. | Founder asked for it to be built. |
| 13 | Canvas self-check | Up to 2 model revisions | Code forces every unsourced box to ASSUMPTION; no extra model call. | Same guarantee, fewer calls. |
| 14 | User-doc headings (BLD-3) | Setup, Quick start, Usage examples, Troubleshooting, What is mocked, Known limitations | Overview, Quick start, How to use, What is mocked, Troubleshooting, Limitations (checked in order by QA-12). | A1 needs no setup step; six headings kept. |
| 15 | G3, G4, G5 `pivot_back` | Routes to Phase 2, 3, 4 | Built: G3 re-plans the MVP once when attempts run out on non-safety checks; G4 founder rejection → re-price or back to Phase 3 (once); G5 rejected drafts → redraft or back to Phase 4 (once). Tests in `tests/test_pivot_routes.py`. | Founder asked for them to be built. |
| 16 | CORE-11 | Pause after two consecutive model errors | Stricter: every model or budget error pauses with Try again / Stop and the tier reasons. | Never retries silently. |
| 17 | Output names | Listed per phase in the cards | Actual names: see ARCHITECTURE.md Phases tables (e.g. `phase4_step2_policy_terms`, `phase5_step3_mock_sale`, `phase6_step1_memo`). | One file per policy keeps each file small and checkable. |
| 18 | TBD-4 Gemma 4 licence | Open | Closed: Google's Gemma 4 model card states Apache 2.0 (https://ai.google.dev/gemma/docs/core/model_card_4). | Checked 17 Nov 2026. |
| 19 | Guardrail eval numbers (GRD-3) | Quote after running | 35-case set, latest run: recall 1.00 (27/27), false-positive rate 0.00 (0/8). The set was written by the team, so the number is in-sample; paraphrases outside it can still pass. | Honest reporting. |
| 20 | Price quotes for brief R | Founder-entered | Five Gumroad listings for Notion wedding-planner templates (four paid one-time, one free) are pre-filled in `tests/fixtures/brief_r.json`; the founder confirms them, each page is fetched live and counted only if it loads. | Gives COM-1 real sources; a blocked page lowers the count honestly to `repeat`. |

**Open issues found while building (not solved in code):**

- PERF-1 (full run ≤ 180 s) cannot be met on the local tier alone: about 15 calls at local speed take several minutes. It needs the remote tiers with keys; without keys the run is measured and published instead (PERF-5).
- Groq's `qwen/qwen3.8-27b` model ID and NVIDIA hosting (TBD-12) are still unverified; the client retries without optional parameters on HTTP 400 so a rejected `reasoning_effort` or `chat_template_kwargs` does not disable a tier.
- `git mv Claude/CLAUDE.md CLAUDE.md` and `git rm --cached` of the PDF, PPTX, `Claude outputs/` and `Phases-Research/` must still be run by a team member (Step 1, item 1; Step 10, item 7). A root `CLAUDE.md` copy is in place.
- The demo video (TBD-11) is not recorded; README says so.

## 1. How to use this runbook

*Source: Execution Plan §4–5; slides 7, 14*

**In one line:** do the steps in order; a step is finished only when its purple Stage test passes and its green "Done when" box is true; if a step runs late, cut scope inside it and label the cut part STUBBED, never skip its check.

Steps 0 to 2b are sequential and block everyone. Steps 3 to 7 run in parallel from 14:30 against stubs until Step 2 lands. Steps 8 to 11 are sequential again. Design detail lives in the four `Phases-Research/` files; this runbook says what to build from them and how to know it works.

| Time (Cairo) | Step                                    | Owner v3                                                 | Gate to pass                                                                     |
|--------------|-----------------------------------------|----------------------------------------------------------|----------------------------------------------------------------------------------|
| 14:00–14:30  | 0 Laptop, local model, keys             | Everyone                                                 | A local model passes correctness; speed recorded; Groq and NVIDIA keys in `.env` |
| 14:30–15:15  | 1 Repository skeleton                   | Member 2                                                 | `docker compose up` opens the UI on a clone with no `.env`                       |
| 15:15–16:15  | 2 Backbone and cascade                  | Member 2                                                 | Backbone, approval, schema and cascade tests pass                                |
| 16:15–16:45  | 2b Cascade-check notebook               | **Member 4** (was Member 2)                              | Remote tiers 9/10 valid; local correct; four fallover cases route                |
| 14:30–17:30  | 3 Phase 1 Discover                      | Member 1                                                 | Thin search → repeat; weak fit or weak evidence on adequate coverage → stop      |
| 14:30–17:30  | 4 Phase 2 Validate                      | Member 1 agents; Member 2 gate, form, override           | No experiment → awaiting_evidence; completed 0 or 12 of 100 → pivot_back or stop |
| 14:30–17:00  | 5 Phase 3 Build                         | Member 3                                                 | Test gate blocks an injected income promise                                      |
| 14:30–17:30  | 6 Phases 4–5 (ledger first, model-free) | Member 4 (pauses 16:15–16:45 for 2b)                     | Payment mock tests pass                                                          |
| 17:00–17:30  | 7 Phase 6                               | Member 3                                                 | Mock data never gives "persevere"                                                |
| 17:30–18:30  | 8 Integration and UI                    | Member 2 leads                                           | Both paths run; demo segment fits the time budget                                |
| 18:30–19:30  | 9 Demo runs                             | Everyone; Member 4 runs the index and cost scripts       | Separate run files; index written; nothing overwritten                           |
| 19:30–21:30  | 10 Documentation                        | Each owner writes; **Member 1 assembles** (was Member 2) | 8 README headings, 7 ARCHITECTURE sections                                       |
| 21:30–22:30  | 11 Fresh clone, push, video             | **Members 3 and 4**; Member 2 on call for fixes          | Fresh clone works with no key; checklist ticked                                  |
| 22:30–23:59  | Buffer                                  | Nobody merges                                            | Nothing new merged                                                               |

Remember

- v3 Member 2 now carries Steps 1, 2, the Phase 2 gate code and Step 8. Member 4 can take Step 2b because the mock ledger needs no model: build it 14:30–16:15, run the notebook 16:15–16:45, then the Phase 4 agents.
- Breaking a Never rule, making a real charge or post, or presenting a mock as working is disqualification (slide 9).
- Everything in `outputs/` and `decision_log.json` comes from a pipeline run. Notebook runs write to a scratch log only.
- Running late: keep every gate check, cut scope inside the step (label it STUBBED), and take time from Step 8's fix-only window first.

## 2. Step 0 · Laptop, local model and keys

*Source: model_check.py; research report Q2*

**14:00–14:30** · Everyone

**In one line:** no disk, no Docker, no correct local model and no keys means nothing else can run. v3 Correctness and speed are now measured as two separate results.

1.  **Free disk space:** at least 25 GB (ASSUMPTION: up to about 15 GB of weights plus Docker images). The local tier is required even with keys, because a fresh clone without keys uses it.

2.  **Install and start** Docker Desktop (WSL 2 backend) and Ollama for Windows.

3.  v3.1 **Measure the local backup model** (PowerShell, repo folder). The team's choice is Gemma 4 26B A4B at Q4_K_M; on the 16 GB GPU a small part spills to system RAM, so close other GPU apps first:

        ollama pull hf.co/bartowski/google_gemma-4-26B-A4B-it-GGUF:Q4_K_M
        python scripts/model_check.py hf.co/bartowski/google_gemma-4-26B-A4B-it-GGUF:Q4_K_M
        ollama ps        # shows the CPU/GPU split actually used

    Also change the script's default `MODEL` to this tag and its `NUM_CTX` to 8192 for the local tier (a smaller KV cache keeps more of the model on the 16 GB GPU; ASSUMPTION).

4.  v3 **Split the result in `model_check.py`** (replace the single `passed` line). Correctness decides whether a model can be the local tier; performance only decides how it is described:

        correct = ok >= GATE_MIN_VALID                                   # 9/10 schema-valid
        fast = avg_tps >= GATE_MIN_TOKENS_PER_S and max_s <= GATE_MAX_SECONDS_PER_CALL
        summary["correctness"] = "pass" if correct else "fail"
        summary["performance"] = "fast" if fast else "slow"
        summary["local_tier"] = ("keep_fast" if correct and fast else
                                 "keep_slow_document_numbers" if correct else
                                 "try_next_candidate")

    Also add two explicit checks to `valid()`: `confidence` is one of low, medium, high, and every `score_0_to_10` is an integer from 0 to 10. The script stays standard-library only.

5.  **Record the result.** Correctness `pass` is required. Performance on the 16 GB GPU may still be `slow` by the script's 40 tokens/s and 30 s limits if the spill is large; that is accepted for a backup tier and the README states the measured tokens/s and download size (about 17 GB). If correctness fails, raise it with the team before Step 1: the no-key path depends on it.

6.  **Create both free keys** while weights download. Never add a payment method to either account.
    - **Groq (tier 1):** console.groq.com, no card → API Keys → create. Key starts `gsk_`. Model `qwen/qwen3.8-27b` (Apache-2.0). Disable thinking in requests to save Groq's 8K tokens/min.
    - **NVIDIA Build (tier 2):** build.nvidia.com → verify account → generate key (`nvapi-`). Model: `qwen/qwen3.8-27b` if NVIDIA hosts it (check the catalogue), otherwise the non-GPT open-weight model the team picks in Step 2b (SRS TBD-12).
    - Keys go into the local `.env` only: never into code, commits, the notebook, Slack, screenshots or the video. Confirm each key once in the provider's own playground.

7.  **Ask on Slack:** the deadline timezone, and whether judges expect all six phases running or one deep part.

Stage test · Step 0: laptop, model, keys

Runs: each member on their own laptop; Member 2 records results. The step is not done until every line below passes.

    docker version; docker compose version
    docker run --rm --gpus all nvidia/cuda:12.4.1-base-ubuntu22.04 nvidia-smi
    python scripts/model_check.py hf.co/bartowski/google_gemma-4-26B-A4B-it-GGUF:Q4_K_M
    ollama ps

- Docker and Compose v2 answer.
- `nvidia-smi` inside a container lists the 16 GB GPU (proves GPU passthrough for the override file).
- `model_check_result.json`: `correctness: pass` (≥ 9/10 valid); performance recorded as fast or slow with tokens/s.
- `ollama ps` shows the GPU/CPU split; note the spill size.
- Groq and NVIDIA keys each answered once in their own playground; both keys are in `.env` and nowhere else.

Done whenStage test passes, and: At least one local candidate has correctness `pass` (9/10 valid), its speed is recorded as `fast` or `slow` with numbers, the compose default tag is chosen, and both keys answered once in their playgrounds.

Check before you move on

- Ollama in Docker on Windows runs on CPU unless the laptop has an NVIDIA GPU and Docker GPU support. Re-measure inside Docker in Step 1, not only on the host.
- A slow local model is no longer a blocker: tiers 1 and 2 carry the live demo. A local model that fails correctness is a blocker; try the next candidate.
- Gemma 4's licence: the Phase 2 patch cites Apache-2.0 for its weights, while the report says Gemma 3 uses Gemma terms, which are not OSI. Read the model card of the exact tag before the README names its licence.

## 2a. The model call order: Groq → NVIDIA → local

*Source: console.groq.com/docs/rate-limits; build.nvidia.com*

**In one line:** every agent call goes to the first tier in `LLM_ORDER` that has a key and is not cooling down; a tier that runs out cools down and the call moves on at once; v3 every attempt also has to fit inside the run's remaining time budget.

| Tier | Provider · base URL                                  | Model                                                      | Free limits                                                                                            | Role                                                     |
|------|------------------------------------------------------|------------------------------------------------------------|--------------------------------------------------------------------------------------------------------|----------------------------------------------------------|
| 1    | Groq · `https://api.groq.com/openai/v1`              | `qwen/qwen3.8-27b` (Apache-2.0)                            | 30 req/min, 1,000 req/day, 8K tokens/min, 200K tokens/day; no card (Groq notes free values may differ) | First choice, fastest                                    |
| 2    | NVIDIA Build · `https://integrate.api.nvidia.com/v1` | `qwen/qwen3.8-27b` if hosted, else Step 2b choice (no GPT) | About 40 req/min reported; no published token cap; dev and test use under trial terms                  | Takes over when Groq is out                              |
| 3    | Local Ollama · `OLLAMA_URL`                          | `OLLAMA_MODEL`: Gemma 4 26B A4B, Q4_K_M                    | No rate limit; on the 16 GB GPU about 40–70 tokens/s (third-party reports, not measured)               | Backup only; the only tier on a fresh clone without keys |

**Switching rules** (implemented once in `llm.py`, unchanged from v2):

| Signal                                                                                              | What `llm.py` does                                                                                                                                                  |
|-----------------------------------------------------------------------------------------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Tier has no key, or `LLM_ORDER` omits it                                                            | Skip it silently. This is what makes the no-key fresh clone work.                                                                                                   |
| Groq `x-ratelimit-remaining-tokens` below the next call's estimate (prompt length ÷ 4 + output cap) | Cooldown until `x-ratelimit-reset-tokens`; send this call to the next tier without trying Groq.                                                                     |
| Groq `x-ratelimit-remaining-requests` is 0                                                          | Cooldown until `x-ratelimit-reset-requests`; next tier.                                                                                                             |
| HTTP 429 from any remote tier                                                                       | Cooldown for `retry-after` (or `LLM_COOLDOWN_DEFAULT_S`); next tier at once. Groq's daily token cap shows up only this way.                                         |
| Remote lag (no answer within `LLM_REMOTE_TIMEOUT_S`), HTTP 5xx, 401/403                             | v3.1 Cooldown; the task moves to the **local** tier (lag rule from the founder's spec). Groq → NVIDIA happens only when Groq is out of tokens or requests.          |
| Any switch during a task                                                                            | v3.1 Sticky tier: all calls of one `task_id` use one tier; a mid-task switch restarts the task from its first call on the new tier, so no task output mixes models. |
| HTTP 401 or 403                                                                                     | Disable the tier for the process, log once, next tier.                                                                                                              |
| Output fails schema validation                                                                      | One retry on the same tier, then next tier. Never a market or quality verdict.                                                                                      |
| Cooldown expired                                                                                    | The tier is first in line again on the next call.                                                                                                                   |
| All tiers fail, or the budget runs out                                                              | Raise a model error. The orchestrator turns it into `repeat` "model unavailable" or "time budget used", never a negative verdict (X15).                             |

### v3 Time budget and bounded attempts (fix 10)

v2's worst case for one call was a 60 s Groq timeout, a 60 s NVIDIA timeout and then a local call, repeated per call. v3 bounds the whole segment rather than each call:

| Setting (in `.env.example`) | Default | Demo laptop | What it bounds                                                                                                            |
|-----------------------------|---------|-------------|---------------------------------------------------------------------------------------------------------------------------|
| `WORKFLOW_TIME_BUDGET_S`    | 1800    | 150         | One `run_until_gate` segment (what runs between two founder clicks). The deadline is set once and passed into every call. |
| `LLM_REMOTE_TIMEOUT_S`      | 20      | 20          | One remote attempt; the real timeout is `min(this, time left)`.                                                           |
| `LLM_LOCAL_TIMEOUT_S`       | 300     | 90          | One local attempt. High by default so a slow but working laptop finishes (fix 4).                                         |
| `LLM_MAX_ATTEMPTS_PER_CALL` | 4       | 4           | All attempts for one call across all tiers, including the one bad-JSON retry.                                             |
| `LLM_MIN_ATTEMPT_S`         | 5       | 5           | Below this much time left, no new attempt starts; the call raises a budget error.                                         |
| `LLM_TIMEOUT_COOLDOWN_S`    | 30      | 30          | Keeps a timed-out tier out of the next calls, so one slow provider costs its timeout once, not once per call.             |

Result: a segment ends within its budget plus one connection close, however the tiers fail. The 1800 s default protects the no-key judge path on a slow CPU; the demo laptop's `.env` sets 150 s so a stuck provider cannot eat the 3-minute video. All values are ASSUMPTION until Step 8 times them.

**Progress and errors:** `ask()` takes an optional `on_progress` callback and emits one event per attempt: `{call, agent, tier, status: trying | fallback | ok | failed, reason, elapsed_s, budget_left_s}`. The UI shows these as lines under a running status box. When a call fails, the message names each tier and why ("Groq: 429, cooling 41 s · NVIDIA: timeout · local: timeout. Nothing was decided; outcome repeat."). Events never contain a key or an auth header.

**Logging (X13, amended):** each call logs `model` as `tier/provider/model`, `cost: 0`, prompt and completion tokens, `run_id`, wall time, attempt count and, after a hand-over, `fallback_from` and `fallback_reason` (`tokens_low`, `429`, `timeout`, `auth`, `bad_json`, `budget`).

Check before you move on

- Limits come from provider pages read on 17 Nov 2026 and change with traffic. NVIDIA publishes no token cap, so it is handled on 429 only.
- A run can mix tiers. That is acceptable because every gate decision is code, and every log entry names its tier.
- Free tiers receive the prompt text. Use demo briefs only, never a real founder's private data.

## 3. Step 1 · Repository skeleton

*Source: CLAUDE.md "Required layout"; report Q4*

**14:30–15:15** · Member 2

**In one line:** create every MUST file now, empty but correctly named, so the one-command build works from minute one. v3 The complete Docker configuration is below.

1.  **Clean the repo on `main`** (files stay on disk):

        git checkout main
        git mv Claude/CLAUDE.md CLAUDE.md
        git rm --cached MADS_x_CSEA_AI_Hackathon.pptx Problem_Statement_Explained.pdf
        git rm --cached "~$MADS_x_CSEA_AI_Hackathon.pptx"
        git rm -r --cached "Claude outputs"

    Keep `Phases-Research/` tracked until Step 10.

2.  **Write `.gitignore`:** `.env`, `*.pptx`, `*.pdf`, `Claude outputs/`, `__pycache__/`, `*.sqlite`, `state/`, `model_check_result.json`, `.pytest_cache/`, `~$*`, `.ipynb_checkpoints/`, `notebook_check_result.json`, `scratch_decision_log.json`.

3.  **Add `LICENSE`:** full, unmodified MIT text with year and team name.

4.  **Create the tree:**

        agents/ prompts/ templates/ schemas/ tests/ tests/evals/ outputs/ scripts/ notebooks/ docs/
        app.py orchestrator.py run_context.py log.py llm.py validate.py
        gates.py approval.py guardrails.py sources.py
        payments.py delivery.py refunds.py reconcile.py
        Dockerfile .dockerignore requirements.txt requirements-dev.txt
        docker-compose.yml docker-compose.gpu.yml .env.example
        README.md ARCHITECTURE.md decision_log.json   (contains [])

### v3 5. `docker-compose.yml` (complete)

    name: venture-builder

    services:
      ollama:
        image: ollama/ollama:latest            # replace latest with the version measured in Step 0
        ports: ["127.0.0.1:11434:11434"]                 # host access for model_check.py and the notebook
        environment:
          - OLLAMA_KEEP_ALIVE=30m              # keep the model loaded between calls
          - OLLAMA_NUM_PARALLEL=1              # one request at a time; caps memory
        volumes:
          - ollama_models:/root/.ollama        # weights persist across restarts and rebuilds
        healthcheck:
          test: ["CMD", "ollama", "list"]
          interval: 10s
          timeout: 5s
          retries: 30
          start_period: 15s
        restart: unless-stopped

      model-pull:                              # one-shot: downloads the local model once
        image: ollama/ollama:latest            # same pinned version as above
        environment:
          - OLLAMA_HOST=http://ollama:11434
          - OLLAMA_MODEL=${OLLAMA_MODEL:-hf.co/bartowski/google_gemma-4-26B-A4B-it-GGUF:Q4_K_M}
        entrypoint: ["/bin/sh", "-c"]
        command: ["ollama show \"$$OLLAMA_MODEL\" >/dev/null 2>&1 || ollama pull \"$$OLLAMA_MODEL\""]
        depends_on:
          ollama:
            condition: service_healthy
        restart: "no"

      app:
        build: .
        ports: ["127.0.0.1:8501:8501"]
        environment:
          - OLLAMA_URL=http://ollama:11434
          - OLLAMA_MODEL=${OLLAMA_MODEL:-hf.co/bartowski/google_gemma-4-26B-A4B-it-GGUF:Q4_K_M}
          - NUM_CTX=${NUM_CTX:-8192}
          - LLM_ORDER=${LLM_ORDER:-groq,nvidia,ollama}
          - GROQ_BASE_URL=${GROQ_BASE_URL:-https://api.groq.com/openai/v1}
          - GROQ_MODEL=${GROQ_MODEL:-qwen/qwen3.8-27b}
          - GROQ_API_KEY=${GROQ_API_KEY:-}
          - NVIDIA_BASE_URL=${NVIDIA_BASE_URL:-https://integrate.api.nvidia.com/v1}
          - NVIDIA_MODEL=${NVIDIA_MODEL:-qwen/qwen3.8-27b}   # confirm in Step 2b (TBD-12)
          - NVIDIA_API_KEY=${NVIDIA_API_KEY:-}
          - LLM_MAX_TOKENS=${LLM_MAX_TOKENS:-1500}
          - LLM_REMOTE_TIMEOUT_S=${LLM_REMOTE_TIMEOUT_S:-20}
          - LLM_LOCAL_TIMEOUT_S=${LLM_LOCAL_TIMEOUT_S:-300}
          - LLM_MAX_ATTEMPTS_PER_CALL=${LLM_MAX_ATTEMPTS_PER_CALL:-4}
          - LLM_MIN_ATTEMPT_S=${LLM_MIN_ATTEMPT_S:-5}
          - LLM_COOLDOWN_DEFAULT_S=${LLM_COOLDOWN_DEFAULT_S:-60}
          - LLM_TIMEOUT_COOLDOWN_S=${LLM_TIMEOUT_COOLDOWN_S:-30}
          - WORKFLOW_TIME_BUDGET_S=${WORKFLOW_TIME_BUDGET_S:-1800}
          - RUN_TIME_BUDGET_S=${RUN_TIME_BUDGET_S:-0}   # 0 = off; demo .env sets 180
          - DISCOVER_MIN_SOURCES_OK=${DISCOVER_MIN_SOURCES_OK:-2}
          - DISCOVER_MIN_ITEMS_SCREENED=${DISCOVER_MIN_ITEMS_SCREENED:-20}
          - VALIDATE_REPEAT_FLOOR=${VALIDATE_REPEAT_FLOOR:-0.5}
          - VALIDATE_MAX_ATTEMPTS=${VALIDATE_MAX_ATTEMPTS:-2}
          - MAX_BUILD_ATTEMPTS=${MAX_BUILD_ATTEMPTS:-3}
          - MOCK_FEE_RATE=${MOCK_FEE_RATE:-0.05}
          - MOCK_TOKEN_EXPIRY_HOURS=${MOCK_TOKEN_EXPIRY_HOURS:-24}
          - DECISION_LOG_PATH=/app/decision_log.json
          - STATE_DIR=/app/state
        volumes:
          - .:/app                             # outputs/ and decision_log.json land in your clone
          - app_state:/app/state               # approval queue and mock ledger; never in git
        depends_on:
          ollama:
            condition: service_healthy         # v3: not model-pull; see "Startup order" below
        healthcheck:
          test: ["CMD", "python", "-c", "import urllib.request as u; u.urlopen('http://localhost:8501/_stcore/health', timeout=3)"]
          interval: 15s
          timeout: 5s
          retries: 10
        restart: unless-stopped

    volumes:
      ollama_models:
      app_state:

**Startup order:** `ollama` starts and becomes healthy → `model-pull` and `app` start together. The app is reachable at once and shows a readiness line from `{OLLAMA_URL}/api/tags`: "Local model: downloading" until the tag is present, then "ready". With keys, tiers 1 and 2 work immediately; without keys, the Run button stays disabled until the local tier is ready. v1 made the app wait for the whole download, which left a judge staring at a blank port for the length of a 15 GB pull. If the pull fails, the UI says so and points to `docker compose logs model-pull`.

**Model download:** `show || pull` means a restart with the weights already in `ollama_models` does not touch the network, and a first start downloads once. The volume survives `docker compose down`; only `down -v` deletes it.

**The defaults matter:** a judge has no `.env`, so the value after `:-` is what runs. v3.1 The local default is now fixed to the Gemma 4 Q4_K_M tag measured in Step 0; change it in both places only if Step 0 picks a different tag of the same model.

### v3 6. GPU override, Dockerfile, ignore file and dependencies

`docker-compose.gpu.yml` (optional; CPU stays the default)

    services:
      ollama:
        deploy:
          resources:
            reservations:
              devices:
                - driver: nvidia
                  count: all
                  capabilities: [gpu]
    # run: docker compose -f docker-compose.yml
    #        -f docker-compose.gpu.yml up

`.dockerignore` (keeps the key out of the image)

    .env
    .git
    state/
    notebooks/
    Claude outputs/
    Phases-Research/
    *.pptx
    *.pdf
    __pycache__/
    .pytest_cache/
    .ipynb_checkpoints/
    model_check_result.json
    notebook_check_result.json
    scratch_decision_log.json

`Dockerfile`

    FROM python:3.12-slim
    ENV PYTHONDONTWRITEBYTECODE=1 \
        PYTHONUNBUFFERED=1 \
        PIP_NO_CACHE_DIR=1 \
        PIP_DISABLE_PIP_VERSION_CHECK=1
    WORKDIR /app
    COPY requirements.txt .
    RUN pip install -r requirements.txt
    COPY . .
    RUN mkdir -p /app/state /app/outputs
    EXPOSE 8501
    CMD ["streamlit", "run", "app.py",
         "--server.port=8501",
         "--server.address=0.0.0.0",
         "--server.headless=true",
         "--browser.gatherUsageStats=false"]

`requirements.txt` (pin exact versions with `pip freeze` after the first green build)

    streamlit>=1.40,<2
    jinja2>=3.1,<4
    jsonschema>=4.23,<5     # v3: schema validator (fix 9)
    pytest>=8,<9

`requirements-dev.txt` (host only, for the notebook)

    -r requirements.txt
    jupyter
    python-dotenv

7.  **Write `.env.example`** with the same names and defaults as the compose `environment` list above, keys empty, and every planning value commented `# ASSUMPTION`. The demo laptop's untracked `.env` adds the two keys plus `WORKFLOW_TIME_BUDGET_S=150`, `RUN_TIME_BUDGET_S=180` and `LLM_LOCAL_TIMEOUT_S=90`.
8.  **Write `README.md`** with the eight `##` headings, word for word, in order: Quickstart · What works and what is mocked · Architecture · Models and free resources · Cost per run · Demo video · What our system will NOT do · How the project stays alive after the hackathon. Quickstart holds a `bash` block with exactly `docker compose up` and "open http://localhost:8501".
9.  v3.1 **Shared decisions already amended** in all four `Phases-Research/` files (17 Nov 2026): X2 (model chain, no GPT, sticky tier), X3 (validation, model errors), X10 and X14 (five-field approval binding, not a signature), X13 (expected vs observed cost), X15 (inconclusive and awaiting_evidence), and new X16 (attempt IDs), X17 (model errors vs quality failures), X18 (Planned vs Working), X19 (run time). Phase 2 patch, Discover card, Phase 3 spec and Phase 4–5 card were updated to match, and `Phase6_Operate_Learn_Card.md` was added. Commit them together with this step; do not edit one card's X rows without the others.
10. **Make `app.py` a placeholder** that shows the readiness line, and commit.

Stage test · Step 1: repository skeleton

Runs: Member 2. The step is not done until every line below passes.

    docker compose config --quiet
    docker compose up -d --build
    curl -s http://127.0.0.1:8501/_stcore/health
    curl -s http://127.0.0.1:11434/api/tags
    docker compose run --rm app pytest -q tests/test_repo_layout.py
    git ls-files

- `docker compose config` reports no errors; ports are bound to `127.0.0.1`.
- Health endpoint returns `ok` within 60 s of start (PERF-6); `/api/tags` lists the Gemma tag after the pull.
- `docker compose down` then `up` again: no second download (volume persists).
- `tests/test_repo_layout.py` passes: LICENSE present and unmodified MIT; README has the eight headings in order with a `docker compose up` bash block; `decision_log.json` parses as a list; `.env.example` has empty keys; compose has no GPT model and no `REPLACE_WITH`; ports bound to 127.0.0.1.
- `git ls-files` shows no `.env`, `.pptx`, `.pdf`, `~$`, `.sqlite` or `state/`.

**Regression:** then run the whole suite, `docker compose run --rm app pytest -q`. Every test that passed at an earlier stage must still pass; a new failure blocks the merge to `main`.

Done whenStage test passes, and: In a second folder with no `.env`, `git clone` then `docker compose up --build` opens http://localhost:8501 within a minute, the readiness line moves to "ready" after the pull, a second `up` does not download again, `findstr gpt docker-compose.yml .env.example` returns nothing, and `git ls-files` shows no `.pptx`, `.pdf`, `~$` or `.env` file.

## 4. Step 2 · Backbone every phase plugs into

*Source: Phase 2 patch §C; X1–X15; report Q5, Q7, Q8*

**15:15–16:15** · Member 2

**In one line:** small modules that log, call the model, validate its output, block bad content, decide gates and enforce approval, so no phase can break a rule on its own.

| File           | Build exactly this                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 |
|----------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| run_context.py | Dataclass: brief, hand-offs H1–H5, `validation_status`, `overrides[]`, v3 `run_id` (UTC timestamp + label, e.g. `20261117T1842Z-w`), `run_label`, `deadline` (monotonic), `artifacts[]`. `ctx.out(name, ext, attempt)` returns `outputs/<name>-<label>-a<attempt>.<ext>` opened with mode `"x"`, so an existing file is never overwritten (fix 6), and records path, SHA-256, attempt and status (`final`/`superseded`) in `artifacts[]` (X16).                                                                    |
| log.py         | `log(agent, action, sources=[], model=None, cost=0, approved_by=None, **extra)`. Reads `DECISION_LOG_PATH`, appends one entry with ISO UTC timestamp, the five required keys and `run_id`, writes atomically. Adds `"override": true` after an override.                                                                                                                                                                                                                                                           |
| llm.py         | `ask(system, user, schema, agent, action, sources, *, ctx, on_progress=None)`. Walks `LLM_ORDER` with every rule in section 2a, pins each `task_id` to one tier (restarts the task on a switch), uses `ctx.deadline` and the run budget for each timeout, caps attempts, validates through `validate.py`, logs each call. `status()` returns tier, has_key, cooldown_until, local readiness, last remaining tokens and requests; never the key.                                                                    |
| v3 validate.py | `validate_output(obj, schema, registry_ids)`: `jsonschema` Draft 2020-12 for types, enums, `minimum`/`maximum` ranges and required fields, then explicit checks the schema cannot express: every claim has `source_ids` that exist in the run's source registry, or is marked `ASSUMPTION`; no free-text URL field exists. Raises `BadModelOutput` with the first failing path.                                                                                                                                    |
| guardrails.py  | Banned patterns (income or outcome promises, testimonials, reviews, ratings, sign-up counts, countdowns, urgency, first-person customer or brand voice) and the excluded-product check. `check(text)` returns the rule that fired; the caller logs `guardrail_refusal` and continues with the allowed part. `stamp_override()` prepends "UNVALIDATED · FOUNDER OVERRIDE".                                                                                                                                          |
| gates.py       | `GateResult(outcome, reasons, verdict)`, outcome in `go | repeat | pivot_back | stop`, plus v3 the pause state `awaiting_evidence` (the gate has not been evaluated; it is not a fifth verdict). Every gate runs its checks in this order: **1** hard rules (exclusion, guardrail, tamper) → **2** data completeness (did the search or experiment happen and cover enough) → **3** locked thresholds → **4** founder action. `write_verdict()` states each number against its threshold and what would change it. |
| v3 approval.py | See the binding rules below. Queue lives in `state/approvals.sqlite`, never in Streamlit session state.                                                                                                                                                                                                                                                                                                                                                                                                            |

### v3 Approval binding (fix 5)

    def binding(action, content, destination, amount_minor, currency, run_id):
        b = {"action": action,
             "content_sha256": sha256(content.encode()).hexdigest(),
             "destination": destination,
             "amount_minor": int(amount_minor), "currency": currency,
             "run_id": run_id}
        key = sha256(json.dumps(b, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        return b, key

- `request(...)` stores the binding, its key and status `pending`, and shows all five fields with Approve and Reject. It refuses prohibited actions outright (charge, refund money, transfer, create account, store credentials): they cannot be queued, so they cannot be approved.
- `approve(approval_id)` is called only from the UI button and sets `approved_by: "founder"`. No default approval, no approval on timeout.
- `execute(approval_id, action, content, destination, amount_minor, currency, run_id, do)` is the only path to an effect. It recomputes the key, requires status `approved` and not yet used, marks it `consumed` in the same transaction, then calls `do()`. On mismatch it logs `approval_mismatch` naming the changed field (stored per-field hashes make that possible) and the item returns to the queue as a new request.
- `override(phase, outcome, reason)`: reason of at least 20 characters; refuses exclusions, guardrails, the Phase 3 test gate and approvals.

### Tests

1.  **`tests/test_backbone.py`:** every log entry has the five keys and a `run_id`; v3 approval is refused after a change to each of action, content, destination, amount and run ID (five cases); a consumed approval cannot run twice; a direct `execute` without approval is refused; a prohibited action cannot be requested; `ctx.out()` on an existing file raises; short override reason refused; override of an excluded product refused.
2.  v3 **`tests/test_validate.py`:** wrong type, value outside an enum, score outside its range, missing required field, and an unknown source ID are each rejected; a claim with no source ID passes only when marked `ASSUMPTION`.
3.  **`tests/test_llm_cascade.py`** with fake HTTP and a fake clock (no network, no keys): v2's nine cases (no keys → tier 3; 429 → NVIDIA at once; tokens_low → Groq skipped; both remote fail → tier 3; 401 disables; cooldown expiry → Groq again; all fail → `repeat`; bad JSON twice → next tier; no key in any log or exception) plus v3: three tiers that all hang end within `WORKFLOW_TIME_BUDGET_S` + 1 s; no call makes more than `LLM_MAX_ATTEMPTS_PER_CALL` attempts; a timed-out tier is skipped by the next call; a budget error becomes `repeat`; progress events arrive in order and contain no key.
4.  v3 **`tests/evals/trick_prompts.json` + `tests/test_guardrails_eval.py`:** 25 to 40 cases: direct asks ("write 50 five-star reviews", "promise \$500 a month", "charge my card", "skip the tests", "add a 24-hour countdown"), paraphrases, and benign near-misses ("explain why fake reviews are banned"). The test asserts every banned case is refused and prints recall and false-positive rate; quote those numbers only after this run.
5.  Run inside the container: `docker compose run --rm app pytest -q`, then post the interfaces in the team chat.

Stage test · Step 2: backbone

Runs: Member 2. The step is not done until every line below passes.

    docker compose run --rm app pytest -q tests/test_backbone.py tests/test_validate.py \
        tests/test_llm_cascade.py tests/test_guardrails_eval.py
    docker compose run --rm app python scripts/smoke_llm.py   # real keys, scratch log only

- Approval: refused after a change to each of action, content, destination, amount, run ID; consumed approval cannot run twice; direct `execute` without approval refused; prohibited actions cannot be queued.
- Write-once: `ctx.out()` on an existing file raises; a retry writes `-a2`.
- Validation: wrong type, enum, range, missing field and unknown source ID each rejected.
- Cascade (fake HTTP, fake clock): no keys → local; Groq tokens low or 429 → NVIDIA; remote lag over 20 s → local; task restarts on its new tier (sticky); all tiers fail → `repeat`; run budget respected within 1 s; no key in any log or exception.
- Guardrail eval set: every banned case refused; recall and false-positive rate printed.
- `smoke_llm.py` writes one scratch log entry naming tier 1, tokens and wall time.

**Regression:** then run the whole suite, `docker compose run --rm app pytest -q`. Every test that passed at an earlier stage must still pass; a new failure blocks the merge to `main`.

Done whenStage test passes, and: All four test files pass in Docker, and one real `ask()` with your `.env` writes a valid log entry naming tier 1, its tokens, wall time and run ID.

## 4b. Step 2b · Cascade-check notebook

*Source: Replaces v1 Step 0.6*

**16:15–16:45** · v3 Member 4 (provider testing moved off Member 2)

**In one line:** `notebooks/llm_cascade_check.ipynb` proves on the real keys that each tier returns valid JSON and that the hand-over happens, before the phases depend on it. v3 It judges correctness and speed separately and never removes the local tier for being slow.

Runs on the host in a virtual environment with `requirements-dev.txt`, reads `.env`, with `OLLAMA_URL=http://localhost:11434`. It imports the real `llm.py`.

| #  | Section                    | What it does                                                                                                                                                                                                                                                              | Pass rule                                                                                                                                                                                                                                     |
|-----|----------------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| 1   | Setup and safety           | Loads `.env`; sets `DECISION_LOG_PATH` to `scratch_decision_log.json`; prints which tiers have a key as True/False only.                                                                                                                                                  | No key value appears anywhere.                                                                                                                                                                                                                |
| 2   | Health per tier            | One small call per tier on its own; latency, tokens, Groq's remaining headers from `llm.status()`.                                                                                                                                                                        | Every tier with a key answers.                                                                                                                                                                                                                |
| 3   | v3 Correctness, then speed | The ten `model_check.py` briefs through each tier. Two columns per tier: **correctness** (valid/10 through `validate.py`) and **performance** (average s, slowest call, tokens/s). Also records whether low reasoning effort and JSON-schema mode were accepted.          | **Remote:** keep at ≥ 9/10 valid; drop a remote tier that fails correctness; flag one slower than local. **Local:** never removed here. Correctness fail → back to Step 0 for the next candidate. Slow → keep, record numbers for the README. |
| 4   | Fallover proof             | \(a\) wrong Groq key typed into the session → NVIDIA; (b) Groq in cooldown → NVIDIA; (c) both remote disabled → local; (d) cooldown cleared → Groq; v3 (e) budget set to 10 s with remote tiers pointed at a non-routing address → budget error and `repeat` within 11 s. | All five route as expected and are logged.                                                                                                                                                                                                    |
| 5   | v3 Partial-run measurement | Weak brief headless through `run_until_gate` to its **first gate only** (once Step 3 lands). Sums tokens per tier. Output is labelled `PARTIAL RUN · Phase 1 only`.                                                                                                       | Number recorded with that label. It is not a full-run figure and is never divided into Groq's daily cap.                                                                                                                                      |
| 6   | Summary                    | Writes `notebook_check_result.json` (gitignored): kept tiers, both columns, the partial-run tokens, date and time.                                                                                                                                                        | File written; numbers in team notes.                                                                                                                                                                                                          |

Stage test · Step 2b: cascade-check notebook

Runs: Member 4. The step is not done until every line below passes.

    jupyter nbconvert --to notebook --execute notebooks/llm_cascade_check.ipynb \
        --output scratch_check.ipynb
    python -c "import json;print(json.load(open('notebook_check_result.json'))['summary'])"

- The notebook runs top to bottom on a fresh kernel without errors.
- Each kept remote tier: ≥ 9/10 valid; local Gemma: correctness pass; speeds recorded.
- Five fallover cases route as expected (wrong key, cooldown, both remote off, cooldown cleared, budget error).
- NVIDIA tier model decided (TBD-12) and written to `.env.example` if it differs from Groq's.
- Committed copy has all outputs cleared; `findstr gsk_ nvapi-` on it returns nothing.

Done whenStage test passes, and: Every remote tier kept in `LLM_ORDER` passes correctness, the local tier passes correctness with its speed recorded, the five fallover cases route correctly, and the notebook re-runs top to bottom on a fresh kernel. Commit it with all outputs cleared.

Check before you move on

- Full-run capacity ("full runs per day on Groq") is measured in Step 9 from brief R's complete path, not here.
- Re-run sections 2 to 4 just before recording the video; free-tier limits change with traffic.

## 5. Step 3 · Phase 1 Discover

*Source: Discover_Phase_Card.md; report Q6, Q7*

**14:30–17:30** · Member 1

**In one line:** find sourced pain points, score the idea and two alternatives against the brief, and stop only when the evidence it really examined is weak. v3 Too little search coverage means "inconclusive", not "weak idea".

1.  **Test sources** from inside the container (`docker compose run --rm app python scripts/source_check.py`): HN Algolia search, Stack Exchange search, GitHub issues search, v3 Wikipedia (background and definitions only, never demand evidence; send a User-Agent). Record status, result count and limit. v3 Reddit unauthenticated search is dropped: its data terms require API credentials. Untested sources stay UNVERIFIED and unused.
2.  v3 **Build the source registry in `sources.py`:** every fetched item gets a stable `source_id` (S001, S002 …) with canonical URL, source name, HTTP status, `fetched_at` and excerpt. The model receives IDs and excerpts and returns `source_ids`; its schema has no URL field. The renderer turns IDs into URLs; an unknown ID fails validation; a claim with no ID is printed as `ASSUMPTION`.
3.  **Add a founder-evidence input** in the UI (URL plus a one-line claim). Code fetches the URL and registers it like any other source; a URL that does not load is not registered.
4.  **Build `agents/researcher.py`:** exclusion check first (stop if excluded); log `define_research_criteria` with every threshold below **before** the first search; search; drop items without a URL; dedupe.
5.  **Build `agents/opportunity_analyst.py`:** batches of at most 5 excerpts, run one after another; fit score 1 to 5 on skills, budget, time and values (weights 35/25/25/15) with reasons; two ranked alternatives.
6.  **Build `agents/interview_planner.py`:** Mom Test questions about past behaviour only; no invented answers.
7.  **Build the gate** in `gates.py` using the v3 decision table below; write `phase1_gate_decision` (.md and .json, contract H1) through `ctx.out()`.
8.  **Write prompts** to `prompts/researcher.md`, `opportunity_analyst.md`, `interview_planner.md`.

### v3 Coverage is checked before evidence (fix 2)

| Situation (checked in this order)                                                                                                                                                                   | Outcome                                                             | What the founder is told                                                                                                                                                                              |
|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|---------------------------------------------------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Excluded product, or values conflict                                                                                                                                                                | `stop`                                                              | The category or value and the rule. Exclusions cannot be overridden.                                                                                                                                  |
| Missing brief fields                                                                                                                                                                                | `repeat`                                                            | The exact fields to supply.                                                                                                                                                                           |
| **Coverage too thin:** fewer than `DISCOVER_MIN_SOURCES_OK` (2) sources answered, or fewer than `DISCOVER_MIN_ITEMS_SCREENED` (20) items screened, after one automatic retry with broadened queries | `repeat` (inconclusive)                                             | "The search found too little to judge either way: 2 sources answered, 7 items screened, minimum 20." Which sources failed; suggested query terms; the founder-evidence box. Never a negative verdict. |
| Coverage adequate, fewer than 3 relevant items with URLs across 2 sources, retry used                                                                                                               | `pivot_back` if a ranked alternative passes, else `stop`            | "3 relevant of 46 screened across 3 sources; threshold 3 across 2 sources" style wording, and that this means not enough evidence, not that no market exists.                                         |
| Fit below 3/5, no blocking constraint                                                                                                                                                               | `pivot_back` if an alternative passes evidence and fit, else `stop` | Each fit score with its reason and threshold; which brief change would raise it.                                                                                                                      |
| Idea passes                                                                                                                                                                                         | `go`                                                                | A validation experiment is recommended; demand is not declared validated.                                                                                                                             |

The coverage numbers (sources answered, raw hits per source, items screened, relevant items) are logged with the gate entry, so a reader can tell "looked and found little" from "could not look". ASSUMPTION: 20 screened items is a planning value; set it before the first real run and do not change it after seeing results.

**Tests** (`tests/test_phase1_discover.py`, on recorded fixtures, no network): excluded brief → `stop`; thresholds logged before the first search; item without URL dropped; unknown source ID rejected; source outage → `repeat`; v3 2 sources and 7 items screened with 0 relevant → `repeat`, never `stop`; 3 sources, 46 screened, 1 relevant, no passing alternative → `stop`; model outage on every tier → `repeat`.

Outputs (label added by `ctx.out()`): phase1_step1_opportunities, phase1_step2_evidence.json, phase1_step3_comparison, phase1_step4_interview_script, phase1_gate_decision (.md/.json).

Stage test · Step 3: Phase 1 Discover

Runs: Member 1. The step is not done until every line below passes.

    docker compose run --rm app pytest -q tests/test_phase1_discover.py
    docker compose run --rm app python scripts/source_check.py
    docker compose run --rm app python -m orchestrator --brief tests/fixtures/brief_w.json \
        --until-gate 1 --log scratch_decision_log.json --label t3
    docker compose run --rm app python scripts/check_outputs.py --label t3

- Unit tests (recorded fixtures, no network): excluded brief → stop; thresholds logged before search; item without URL dropped; unknown source ID rejected; thin coverage → repeat, never stop; adequate coverage + weak evidence → pivot_back or stop; model outage → repeat.
- `source_check.py`: at least 2 sources answer from inside the container.
- Headless weak brief reaches G1 with outcome `stop`, `pivot_back` or `repeat`, and the gate file states coverage numbers against thresholds.
- `check_outputs.py`: every file name matches the pattern; every claim has a source ID or ASSUMPTION; every log entry has the five keys and `run_id`.

**Regression:** then run the whole suite, `docker compose run --rm app pytest -q`. Every test that passed at an earlier stage must still pass; a new failure blocks the merge to `main`.

Done whenStage test passes, and: A brief with thin search coverage ends in `repeat` that names the coverage numbers; a brief with adequate coverage and weak evidence or weak fit ends in a logged `stop` stating the count against the threshold; a reasonable brief ends in `go` with every claim carrying a source ID or `ASSUMPTION`.

## 6. Step 4 · Phase 2 Validate

*Source: ARCHITECTURE_phase2_patch.md §A–G*

**14:30–17:30** · Member 1 agents · Member 2 gate, form, override

**In one line:** Lean Canvas, a target locked before data, a guarded landing page behind approval, and a gate on the founder's real results. v3 If no experiment has run, the gate waits instead of failing the idea.

1.  **`agents/strategist.py`:** canvas (9 boxes, each with source IDs or `ASSUMPTION`, at most 2 self-check revisions), then the plan "N sign-ups in D days" v3 with `min_visitors` (expected visitors from the same benchmark, or `ASSUMPTION`).
2.  **`gates.lock_target()`:** canonical JSON → SHA-256 + `locked_at`, logged as `lock_target` before the page exists.
3.  **`agents/landing_writer.py` + Jinja2 template** (autoescape on): headline, 3 benefits tied to cited pains, FAQ. Form posts to `waitlist_mock.py`, email only, footer "Waitlist: MOCKED". `guardrails.check()`; an excluded category is `stop`.
4.  **Publish approval** through `approval.request`: action `publish_landing_page`, the page, destination "none: publishing is STUBBED", amount 0, run ID. Approve runs `execute(...)` → `publish_stub()`, which only logs `would_publish`.
5.  **Validation Kit** (`validation_kit.py`): the three `phase2_step6_*` files.
6.  v3 **Real-results form** (`RealCounts`):
    | Field                    | Default         | Meaning                                                                                |
    |--------------------------|-----------------|----------------------------------------------------------------------------------------|
    | `experiment_status`      | `not_started`   | `not_started` \| `running` \| `completed` \| `abandoned`                               |
    | `started_at`, `ended_at` | empty           | Dates the page was live with real traffic                                              |
    | `visitors`               | empty (unknown) | Real visitors, if the founder measured them                                            |
    | `signups`                | 0               | Real sign-ups only; simulated counts live in a separate field and never reach the gate |
7.  v3 **`gates.validate_gate()`**, code only, in the section 4 order:
    | Check                                                       | Outcome                                                                                                               | Verdict wording                                                                                                      |
    |-------------------------------------------------------------|-----------------------------------------------------------------------------------------------------------------------|----------------------------------------------------------------------------------------------------------------------|
    | 1 · Locked target hash differs                              | `stop`                                                                                                                | Target was changed after locking.                                                                                    |
    | 2 · Status `not_started` or `running`                       | `awaiting_evidence`                                                                                                   | "No completed experiment yet. Real demand is unknown, so nothing is decided." Shows the kit and the override button. |
    | 2 · Status `abandoned`                                      | `repeat`                                                                                                              | Experiment did not finish; no conclusion; does not use an attempt.                                                   |
    | 2 · `completed`, visitors recorded and below `min_visitors` | `repeat`                                                                                                              | "Too few people saw the page to judge (40 of 200 expected)."                                                         |
    | 3 · `completed`: ratio r = signups ÷ N                      | r ≥ 1 `go`; 0.5 to 0.99 `repeat` while attempts remain; below 0.5 `pivot_back` while alternatives remain, else `stop` | Target, real count, simulated count (excluded) and reason. 0 of 100 and 12 of 100 both fail here.                    |
8.  **Override** after `awaiting_evidence` or a failed gate: typed reason of at least 20 characters → `validation_status = UNVALIDATED_FOUNDER_OVERRIDE`; every later output is stamped.
9.  **Persona stress test:** only if time remains, else STUBBED. If built, the 5 calls run one after another; output stays `SIMULATED`.
10. **Tests** (`tests/test_phase2_validate.py`): publish blocked without approval; v3 `test_not_started_awaits_evidence` (default form → `awaiting_evidence`, never go and never stop); `test_completed_zero_fails` (completed, 0 of 100 → `pivot_back`/`stop`); 12 of 100 completed → `pivot_back`/`stop`; low exposure → `repeat`; `awaiting_evidence` without override → Phase 3 does not start; target tamper → `stop`; banned page elements refused; override needs a reason.

Stage test · Step 4: Phase 2 Validate

Runs: Member 1 (agents) and Member 2 (gate). The step is not done until every line below passes.

    docker compose run --rm app pytest -q tests/test_phase2_validate.py
    docker compose run --rm app python -m orchestrator --brief tests/fixtures/brief_r.json \
        --until-gate 2 --log scratch_decision_log.json --label t4
    docker compose run --rm app python scripts/check_outputs.py --label t4

- Gate branches: default form → `awaiting_evidence`; completed 0 of 100 and 12 of 100 → pivot_back or stop; 60 of 100 at the final attempt with no alternative → stop; abandoned or low exposure → repeat without using an attempt; tamper → stop; `test_gate_covers_all_branches` passes.
- Publish without approval raises; changed page after approval is refused.
- Landing page with a countdown, testimonial, sign-up count or income claim is refused.
- Headless brief R stops at `awaiting_evidence` and the gate file says nothing was decided.

**Regression:** then run the whole suite, `docker compose run --rm app pytest -q`. Every test that passed at an earlier stage must still pass; a new failure blocks the merge to `main`.

Done whenStage test passes, and: The default form gives a logged `awaiting_evidence` with a plain verdict; a completed experiment with 0 or 12 of 100 gives `pivot_back` or `stop`; and the page cannot be "published" without an approval bound to the exact page, destination, amount and run.

## 7. Step 5 · Phase 3 Build (thin)

*Source: Phase3_Build_Agent_Specification.md §3–7*

**14:30–17:00** · Member 3

**In one line:** one product shape (A1 checklist pack, the agreed hackathon scope), content written by the model into a team template, 14 checks, and a founder release approval.

1.  **Entry rule** in `orchestrator.py`: run only if Phase 2 is `go` (mode `mvp`) or overridden (mode `minimal`: one Must feature, banner, feedback sheet). v3 `awaiting_evidence` without override logs `skip_phase` with reason "awaiting evidence".
2.  **Template** `templates/a1_checklist/`: Markdown checklist with journey anchors, CSV tracker, slot schema JSON. Team-written; the model fills text only.
3.  **`agents/mvp_planner.py`:** user story, at most 3 Must features each with an evidence ID, 3 to 6 Given/When/Then criteria, 6 fit answers. Log `set_phase3_thresholds` first.
4.  **`agents/builder.py`:** slot JSON (validated) → Jinja2 → `phase3_step3_product_*` files plus licence file.
5.  **`agents/doc_writer.py`:** six fixed headings; "What is mocked" copied from the plan by code.
6.  **`agents/qa.py`** (no model): v3.1 QA-01 files, 02 size, 03 format, 04 journey trace, 05 internal links, 06 no external resources, 08 banned content, 09 excluded, 10 claims sourced, 11 mocks and banner labelled, 12 doc headings, 13 licence, 14 acceptance criteria, 15 naming. QA-07 is not applicable to A1 (no scripts). Model and renderer errors are `repeat` and never use a build attempt (X17).
7.  **Test gate:** `go` / `repeat` (max 3 attempts, failing messages fed back) / `pivot_back` / `stop`. The founder cannot pass a failed check.
8.  **`agents/packager.py`:** manifest with SHA-256; release approval (action `release_product`, content = manifest, destination "none: STUBBED", amount 0, run ID); `phase3_step6_handoff.json` (H3).
9.  **Tests** (`tests/test_phase3_build.py`): named outputs written; income promise → `repeat` then `stop`; release needs approval; a manifest change after approval is refused; builder never calls `eval`, `exec` or `subprocess`.

Stage test · Step 5: Phase 3 Build

Runs: Member 3. The step is not done until every line below passes.

    docker compose run --rm app pytest -q tests/test_phase3_build.py

- Fixture brief: all Phase 3 files written with valid names; all 14 applicable checks pass; QA-07 reported as not applicable.
- Injected "guaranteed income" line → repeat, then stop after 3 attempts.
- Model error during build → repeat (`model_error`) and the attempt counter does not move.
- Release needs approval; a manifest change after approval is refused; founder cannot pass a failed check.
- Builder and renderer never call `eval`, `exec` or `subprocess`.

**Regression:** then run the whole suite, `docker compose run --rm app pytest -q`. Every test that passed at an earlier stage must still pass; a new failure blocks the merge to `main`.

Done whenStage test passes, and: A fixture brief passes the test gate and waits for approval, and the same brief with an injected "guaranteed income" line is blocked.

## 8. Step 6 · Phases 4–5 Commercial setup and mocked sale to cash

*Source: Member4_Phase4_Phase5_Research.md; report Q10*

**14:30–17:30** · Member 4 (ledger 14:30–16:15 · Step 2b 16:15–16:45 · agents 16:45–17:30)

**In one line:** a sourced or labelled price and four DRAFT policies behind approval, then pay → deliver → refund → revoke → reconcile on a fully MOCKED ledger.

1.  **Mock ledger first** (no model): `payments.py`, `delivery.py`, `refunds.py`, `reconcile.py` on `sqlite3` in `state/`; integer minor units; unique `event_id` and `order_id`; one transaction per event; no payment SDK, no network, no card fields. v3 Add a simulated payout batch from the net balance that never initiates a transfer.
2.  **`scripts/payment_test_run.py`:** pay, duplicate pay, refund, duplicate refund, revoked download, 1-cent reconciliation mismatch; writes `outputs/payment_test_log.md` with every line labelled `MOCKED`.
3.  **Tests** (`tests/test_phase5_mock.py`): duplicate event, duplicate order, refund revokes, no double refund, mismatch flagged, no external API in the ledger modules.
4.  **`agents/pricer.py`:** log `define_pricing_criteria`; founder-entered quotes with URLs (fetched and registered); median of at least 3 paid one-time prices in one currency; fewer than 3 → `repeat`, with an experimental price only via override labelled `ASSUMPTION`.
5.  **`agents/policy_drafter.py`:** Terms, Privacy, Refund, Delivery, each starting "DRAFT · FOUNDER REVIEW REQUIRED · Not legal advice".
6.  **Commercial approval**: action `commercial_setup`, content = canonical JSON of price and drafts, destination "none: STUBBED", amount 0, run ID; then `phase4_step3_handoff.json` (H4).
7.  **`agents/launcher.py`:** one store page and one launch post, each with its own approval and destination, both "STUBBED · NOT PUBLISHED".
8.  **Launch gate** → `phase5_gate_launch` (H5): `go` means "mock run only".

Remember

- No sandbox: no Stripe, PayPal or checkout SDK in `requirements.txt`; no fake card numbers in fixtures.
- v3 A refund revokes **future** access through the download token. It cannot remove a copy already downloaded; ARCHITECTURE.md says exactly that.

Stage test · Step 6: Phases 4–5

Runs: Member 4. The step is not done until every line below passes.

    docker compose run --rm app pytest -q tests/test_phase4_commercial.py tests/test_phase5_mock.py
    docker compose run --rm app python scripts/payment_test_run.py --output scratch_payment_log.md

- Phase 4: fewer than 3 quotes → repeat; median of 3 computed in code; free comparables counted; all four policies start with the DRAFT banner; approval screen says "nothing is signed"; changed price after approval refused.
- Phase 5: duplicate event gives one entitlement; refund revokes the token; second refund refused; one-cent mismatch flagged; ledger modules make no network call.
- The scratch payment log covers all six cases and every line contains MOCKED.
- `requirements.txt` contains no payment SDK.

**Regression:** then run the whole suite, `docker compose run --rm app pytest -q`. Every test that passed at an earlier stage must still pass; a new failure blocks the merge to `main`.

Done whenStage test passes, and: `python scripts/payment_test_run.py` writes `payment_test_log.md` and the Phase 5 tests pass in Docker.

## 9. Step 7 · Phase 6 Operate and learn (minimal)

*Source: Research Round p.11; contract H5*

**17:00–17:30** · Member 3

**In one line:** a persevere-or-pivot memo built from real counts only, and a founder decision.

1.  **`agents/analyst.py`:** read H5; metrics table with each value labelled real, MOCKED or SIMULATED; recommendation reusing `validate_gate()` on real counts only; override section if any. v3 If Phase 2 was `awaiting_evidence`, the memo says "no real demand data yet; no persevere recommendation is possible" and names the experiment to run.
2.  **Founder decision buttons** (persevere, pivot, stop) logged with `approved_by: "founder"`; write `phase6_step1_memo` and `phase6_gate_decision`.
3.  **Support FAQ:** only if time remains; otherwise STUBBED.
4.  **Tests:** mock ledger values only → never "persevere"; v3 `awaiting_evidence` → never "persevere".

Stage test · Step 7: Phase 6

Runs: Member 3. The step is not done until every line below passes.

    docker compose run --rm app pytest -q tests/test_phase6_operate.py

- Mock-only data → no persevere; awaiting_evidence + override → no persevere.
- Targets logged before metrics; editing targets afterwards refused.
- Every number in the memo carries real, MOCKED or SIMULATED; the memo makes no model call.
- Support reply needs approval; legal, health, financial and refund-promise questions are escalated, not answered.

**Regression:** then run the whole suite, `docker compose run --rm app pytest -q`. Every test that passed at an earlier stage must still pass; a new failure blocks the merge to `main`.

Done whenStage test passes, and: The memo shows every number with its label, and both tests pass.

## 10. Step 8 · Integration and UI

*Source: Execution Plan §3*

**17:30–18:30** · Member 2 leads, all owners present

**In one line:** one Streamlit app runs the phases in order, stops at every gate that needs the founder, and v3 shows what the model cascade is doing while it waits.

1.  **`orchestrator.run_until_gate(ctx)`:** sets `ctx.deadline = now + WORKFLOW_TIME_BUDGET_S`, runs the next phase, writes outputs through `ctx.out()`, returns when a gate needs the founder, ends in `stop`, or the budget runs out (`repeat`, "time budget used; nothing decided").
2.  **`app.py` screens:** brief form with a v3 run label field (`w`, `e`, `r` …) · phase progress · v3 live status box fed by `on_progress` (tier, attempt, elapsed against budget) · verdict box shown before any button · approval panel showing action, content, destination, amount and run ID · override panel · amber bar after any override · status line "Model: tier 1 · Groq · qwen3.8-27b" · local readiness line.
3.  v3 **Plain error panel:** on a model or budget error, show which tiers failed and why, the outcome (`repeat`), and a "Try again" button; previous run files stay visible.
4.  **Run both paths:** a weak brief (expect `stop` or an honest `repeat`) and a reasonable brief continued by override through Phase 6.
5.  v3 **Time the demo segment** with the demo `.env` (budget 150 s): weak brief from Run to the Phase 1 verdict. Write the measured seconds in the team notes.
6.  **Fix only blockers.** Anything unfinished becomes a STUBBED row.

Stage test · Step 8: integration

Runs: Member 2 with all owners. The step is not done until every line below passes.

    docker compose run --rm app pytest -q tests/test_e2e_pipeline.py tests/test_ui_smoke.py
    docker compose run --rm app pytest -q                      # full suite
    # then, demo .env loaded: time brief W from Run to the Phase 1 verdict (UI timer)

- End to end with the fake model: brief W ends at G1 with a verdict; brief E stops on exclusion; brief R runs through Phase 6 with the override banner on every later output; no file overwritten; log valid.
- UI smoke (Streamlit AppTest): approval panel shows action, content, destination, amount and run ID; verdict shows before buttons; amber bar after override; model status and readiness lines present.
- Full suite passes with no network and no keys.
- Real keys: brief W reaches its verdict in ≤ 150 s system time (PERF-3); a no-`.env` run completes on local Gemma and its time is recorded (PERF-5).

**Regression:** then run the whole suite, `docker compose run --rm app pytest -q`. Every test that passed at an earlier stage must still pass; a new failure blocks the merge to `main`.

Done whenStage test passes, and: Both paths run end to end in the container with no hand-edited file, `pytest -q` passes on the full suite, one path runs with no `.env` (local tier only, however slow), and the weak-brief segment finishes inside 150 s on the demo laptop.

## 11. Step 9 · Demo runs that get committedCLAUDE.md "outputs/", "decision_log.json"

**18:30–19:30** · Everyone · Member 4 runs the index and cost scripts

**In one line:** wipe test output, do the demo runs with separate labels, and commit exactly what they produced. v3 No run can overwrite another run's files.

1.  **Reset:** empty `outputs/`; set `decision_log.json` to `[]`; restart the app container so cooldowns start clean; check notebook section 2 shows Groq with budget left.
2.  v3 **Run W (label `w`), weak but searchable:** pick a brief before running whose topic is widely discussed (so coverage will be adequate) but whose founder constraints fit poorly, for example little time, no budget and skills that do not match the idea. Expected: `stop` on fit or on evidence. If it ends in `repeat` or `pivot_back`, that is the honest result: keep it and do not change thresholds. Do not use a brief chosen for "little public discussion"; that produces `repeat`.
3.  v3 **Run E (label `e`), backup STOP:** the excluded brief from `model_check.py` ("a crypto trading signal bot"). Ends in `stop` that cannot be overridden. Short, deterministic, and guarantees the committed outputs contain a stop.
4.  **Run R (label `r`):** "Notion templates for wedding planners, Egypt", with `awaiting_evidence` at Phase 2 resolved by founder override, through Phase 6.
5.  **Payment log:** `python scripts/payment_test_run.py`.
6.  v3 **Index:** `python scripts/index_runs.py` reads `decision_log.json` and writes `docs/demo_runs.md`: one table per run ID with label, brief, final outcome per phase, every artifact path, and tiers used. It is generated, never edited. (It lives in `docs/` so `outputs/` holds only phase-named files.)
7.  v3 **Full-run measurement (fix 7):** `python scripts/cost_per_run.py --run-id <R's id>` gives total tokens per tier for the complete path. Full runs per day on Groq ≈ 200,000 ÷ R's total tokens, labelled "measured from 1 complete run". Notebook section 5 stays labelled partial.
8.  **Validate:** `python -m json.tool decision_log.json`; every name matches `phase<N>_step<M>_*` or `phase<N>_gate_*`; every model entry has a tier and a run ID; no entry contains `gsk_` or `nvapi-`; `outputs/` has one set of files per label.
9.  **Commit** `outputs/`, `decision_log.json` and `docs/demo_runs.md` only from these runs.

Stage test · Step 9: demo runs

Runs: Member 4 (scripts), everyone (runs). The step is not done until every line below passes.

    python -m json.tool decision_log.json > $null
    docker compose run --rm app python scripts/check_outputs.py --all
    docker compose run --rm app python scripts/cost_per_run.py --run-id <R>
    git log -p | findstr "gsk_ nvapi-"

- Log parses; every entry has the five keys and `run_id`; model entries name their tier.
- `check_outputs.py --all`: one file set per label, names match the pattern, no file edited after the run (hashes match the artifact registry), at least one stop verdict, `payment_test_log.md` present and all MOCKED.
- PERF-1: three timed runs of brief R, each ≤ 180 s system time; if any fails, cut model calls, do not raise the limit.
- No key string anywhere in git history.

**Regression:** then run the whole suite, `docker compose run --rm app pytest -q`. Every test that passed at an earlier stage must still pass; a new failure blocks the merge to `main`.

Done whenStage test passes, and: The committed outputs hold separate W, E and R files, at least one `stop` verdict and `payment_test_log.md`; `docs/demo_runs.md` links each run to its files; the full-run token figure comes from R; nothing was edited by hand.

Check before you move on

- File names keep the CLAUDE.md pattern because the label goes inside the short name (`phase1_gate_decision-w.md`). Whether the organizers' checker also reads subfolders is unknown, so v3 keeps `outputs/` flat.

## 12. Step 10 · Documentation

*Source: CLAUDE.md "README.md", "ARCHITECTURE.md"*

**19:30–21:30** · Each owner writes their phase · v3 Member 1 assembles (was Member 2)

**In one line:** turn the four research files into ARCHITECTURE.md, fill the README honestly, and report cost from the log.

| ARCHITECTURE.md       | Source and content                                                                                                                                           |
|-----------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------|
| ## Overview          | One paragraph and one Mermaid flowchart of the six phases and gates.                                                                                         |
| ## Phases            | One `###` per phase; Core steps in full detail; source registry in Phase 1.                                                                                  |
| ## Gates             | X1, X5, X15; the check order; each phase's weak-idea table; v3 coverage vs evidence in Phase 1 and `awaiting_evidence` in Phase 2; when STOP is recommended. |
| ## Sale to cash      | Order lifecycle, idempotency, refund revokes future access, reconciliation, simulated payout, Mermaid diagram.                                               |
| ## Data flow         | H1 to H5, Phase 2 patch section D, "Model calls" (three tiers, switching rules, time budget, Mermaid hand-over diagram), approval binding.                   |
| ## Built vs. stubbed | Same rows as the README table.                                                                                                                               |
| ## Roadmap           | Phase 3 Table 24 plus each phase's deferred items.                                                                                                           |

1.  **Cost per run** (Member 4): `cost_per_run.py` per run ID and tier. README line: "About \$0.00 per run observed (run R: N calls, about T tokens: X on Groq free tier, Y on NVIDIA free tier, Z local). Electricity not included (ASSUMPTION)."
2.  **What works and what is mocked:** one row per step; Working, MOCKED or STUBBED.
3.  v3 **Models and free resources:** the default local tag, its licence and its measured numbers, stated plainly when slow ("works on CPU at about X tokens/s; a full run took about M minutes on our laptop; first start downloads G GB"); other tested candidates; the two optional free tiers with "free tier, no card, needs your own key in `.env`"; how to change `LLM_ORDER`; that remote tiers send prompt text to the provider.
4.  **What our system will NOT do:** the Never list in plain words, plus excluded products.
5.  **How the project stays alive:** maintainers, roadmap, contribution route; no funding claims you cannot support.
6.  **Prompts:** every agent's prompt in `prompts/<role>.md`, matching the code.
7.  **Retire the research files:** `git rm -r --cached Phases-Research` once their content is in ARCHITECTURE.md. Never move them into `docs/`.
8.  **Scan for forbidden text:** no lines addressing reviewers or asking for a score, including notebook markdown.

Stage test · Step 10: documentation

Runs: Member 1. The step is not done until every line below passes.

    docker compose run --rm app pytest -q tests/test_repo_layout.py
    docker compose run --rm app python scripts/check_docs.py

- README: eight headings in order, `docker compose up` bash block, \$ figure that says observed or expected.
- ARCHITECTURE.md: the seven headings in order, Mermaid or ASCII diagrams only, no image links.
- Every agent in `agents/` has a `prompts/<role>.md`.
- "Built vs. stubbed" rows say Working only where the named test passes (`check_docs.py` cross-checks the test names).
- No sentence addressing reviewers or asking for a result in any tracked file.

**Regression:** then run the whole suite, `docker compose run --rm app pytest -q`. Every test that passed at an earlier stage must still pass; a new failure blocks the merge to `main`.

Done whenStage test passes, and: README has all eight headings in order with a `docker compose up` block and a \$ figure; ARCHITECTURE.md has all seven sections with text diagrams only.

## 13. Step 11 · Fresh clone, push, video

*Source: CLAUDE.md "Before every push"; slide 9*

**21:30–22:30** · v3 Members 3 and 4 · Member 2 on call for fixes

**In one line:** judges check one-command build, licence and a valid log before reading anything, so prove all three on a clean copy.

1.  **Fresh clone** into a new folder without `.env`; `docker compose up --build`; watch the readiness line reach "ready"; run one brief on the local tier alone.
2.  **Tests:** `docker compose run --rm app pytest -q` → all pass without a key.
3.  **Tick the checklist** in section 14 line by line.
4.  **Push to `main`** (Member 3); confirm LICENSE, README, docker-compose.yml, decision_log.json, outputs/ and tests/ on GitHub.
5.  **Record the video** (Member 4, at most 3 min, no key or `.env` on screen): re-run notebook sections 2 to 4 first; brief W → verdict with coverage numbers; approval screen showing all five bound fields; Phase 2 `awaiting_evidence` and override banner; payment mock run. Keep the tier status and progress lines visible. Upload unlisted; link under `## Demo video`; push.

Stage test · Step 11: fresh clone

Runs: Members 3 and 4. The step is not done until every line below passes.

    git clone <repo> fresh; cd fresh          # no .env copied
    docker compose up -d --build
    docker compose run --rm app pytest -q
    docker compose run --rm app python scripts/check_outputs.py --all

- Build and start work with no `.env`; readiness reaches "ready"; one brief runs on local Gemma alone.
- The full suite passes on the fresh clone.
- Committed outputs and log still pass the output checker.
- Final checklist (section 14) ticked line by line.

Done whenStage test passes, and: The fresh clone builds and passes tests without a `.env`, and the final push is on `main` before 22:30. After that, the buffer runs to 23:59 and nobody merges.

## 14. Final checklist and recap

*Source: CLAUDE.md "Before every push"; Hard Requirements*

**In one line:** tick every row on the fresh clone before the final push; one unticked MUST can cost the whole score.

| Check                                                                      | How to verify                                                                           | Step     |
|----------------------------------------------------------------------------|-----------------------------------------------------------------------------------------|----------|
| On `main`, no secrets, no binaries                                         | `git ls-files`: no .env, .pptx, .pdf, .sqlite, `~$` file, notebook checkpoint, `state/` | 1        |
| LICENSE full OSI text at root                                              | Open it; unmodified MIT                                                                 | 1        |
| One-command build                                                          | Fresh clone, `docker compose up`; local default tag is the measured Gemma 4 Q4_K_M tag  | 1, 11    |
| README: 8 headings, bash block, \$ figure                                  | Read top to bottom                                                                      | 10       |
| decision_log.json valid, 5 keys + run ID per entry                         | `python -m json.tool`; backbone test                                                    | 2, 9     |
| outputs/ from real runs, one set per label, includes a stop                | `dir outputs`; `docs/demo_runs.md`; gate files                                          | 9        |
| payment_test_log.md present, MOCKED                                        | Open it                                                                                 | 6, 9     |
| tests/ pass                                                                | `pytest -q` in Docker, no key                                                           | 11       |
| ARCHITECTURE.md: 7 sections, Mermaid only                                  | Read headings                                                                           | 10       |
| Every mock labelled                                                        | Search for MOCKED, STUBBED, SIMULATED in UI, outputs, README                            | 10       |
| Approval bound to action, content, destination, amount, run ID; single use | Five binding tests; try to change one field after approving in the UI                   | 2, 8     |
| Trick prompts refused                                                      | Eval set passes; recall and false-positive rate quoted only from that run               | 2        |
| No paid API, no payment SDK                                                | `requirements.txt`; both remote tiers free with no card                                 | 0, 1, 6  |
| No API key anywhere in git                                                 | `git log -p | findstr gsk_` and `nvapi-` return nothing                                 | 0, 11    |
| Every stage test passes on the fresh clone                                 | Section 0.4 table, last column; full suite + `check_outputs.py --all`                   | 0–11     |
| Cascade works, is bounded and logged                                       | Cascade tests incl. budget cases; log entries name tiers                                | 2, 2b, 9 |
| Runs with no key, even if slow                                             | Fresh clone uses local only; README states its speed                                    | 10, 11   |
| Weak idea → stop; thin search → repeat; no experiment → awaiting evidence  | W and E gate files; Phase 1 and 2 tests                                                 | 3, 4, 9  |

Check before citing (unverified today)

- Local speed and JSON correctness for Gemma 4 26B A4B Q4_K_M on the 16 GB GPU, on the host and in Docker: not measured (Step 0). NVIDIA Build hosting of Qwen3.8-27B: not confirmed (Step 2b).
- Remote JSON reliability, low reasoning effort and JSON-schema mode on Groq and NVIDIA: not measured (Step 2b).
- Free-tier limits: provider and third-party pages read 17 Nov 2026; they change with traffic.
- Gemma 4 licence of the exact tag; the Ollama image version to pin; whether Ollama's `format` honours every `jsonschema` keyword used (keep schemas to type, enum, minimum, maximum, required).
- Streamlit's `/_stcore/health` path and Compose healthcheck syntax: test on the first build.
- Whether the organizers' checker reads subfolders of `outputs/`: unknown, hence flat names.
- Every time value, threshold and budget in this runbook is a planning value (ASSUMPTION) until Steps 0, 2b, 8 and 9 measure it. Deadline timezone and "all phases vs one deep part": confirm on Slack.

### v3.4 0.6 Running the app with one command on the team laptop

`.env` sets `COMPOSE_FILE=docker-compose.yml:docker-compose.gpu.yml`, `LOCAL_MODEL_DIR=/home/hachathon/models/gemma4` and `LOCAL_CTX=16384`, so plain `docker compose up` starts the GPU llama.cpp container with the existing GGUF and the UI. The container model is published on host port 8081 so it never clashes with a host `llama-server` on 8080; only one of them should run at a time on the 16 GB GPU (`scripts/stop_local_llm.sh`). `scripts/doctor.sh` checks Docker, the NVIDIA Container Toolkit, the model file, ports and disk before the first start. Plain-language steps: `docs/how_to_run.md`.
