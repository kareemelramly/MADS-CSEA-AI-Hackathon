MADS × CSEA AI Hackathon · Software Requirements Specification · v1.3 · 17 Nov 2026

# Software Requirements Specification for the Agentic Venture Builder

What the system must do, how fast, and under which rules, written to the IEEE-style template and traced to CLAUDE.md, the problem statement and Build Runbook v3.

|                  |                                                                                                                                        |
|------------------|----------------------------------------------------------------------------------------------------------------------------------------|
| **Project**      | Agentic Venture Builder (repository `MADS-CSEA-AI-Hackathon`)                                                                          |
| **Version**      | 1.3 draft, for team review (not yet approved). Authoritative for the model architecture and the cross-phase decisions X1–X19.          |
| **Prepared by**  | Team name TBD-1, MADS × CSEA AI Hackathon, Fall 2026                                                                                   |
| **Date created** | 17 November 2026                                                                                                                       |
| **Template**     | Software Requirements Specification template, © 1999 Karl E. Wiegers; the template grants permission to use, modify and distribute it. |

### Revision history

| Name       | Date        | Reason for changes                                                                                                                                                                                                                                                                                                                                                                                                       | Version   |
|------------|-------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|-----------|
| Team TBD-1 | 17 Nov 2026 | First draft from CLAUDE.md, the problem statement and Build Runbook v3; adds the 3-minute run requirement (PERF-1 to PERF-3).                                                                                                                                                                                                                                                                                            | 1.0 draft |
| Team TBD-1 | 17 Nov 2026 | Review fixes (Appendix E): payment rule, unrun experiment vs zero demand, one model architecture (Groq → NVIDIA → local Gemma, no GPT), A1-only Build scope with 14 checks, Phase 2 gate branch coverage, attempt IDs for write-once outputs, model errors vs quality failures, evidence-based status words, commercial approval wording, full Phase 6 specification. Agent-design guidance from four references (§2.5). | 1.1 draft |
| Team TBD-1 | 17 Nov 2026 | Local GPU corrected to 16 GB VRAM; aligned with Architecture Decision Report v2: UI and Ollama ports bound to 127.0.0.1 (COMM-1), SQLite action log canonical with atomic JSON export (LOG-1), Phase 6 memo filled by template (OPS-5), Groq token-per-minute limit made explicit for PERF-1. ARCHITECTURE.md written from this version.                                                                                 | 1.2 draft |
| Team TBD-1 | 17 Nov 2026 | Testing after every build stage: new §6.4 (TEST-1 to TEST-9) with a stage-by-stage verification table matching Build Runbook v3.3.                                                                                                                                                                                                                                                                                       | 1.3 draft |

### Table of contents

|                                      |                                                                                                                                                                                                                                         |
|--------------------------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| 1\. Introduction                     | 1.1 Purpose · 1.2 Document conventions · 1.3 Intended audience · 1.4 Product scope · 1.5 References                                                                                                                                     |
| 2\. Overall description              | 2.1 Perspective · 2.2 Functions · 2.3 User classes · 2.4 Operating environment · 2.5 Constraints · 2.6 User documentation · 2.7 Assumptions and dependencies                                                                            |
| 3\. External interface requirements  | 3.1 User · 3.2 Hardware · 3.3 Software · 3.4 Communications                                                                                                                                                                             |
| 4\. System features                  | 4.1 Run control · 4.2 Model access · 4.3 Discover · 4.4 Validate · 4.5 Build · 4.6 Commercial setup · 4.7 Launch and sale to cash · 4.8 Operate and learn · 4.9 Approval and override · 4.10 Guardrails · 4.11 Decision log and outputs |
| 5\. Other nonfunctional requirements | 5.1 Performance (includes the 3-minute run) · 5.2 Safety · 5.3 Security · 5.4 Quality attributes · 5.5 Business rules                                                                                                                   |
| 6\. Other requirements               | 6.1 Repository deliverables · 6.2 Legal and licensing · 6.3 Data storage · 6.4 Verification by stage                                                                                                                                    |
| Appendices                           | A Glossary · B Analysis models · C To-be-determined list · D Traceability summary · E Review findings and resolutions                                                                                                                   |

## 

*Source: 1. Introduction*Template §1

### 1.1 Purpose

This SRS specifies release 1.0 of the Agentic Venture Builder: an open-source team of AI agents that takes a founder's brief through six phases (Discover, Validate, Build, Commercial setup, Launch, Operate and learn) toward a validated, sellable digital product, and that recommends **stop** when evidence is weak. It covers the whole system that the team submits on the repository's `main` branch: the agents, gates, founder approval, model access, the mocked sale-to-cash ledger, the Streamlit UI, and the repository deliverables the organizers' checker reads.

### 1.2 Document conventions

- **"shall"** marks a mandatory requirement; **"should"** marks a recommended one.
- **IDs:** each requirement has its own tag (`DIS-6`, `PERF-1`), its own priority, a source and a verification method. Priorities are not inherited.
- **Priority:** **High** = a MUST in CLAUDE.md or the Hard Requirements, or breaking it risks disqualification; **Medium** = a SHOULD, or needed for a credible demo; **Low** = build only if time remains, else label STUBBED.
- **Source codes:** CM = CLAUDE.md conventions; HR = CLAUDE.md Hard Requirements; PS = Problem Statement Explained; RB§n = Build Runbook v3, section n; P1 = Discover phase card; P2 = Phase 2 patch; P3 = Phase 3 specification; P45 = Phases 4–5 research; RR = multi-agent research report; UR = user request of 17 Nov 2026; AG1–AG3 = agent-building guides (§1.5); RV = review of 17 Nov 2026 (Appendix E).
- **Verification:** T = automated test (file named), I = inspection, D = demonstration in a run, M = measurement.
- ASSUMPTION marks a planning value not yet measured; TBD-n points to Appendix C.

### 1.3 Intended audience and reading suggestions

| Reader                             | Read first                                                                                 |
|------------------------------------|--------------------------------------------------------------------------------------------|
| Phase owners (Members 1–4)         | Section 4 for your phase, then 4.9 to 4.11 (shared rules every phase must meet), then 5.1. |
| Backbone owner (Member 2)          | 4.1, 4.2, 4.9, 4.11, 5.1, 5.3.                                                             |
| Tester and demo lead               | 5.1 (timing), the Verify column in every table, Appendix D.                                |
| Documentation assembler (Member 1) | Section 6 and 2.6.                                                                         |

### 1.4 Product scope

Most AI business tools promise income, lock users in, and stop at a generic plan (PS). This product is the honest, open alternative: sourced evidence, proven methods (Lean Canvas, Mom Test, pre-set thresholds), the founder in control of every external action, and a system that says "don't launch this" when the numbers say so. All payments, publishing and delivery are MOCKED or STUBBED. The goals for release 1.0 are the hackathon's six scored criteria: working prototype, architecture quality, evidence and honesty, founder control and safety, reproducibility and openness, and a pitch.

### 1.5 References

| Code            | Document                                                                                                                     | Version, date, location                                                                                                                                                                            |
|-----------------|------------------------------------------------------------------------------------------------------------------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| CM, HR          | CLAUDE.md: hackathon submission conventions and Hard Requirements                                                            | Organizers, Fall 2026; repository root (moved from `Claude/` in Step 1)                                                                                                                            |
| PS              | Open-Source Agentic Venture Builders: Problem Statement Explained                                                            | Organizers, Fall 2026; `Problem_Statement_Explained.pdf` (untracked)                                                                                                                               |
| RB              | Build Runbook v3: Empty Repo to Submission                                                                                   | Team, v3, 17 Nov 2026; `Claude outputs/Build_Runbook_v3.pdf`                                                                                                                                       |
| P1, P2, P3, P45 | Discover_Phase_Card.md; ARCHITECTURE_phase2_patch.md; Phase3_Build_Agent_Specification.md; Member4_Phase4_Phase5_Research.md | Team, 17 Nov 2026; `Phases-Research/`                                                                                                                                                              |
| RR              | Building a Reliable, Cost-Efficient Multi-Agent Venture Builder (research report)                                            | Team research handoff, 17 Nov 2026                                                                                                                                                                 |
| Ext.            | Groq rate limits; Qwen3.8-27B licence; Gemma 4 26B A4B quantization sizes; Ollama API and structured outputs                 | console.groq.com/docs/rate-limits; huggingface.co/Qwen/Qwen3.8-27B; huggingface.co/bartowski/google_gemma-4-26B-A4B-it-GGUF; github.com/ollama/ollama/blob/main/docs/api.md (all read 17 Nov 2026) |
| DR              | Architecture Decision Report v2 (aligned)                                                                                    | Team, 17 Nov 2026; `Claude outputs/Agentic_Architecture_Decision_Report_2026-11-17_aligned.md`                                                                                                     |
| AG1             | OpenAI, A practical guide to building AI agents                                                                              | openai.com/business/guides-and-resources/a-practical-guide-to-building-ai-agents (read 17 Nov 2026)                                                                                                |
| AG2             | How to build AI agents that automate business workflows (step-by-step guide)                                                 | dev.to/babavose (read 17 Nov 2026)                                                                                                                                                                 |
| AG3             | B. Marr, The beginner's blueprint for building AI agents that handle your toughest business tasks                            | bernardmarr.com (read 17 Nov 2026)                                                                                                                                                                 |
| AG4             | How to build an enterprise AI agent that can actually execute business tasks                                                 | linkedin.com/pulse (could not be read: the site blocks automated access; not used as a source)                                                                                                     |

## 

*Source: 2. Overall description*Template §2

### 2.1 Product perspective

A new, self-contained product, run with one command (`docker compose up`). Three containers: `ollama` (local model server), `model-pull` (one-shot weight download) and `app` (Streamlit UI, orchestrator, agents, gates, approval, mock ledger). Optional external services are two free model tiers (Groq and NVIDIA Build; the local Gemma model is the backup) and four keyless evidence sources. No payment, e-mail, social or hosting service is connected; those actions are STUBBED behind approval.

    Founder (browser :8501)
       │ brief, approvals, overrides, real counts
       ▼
    app: orchestrator ──► agents (role functions) ──► llm.py ──► tier chosen per task (sticky)
       │      │                   │       Groq qwen3.8-27b → NVIDIA Build → local Gemma 4 26B A4B (backup)
       │      ├─► gates.py (code decides outcomes)
       │      ├─► approval.py ──► executor ──► STUBBED publish / MOCKED ledger (state/*.sqlite)
       │      └─► sources.py ──► HN Algolia · Stack Exchange · GitHub · Wikipedia
       └─► decision_log.json · outputs/*.md|json|csv

### 2.2 Product functions

- Take a structured founder brief and run six phases in order, pausing at every gate that needs the founder.
- Find and cite evidence; score the idea and two alternatives; recommend go, repeat, pivot back or stop.
- Build a Lean Canvas, lock a demand target before data, draft a guarded landing page, and judge real experiment results.
- Produce a tested template-based MVP with user docs; set a sourced price and DRAFT policies.
- Prove pay → deliver → refund → revoke → reconcile on a MOCKED ledger.
- Write a persevere-or-pivot memo from real numbers only.
- Require founder approval, bound to the exact action, for anything published, sent, spent or released.
- Log every agent action and report cost per run.

### 2.3 User classes and characteristics

| Class                             | Importance          | Characteristics and what they use                                                                                                                              |
|-----------------------------------|---------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Founder                           | Primary             | Non-technical to semi-technical; uses the UI only. The only class that can approve, override, enter real counts and make the Phase 6 decision.                 |
| Judge / evaluator                 | Primary for scoring | Clones `main` with no `.env`, runs `docker compose up` and the tests, reads README, ARCHITECTURE and outputs, tries trick prompts. May have a CPU-only laptop. |
| Developer (team)                  | Secondary           | Runs tests, the cascade-check notebook and demo runs; holds API keys in `.env`.                                                                                |
| Contributor (after the hackathon) | Tertiary            | Reads ARCHITECTURE.md and prompts; extends phases.                                                                                                             |

### 2.4 Operating environment

- Docker Desktop with Compose v2 on Windows 10/11 (WSL 2 backend), Linux or macOS; x86-64 CPU by default; NVIDIA GPU optional via `docker-compose.gpu.yml`.
- Disk: at least 25 GB free for images and weights (ASSUMPTION).
- **Local backup model:** Gemma 4 26B A4B at Q4_K_M on the team laptop's **16 GB GPU**. The weights are about 16–17 GB (published GGUF listings), so at an 8K context a small part (about 1–2 GB) spills to system RAM; third-party reports give roughly 40–70 tokens/s on 16 GB cards (not measured here). Plan for at least 16 GB of free system RAM, raise the WSL 2 memory limit in `.wslconfig`, and run with the GPU compose override and NVIDIA's WSL GPU support. If the spill makes calls slow, use a smaller quantization of the same model that fits fully (Q4_K_S about 14.9 GB, UD-IQ4_XS about 12.7 GB); the model choice does not change. Machines without a GPU still run the CPU-safe default, slowly (PERF-5).
- Container runtime: Python 3.12 (slim image), Streamlit, Jinja2, jsonschema, pytest; Ollama server image pinned to the version measured in Step 0 (TBD-3).
- A current desktop browser on the host (Chrome, Edge, Firefox) at http://localhost:8501.
- Internet needed for the first image and model download, for remote tiers and for evidence sources; the no-key path needs it only for evidence sources.

### 2.5 Design and implementation constraints

- **Hackathon rules (HR, CM):** OSI licence; one-command setup; free open-weight models only; no paid API; no payments of any kind, including sandbox and test mode; founder approval enforced in code; every claim sourced or labelled ASSUMPTION; every mock labelled; cost per run reported.
- **Checker conventions (CM):** exact file names, README and ARCHITECTURE headings, outputs naming; default branch only; text diagrams only.
- **Architecture (RB, RR):** fixed Python state machine; agents are role functions named `agents/<role>.py`; gate outcomes computed by code; one shared model client (`llm.py`); OpenAI chat-completions format for remote tiers; Ollama `/api/chat` locally.
- **Excluded products (CM, PS):** physical goods; financial, investment or crypto products; health or legal advice products.
- **Time:** code freeze at the final push before Tuesday 11:59 PM (deadline timezone TBD-8).

**Design guidance adopted from the agent-building references (AG1–AG3).** The guides were read as advice, not as rules; each item below is adopted because it fits the hackathon constraints.

| Guidance                                                                                                                     | Ref      | Where this SRS applies it                                                                                              |
|------------------------------------------------------------------------------------------------------------------------------|----------|------------------------------------------------------------------------------------------------------------------------|
| Agent = model + tools + instructions; write instructions as numbered routines with branches for missing data                 | AG1      | One prompt file per role (QUAL-6); every phase card lists its routine and missing-input branches (CORE-1).             |
| Rate every tool low, medium or high by write access, reversibility and financial impact; pause for checks on high-risk calls | AG1      | APR-10 risk table: every external-effect action is high and needs approval; payment actions are prohibited, not rated. |
| Escalate to a human after repeated failures and before high-risk actions                                                     | AG1, AG3 | CORE-11 (two model errors in one step pause for the founder); approvals (4.9).                                         |
| A run loop needs explicit exit conditions                                                                                    | AG1      | Gate outcomes end every phase (CORE-3); bounded attempts and the run budget (MOD-8, PERF-2).                           |
| Combine deterministic rules with model reasoning; validate model output against explicit rules                               | AG2      | Gates are code (CORE-4); jsonschema plus reference checks (MOD-7).                                                     |
| Layer guardrails; no single guardrail is sufficient                                                                          | AG1      | Rules, schema checks, approval binding and the executor boundary (4.9, 4.10).                                          |
| Start with a narrow pilot; split work into discrete stages; measure response time; build failure handling in from the start  | AG2, AG3 | A1-only Build scope (4.5); six gated phases; run timing (5.1); model and pipeline errors handled separately (CORE-9).  |
| Make mistakes traceable and owners clear                                                                                     | AG3      | Run and task IDs on every log entry and file (CORE-6, X16); owners per step in the runbook.                            |
| Not adopted: memory or vector stores; multi-agent manager or hand-off chat                                                   | AG1, AG2 | Each run is self-contained and the pipeline is fixed (CORE-2); long-term memory is a roadmap item.                     |

### 2.6 User documentation

| Item                | Content and format                                                               |
|---------------------|----------------------------------------------------------------------------------|
| `README.md`         | The eight required headings in order (6.1); Markdown.                            |
| `ARCHITECTURE.md`   | The seven required sections with Mermaid diagrams.                               |
| Product user docs   | Generated per run by `agents/doc_writer.py` (six fixed headings), in `outputs/`. |
| In-app text         | Plain-language verdict box, labels and error panel (3.1).                        |
| `docs/demo_runs.md` | Generated index of demo runs and their files.                                    |
| Demo video          | At most 3 minutes, linked under `## Demo video`.                                 |

### 2.7 Assumptions and dependencies

| #  | Assumption or dependency                                                                                                                                                                                      | If wrong                                                                                                           |
|-----|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|--------------------------------------------------------------------------------------------------------------------|
| A1  | Groq's free tier serves `qwen/qwen3.8-27b` (Apache-2.0) at 30 req/min, 1,000 req/day, 8K tokens/min, 200K tokens/day with no card (Groq's page notes free and Developer values may differ; read 17 Nov 2026). | Calls move to NVIDIA or local sooner; PERF-1 may fail on the local tier.                                           |
| A2  | NVIDIA Build hosts Qwen3.8-27B (NGC lists a NIM container; a hosted API endpoint is not confirmed) or another non-GPT open-weight model, at about 40 req/min for dev and test use, no card (TBD-12).          | Tier 2 uses a different model or drops out; Groq → local only.                                                     |
| A3  | Local Gemma 4 26B A4B (Q4_K_M) reaches 9/10 schema-valid outputs on `model_check.py`.                                                                                                                         | No working no-key path; release blocked until fixed (MOD-10).                                                      |
| A7  | The demo laptop has a 16 GB NVIDIA GPU usable from Docker (WSL 2) and enough system RAM for a 1–2 GB spill.                                                                                                   | Local backup slower; switch to a smaller quantization of the same model, or rely on the remote tiers for the demo. |
| A4  | HN Algolia, Stack Exchange and GitHub search answer without keys at demo time.                                                                                                                                | Discover returns `repeat` (inconclusive), never `stop`.                                                            |
| A5  | A full run needs at most 16 model calls and about 20K–45K tokens (RR estimate).                                                                                                                               | PERF-1 and the runs-per-day figure change; re-measure (PERF-9).                                                    |
| A6  | The organizers' checker reads `outputs/` at the top level.                                                                                                                                                    | None, since files stay flat (LOG-5).                                                                               |

## 

*Source: 3. External interface requirements*Template §3

### 3.1 User interfaces

One Streamlit page at port 8501. Every screen shows the run ID, the current phase, the model status line and the local-model readiness line. Errors follow one format: what failed, the resulting outcome, "nothing was decided" when true, and the next action.

| ID    | Requirement                                                                                                                                                       | Pri    | Source       | Verify |
|-------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------|--------|--------------|--------|
| UI-1  | The UI shall provide a brief form with idea, skills, budget amount and currency, hours per week, target market and countries, values, and run label.              | High   | PS; RB§10    | D      |
| UI-2  | The UI shall show phase progress and a live status box listing each model attempt (tier, status, elapsed time, budget left).                                      | High   | RB§2a, §10   | D      |
| UI-3  | The UI shall show the plain-language verdict before any action button for that gate.                                                                              | High   | RB§10        | D      |
| UI-4  | The approval panel shall show action, content, destination, amount and run ID, with Approve and Reject buttons, and no pre-selected choice.                       | High   | HR; RB§4     | D, T   |
| UI-5  | The override panel shall require a typed reason; after any override an amber bar stays visible for the rest of the run.                                           | High   | P2; RB§6     | D      |
| UI-6  | Every mocked, stubbed or simulated element shall carry its label (MOCKED, STUBBED, SIMULATED) on screen.                                                          | High   | CM; HR       | I      |
| UI-7  | The UI shall show elapsed system time for the run against `RUN_TIME_BUDGET_S` (PERF-2).                                                                           | High   | UR           | D      |
| UI-8  | On a model or budget error, the UI shall show each tier and its failure reason, the outcome `repeat`, and a Try again button, and keep earlier run files visible. | Medium | RB§10        | D      |
| UI-9  | The UI shall provide a founder-evidence input (URL plus one-line claim), the Phase 2 real-results form (VAL-6) and the Phase 6 decision buttons.                  | High   | P1; P2; RB§9 | D      |
| UI-10 | With no remote key, the Run button shall stay disabled until the local model is ready, with the reason shown.                                                     | Medium | RB§3         | D      |

### 3.2 Hardware interfaces

No direct hardware interface. GPU use is optional and only through Docker's NVIDIA device reservation in `docker-compose.gpu.yml`; the default configuration shall run on CPU only (QUAL-4). No card readers, payment terminals or other devices are supported.

### 3.3 Software interfaces

| Component          | Interface and data                                                                                                      | Purpose and rules                                                                                     |
|--------------------|-------------------------------------------------------------------------------------------------------------------------|-------------------------------------------------------------------------------------------------------|
| Local Ollama       | `POST /api/chat` (`format` = JSON schema, `stream:false`, `think:false` where supported); `GET /api/tags`               | Tier 3 model calls; readiness check. Tokens from `eval_count`, `prompt_eval_count`.                   |
| Groq, NVIDIA Build | `POST {BASE_URL}/chat/completions`, Bearer key, JSON mode, schema in system prompt, `max_tokens` cap, thinking disabled | Tiers 1–2, model `qwen/qwen3.8-27b`. Rate-limit headers and `retry-after` read for switching (MOD-4). |
| Evidence sources   | HN Algolia search API; Stack Exchange search; GitHub issues search (unauthenticated); Wikipedia API (background only)   | Read-only HTTPS GET; results registered with source IDs (DIS-4).                                      |
| SQLite (stdlib)    | `state/approvals.sqlite`, `state/ledger.sqlite`                                                                         | Approval queue and MOCKED ledger; never committed.                                                    |
| Libraries          | Streamlit ≥1.40, Jinja2 ≥3.1 (autoescape on), jsonschema ≥4.23 (Draft 2020-12), pytest ≥8                               | UI, templates, validation, tests. Exact pins after first green build.                                 |
| Internal contracts | H1–H5 hand-off JSON between phases; `RunContext`; `GateResult`; `RealCounts`; `LockedPlan`                              | Field names as in P1–P45 and RB§4.                                                                    |

### 3.4 Communications interfaces

- **COMM-1 (High):** remote model and evidence calls shall use HTTPS; containers talk over the Compose network (`http://ollama:11434`); host ports 8501 and 11434 only, both bound to `127.0.0.1`; the UI is a single-founder local control, not authenticated multi-user authorization.
- **COMM-2 (High):** the product shall not send e-mail, messages or social posts, or call any payment, hosting or store API. Publish and post actions end in a STUBBED function that only logs `would_publish`.
- **COMM-3 (Medium):** evidence requests shall send a descriptive User-Agent and respect each source's rate limit; HTTP 403/429 marks the source as failed for coverage (DIS-6).
- **COMM-4 (High):** every outbound request shall have a timeout bounded by the remaining run budget (MOD-8, PERF-2).

## 

*Source: 4. System features*Template §4 · organized by feature

### 4.1 Run control and orchestration

**4.1.1 Description and priority.** High. Runs the six phases in order as a state machine, pauses at founder gates, and keeps runs separate.

**4.1.2 Stimulus/response.** Founder submits brief and presses Run → system validates the brief, creates a run ID, runs the next phase until a gate needs the founder, a stop, or the budget ends → founder acts (approve, override, enter counts) → system continues.

**4.1.3 Functional requirements**

| ID      | Requirement                                                                                                                                                                                                                                                                                                                                                                                         | Pri    | Source        | Verify                                |
|---------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|--------|---------------|---------------------------------------|
| CORE-1  | The system shall reject a brief with missing essential fields with outcome `repeat` and the list of missing fields, and shall not invent founder details.                                                                                                                                                                                                                                           | High   | PS; P1        | T test_phase1_discover                |
| CORE-2  | The system shall run Discover, Validate, Build, Commercial setup, Launch, Operate in that order, through a fixed state machine with no free-form agent conversation in the decision path.                                                                                                                                                                                                           | High   | PS; RR Q1     | I, D                                  |
| CORE-3  | Every phase shall end in a gate whose outcome is one of `go`, `repeat`, `pivot_back`, `stop`, or the pause state `awaiting_evidence`.                                                                                                                                                                                                                                                               | High   | PS; RB§4, §6  | T                                     |
| CORE-4  | Gate outcomes shall be computed by code from logged thresholds; a model may propose but never decide an outcome.                                                                                                                                                                                                                                                                                    | High   | RB§4; RR Q7   | I, T                                  |
| CORE-5  | Each gate shall check, in order: hard rules (exclusion, guardrail, tamper), data completeness, locked thresholds, founder action.                                                                                                                                                                                                                                                                   | High   | RB§4          | T                                     |
| CORE-6  | Each run shall get a unique run ID (UTC timestamp + label) carried by every log entry, output file and approval.                                                                                                                                                                                                                                                                                    | High   | RB§4          | T test_backbone                       |
| CORE-7  | Output files shall be write-once and named with run label and attempt number (`phase<N>_step<M>_<name>-<label>-a<k>.<ext>`); a retry writes the next attempt number and never overwrites. `RunContext.artifacts[]` shall record path, SHA-256, phase, step, attempt and status (`final` or `superseded`), and hand-offs and approvals shall reference the final artifact by path and SHA-256 (X16). | High   | RB§4, §11; RV | T test_backbone                       |
| CORE-8  | Phase 3 shall start only after Phase 2 `go` or a founder override; otherwise the system logs `skip_phase` with the reason.                                                                                                                                                                                                                                                                          | High   | P3; RB§7      | T test_phase2_validate                |
| CORE-9  | Model errors (invalid output after retries, timeouts, all tiers down, run budget used) and pipeline errors shall give `repeat` (`model_error` or `pipeline_error`) with "nothing decided", never `pivot_back` or `stop`, and shall never consume a quality attempt (Phase 1 research retry, `VALIDATE_MAX_ATTEMPTS`, `MAX_BUILD_ATTEMPTS`), which count only gate failures on valid output (X17).   | High   | X15; X17; RV  | T test_llm_cascade, test_phase3_build |
| CORE-10 | A `stop` on hard rules shall end the run; the founder may start a new run with a changed brief.                                                                                                                                                                                                                                                                                                     | High   | P1            | T                                     |
| CORE-11 | Two consecutive model errors in the same step shall pause the run and ask the founder to try again or stop, instead of retrying silently.                                                                                                                                                                                                                                                           | Medium | AG1, AG3      | T                                     |

### 4.2 Model access cascade

**4.2.1 Description and priority.** High. One client gives every agent a free open-weight model through one authoritative chain: Groq first, NVIDIA Build when Groq's tokens run out, local Gemma 4 26B A4B as the backup when a remote tier lags or fails. No GPT model is used on any tier. This section supersedes every other model statement in the research cards and Runbook v3 (cards now carry it as X2).

**4.2.2 Stimulus/response.** An agent starts a task and calls `ask()` → the client picks the first tier with a key, quota and no cooldown and pins the task to it → every later call of that task uses the same tier → if the pinned tier fails or lags, the task restarts on the next tier → validated JSON or a model error.

**4.2.3 Functional requirements**

| ID     | Requirement                                                                                                                                                                                                                                                                                                                              | Pri    | Source     | Verify                    |
|--------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|--------|------------|---------------------------|
| MOD-1  | The call order shall be set by `LLM_ORDER` (default `groq,nvidia,ollama`); a tier without a key shall be skipped silently, so a clone with no `.env` uses tier 3 only.                                                                                                                                                                   | High   | RB§2a; UR  | T test_llm_cascade        |
| MOD-2  | Tier 1 shall be Groq serving `qwen/qwen3.8-27b` (Apache-2.0) on its free tier without a payment method. Tier 2 shall be NVIDIA Build serving the same model if hosted, otherwise the non-GPT open-weight model chosen and measured in Step 2b (TBD-12). Tier 3 shall be local Gemma 4 26B A4B at Q4_K_M through Ollama (`OLLAMA_MODEL`). | High   | HR; UR; RV | I                         |
| MOD-3  | No tier shall use a GPT-family model.                                                                                                                                                                                                                                                                                                    | High   | UR         | I `.env.example`, compose |
| MOD-4  | Switching shall follow: Groq out of tokens or requests (pre-emptive header check or HTTP 429) → NVIDIA at once; any remote tier that **lags** (no complete answer within `LLM_REMOTE_TIMEOUT_S`, 20 s) or returns 5xx or 401/403 → local tier; cooldowns per RB§2a; a tier returns to line when its cooldown ends.                       | High   | UR; RB§2a  | T (fake clock)            |
| MOD-5  | **Sticky tier per task:** all model calls of one agent task (`task_id`) shall use the tier that answered the task's first call. If that tier fails mid-task, the task shall restart from its first call on the next tier, so no task output mixes models. Every log entry records `task_id` and `tier/provider/model`.                   | High   | UR         | T                         |
| MOD-6  | Every call shall pass one JSON schema (Ollama `format` locally; JSON mode with the schema in the system prompt remotely) and request thinking off where the model supports it.                                                                                                                                                           | High   | X3         | I, M Step 2b              |
| MOD-7  | Every output shall be validated with jsonschema (types, enums, ranges, required fields) and reference checks (every `source_id` exists in the run registry); invalid output gets one retry on the same tier, then the task moves tier; a final failure is a model error (CORE-9).                                                        | High   | X3; RB§4   | T test_validate           |
| MOD-8  | A call shall make at most `LLM_MAX_ATTEMPTS_PER_CALL` (4) attempts across tiers, each with timeout = min(tier timeout, time left in `RUN_TIME_BUDGET_S`); no attempt starts with less than `LLM_MIN_ATTEMPT_S` left.                                                                                                                     | High   | RB§2a      | T test_llm_cascade        |
| MOD-9  | The client shall emit one progress event per attempt (call, task, agent, tier, status, reason, elapsed, budget left) and expose `status()` without any key.                                                                                                                                                                              | Medium | RB§2a      | T                         |
| MOD-10 | The local backup shall pass correctness (≥ 9 of 10 schema-valid on `model_check.py`); its speed shall be measured and published separately; a slow but correct local tier shall stay in the chain.                                                                                                                                       | High   | RB§2, §4b  | M model_check             |
| MOD-11 | Remote calls shall cap output at `LLM_MAX_TOKENS` and use temperature 0.2; persona and batch calls run one at a time to protect Groq's 8K tokens per minute.                                                                                                                                                                             | Medium | RB§2a      | I                         |

### 4.3 Phase 1 Discover (Core step: find opportunities)

**4.3.1 Description and priority.** High. Finds sourced pain points, scores the idea and two alternatives against the founder's constraints, and recommends stop only on weak evidence that the system really examined.

**4.3.2 Stimulus/response.** Valid brief → exclusion check → criteria logged → search → registry → analysis → gate verdict and outputs.

**4.3.3 Functional requirements**

| ID     | Requirement                                                                                                                                                                                                                                     | Pri    | Source      | Verify         |
|--------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|--------|-------------|----------------|
| DIS-1  | The system shall check excluded categories before any search and give `stop` that cannot be overridden.                                                                                                                                         | High   | CM; P1      | T              |
| DIS-2  | The system shall log `define_research_criteria` with every threshold before the first search.                                                                                                                                                   | High   | P1          | T              |
| DIS-3  | Evidence sources shall be HN Algolia, Stack Exchange and GitHub issues search; Wikipedia only for background; unauthenticated Reddit and untested sources shall not be used.                                                                    | High   | RB§5; RR Q6 | I source_check |
| DIS-4  | Every fetched item shall get a registry entry (source ID, URL, source, HTTP status, fetched_at, excerpt); the model shall receive and return source IDs only; code shall render URLs; claims without a valid ID shall be printed as ASSUMPTION. | High   | HR; RB§5    | T              |
| DIS-5  | Founder-supplied URLs shall be fetched and registered like other sources; a URL that does not load shall not be registered.                                                                                                                     | Medium | P1; RB§5    | T              |
| DIS-6  | If fewer than `DISCOVER_MIN_SOURCES_OK` (2) sources answered or fewer than `DISCOVER_MIN_ITEMS_SCREENED` (20, ASSUMPTION) items were screened after one broadened retry, the outcome shall be `repeat` (inconclusive), never `stop`.            | High   | RB§5        | T              |
| DIS-7  | With adequate coverage and fewer than 3 relevant items with URLs across 2 sources after the retry, the outcome shall be `pivot_back` if a ranked alternative passes, else `stop`, with the count stated ("N relevant of M screened").           | High   | P1; RB§5    | T              |
| DIS-8  | The system shall score fit 1–5 on skills, budget, time and values (weights 35/25/25/15) with reasons; below 3 gives `pivot_back` or `stop` as in DIS-7.                                                                                         | High   | P1          | T              |
| DIS-9  | The system shall propose and rank two alternatives for Phase 2's pivot path.                                                                                                                                                                    | High   | PS; P1      | D              |
| DIS-10 | The interview script shall ask about past behaviour only (Mom Test) and contain no invented answers.                                                                                                                                            | Medium | PS; P1      | I              |
| DIS-11 | A `go` verdict shall recommend a validation experiment and shall not declare demand validated.                                                                                                                                                  | High   | P1          | I              |

### 4.4 Phase 2 Validate (Core step: design the business)

**4.4.1 Description and priority.** High. Lean Canvas, a demand target locked before data, a guarded landing page behind approval, and a gate on real experiment results.

**4.4.2 Stimulus/response.** Phase 1 `go` → canvas and plan → target locked → page drafted → publish approval (STUBBED) → kit exported → founder enters results → gate.

**4.4.3 Functional requirements**

| ID     | Requirement                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       | Pri  | Source       | Verify                                                                                      |
|--------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|------|--------------|---------------------------------------------------------------------------------------------|
| VAL-1  | The system shall produce a 9-box Lean Canvas, each box with source IDs or ASSUMPTION.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             | High | PS; P2       | I                                                                                           |
| VAL-2  | The plan "N sign-ups in D days" with `min_visitors` shall be locked (canonical JSON SHA-256 + `locked_at`) and logged before any page or data exists.                                                                                                                                                                                                                                                                                                                                                                                                                                                             | High | P2           | T                                                                                           |
| VAL-3  | The landing page shall pass guardrails, use an email-only waitlist labelled "Waitlist: MOCKED", and contain no counts, testimonials, ratings or countdowns.                                                                                                                                                                                                                                                                                                                                                                                                                                                       | High | HR; P2       | T                                                                                           |
| VAL-4  | Publishing shall go through approval (4.9) and end in a STUBBED function that only logs `would_publish`.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          | High | HR; P2       | T                                                                                           |
| VAL-5  | The real-results form shall hold `experiment_status` (default `not_started`), start and end dates, visitors (default unknown) and real sign-ups (default 0); simulated counts shall be stored separately and never reach the gate.                                                                                                                                                                                                                                                                                                                                                                                | High | RB§6; P2     | T                                                                                           |
| VAL-6  | The gate shall apply these rules in order, first match wins: (1) locked target changed → `stop`; (2) status not started or running → `awaiting_evidence`; (3) abandoned → `repeat`, no attempt used; (4) completed with recorded visitors below `min_visitors` → `repeat`, no attempt used; (5) completed, r = sign-ups ÷ N ≥ 1 → `go`; (6) 0.5 ≤ r \< 1 and attempt \< `VALIDATE_MAX_ATTEMPTS` → `repeat`; (7) r \< 0.5, or 0.5 ≤ r \< 1 with attempts used up, and an unused alternative → `pivot_back`; (8) the same with no alternative left → `stop`. Every completed case maps to exactly one of rules 5–8. | High | PS; RB§6; RV | T test_gate_covers_all_branches                                                             |
| VAL-7  | A completed experiment with 0 or 12 of 100 sign-ups shall give `pivot_back` or `stop`, never `go`; 60 of 100 after the final attempt with no alternative left shall give `stop`; the default form (not started) shall give `awaiting_evidence`, never `stop`.                                                                                                                                                                                                                                                                                                                                                     | High | PS; RV       | T test_completed_zero_fails, test_final_attempt_near_miss, test_not_started_awaits_evidence |
| VAL-10 | Contract H2 shall carry `experiment_status`, dates, visitors, sign-ups, `attempt`, `min_visitors`, `validation_status` (VALIDATED, AWAITING_EVIDENCE or UNVALIDATED_FOUNDER_OVERRIDE) and final artifact references.                                                                                                                                                                                                                                                                                                                                                                                              | High | P2 §G; RV    | I                                                                                           |
| VAL-8  | A founder override after `awaiting_evidence` or a failed gate shall set `UNVALIDATED_FOUNDER_OVERRIDE` and stamp every later output.                                                                                                                                                                                                                                                                                                                                                                                                                                                                              | High | P2           | T                                                                                           |
| VAL-9  | The persona stress test, if built, shall run calls one at a time and label all output SIMULATED.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  | Low  | P2           | I                                                                                           |

### 4.5 Phase 3 Build (Core step: build the product)

**4.5.1 Description and priority.** High. **Scope decision (v1.1):** the hackathon release builds archetype A1 (checklist pack) only; A2 and A3 move to the roadmap and A4 stays a stretch item. All checks that show the core workflow works are kept: 14 of the Phase 3 specification's 15 checks run on A1, and QA-07 (script integrity) is not applicable because A1 has no HTML or scripts. In this project a **tested MVP** is an A1 product that passes the 14 applicable checks and every automated acceptance criterion, with real-user completion kept as an unchecked MANUAL item.

**4.5.2 Stimulus/response.** Entry rule passes → plan → render → docs → QA → test gate (up to 3 attempts) → manifest → release approval.

**4.5.3 Functional requirements**

| ID    | Requirement                                                                                                                                                                                                                                                                                                                                                                    | Pri  | Source  | Verify              |
|-------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|------|---------|---------------------|
| BLD-0 | Gate G2 shall accept archetype A1 only unless another archetype is enabled together with its checks.                                                                                                                                                                                                                                                                           | High | RV      | T                   |
| BLD-1 | The MVP plan shall have one user story, at most 3 Must features each with an evidence ID, and 3–6 Given/When/Then criteria; thresholds logged first.                                                                                                                                                                                                                           | High | P3      | T                   |
| BLD-2 | The model shall fill text slots of a team-written template only; rendering shall use Jinja2 with autoescape.                                                                                                                                                                                                                                                                   | High | P3      | I                   |
| BLD-3 | User docs shall have six fixed headings; "What is mocked" shall be copied from the plan by code.                                                                                                                                                                                                                                                                               | High | PS; P3  | T                   |
| BLD-4 | QA (no model) shall run QA-01 to QA-06 and QA-08 to QA-15 on A1: manifest, size, format, journey trace, internal links, no external resources, banned content, excluded category, claims sourced, mocks and override labelled, docs headings, licence, acceptance criteria, naming. QA-07 shall be marked not applicable for A1 and become mandatory when A2 or A4 is enabled. | High | P3; RV  | T test_phase3_build |
| BLD-5 | The test gate shall allow at most `MAX_BUILD_ATTEMPTS` (3), counting only QA failures on valid output, with failing messages fed back; model and renderer errors use no attempt (CORE-9); the founder cannot pass a failed check.                                                                                                                                              | High | P3; X17 | T                   |
| BLD-6 | An injected income promise shall give `repeat` then `stop`.                                                                                                                                                                                                                                                                                                                    | High | HR      | T                   |
| BLD-7 | Release shall need approval of a SHA-256 manifest; a manifest change after approval shall be refused.                                                                                                                                                                                                                                                                          | High | HR; P3  | T                   |
| BLD-8 | The builder shall never call `eval`, `exec` or `subprocess`.                                                                                                                                                                                                                                                                                                                   | High | P3      | T                   |

### 4.6 Phase 4 Commercial setup (Core step: set the price and policies)

**4.6.1 Description and priority.** High. A sourced or labelled price and four DRAFT policies behind approval. No payments of any kind.

**4.6.2 Stimulus/response.** Founder enters competitor quotes → price computed → policies drafted → commercial approval → H4 hand-off.

**4.6.3 Functional requirements**

| ID    | Requirement                                                                                                                                                                                                                                                 | Pri  | Source  | Verify |
|-------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|------|---------|--------|
| COM-1 | The system shall log `define_pricing_criteria`, then set the price as the median of at least 3 paid one-time prices in one currency from fetched URLs; with fewer than 3, outcome `repeat`, and an experimental price only by override labelled ASSUMPTION. | High | P45     | T      |
| COM-2 | Terms, Privacy, Refund and Delivery policies shall each begin "DRAFT · FOUNDER REVIEW REQUIRED · Not legal advice" and make no compliance claims.                                                                                                           | High | PS; P45 | T      |
| COM-3 | Price and drafts shall need one commercial approval bound per 4.9 before the H4 hand-off is written. The approval authorizes only that internal hand-off: the policies stay DRAFT, nothing is signed, sent or published, and the screen says so.            | High | HR; RV  | T      |

### 4.7 Phase 5 Launch and mocked sale to cash (Core steps: open the store; deliver automatically)

**4.7.1 Description and priority.** High. Store page and launch post as STUBBED drafts behind approval; a MOCKED ledger proves payment triggers delivery, refunds revoke access, duplicates are ignored and the books reconcile.

**4.7.2 Stimulus/response.** Founder presses "Simulate purchase (MOCKED)" or runs `payment_test_run.py` → MOCKED events → delivery token → refund → reconciliation report.

**4.7.3 Functional requirements**

| ID    | Requirement                                                                                                                                                                                        | Pri  | Source     | Verify             |
|-------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|------|------------|--------------------|
| LCH-1 | The store page and launch post shall each need their own approval and be marked "STUBBED · NOT PUBLISHED".                                                                                         | High | HR; P45    | T                  |
| LCH-2 | The ledger shall use SQLite, integer minor units, unique `event_id` and `order_id`, one transaction per event, and no network, SDK or card fields.                                                 | High | HR; P45    | T test_phase5_mock |
| LCH-3 | A MOCKED payment event shall create one time-limited download token (`MOCK_TOKEN_EXPIRY_HOURS`) bound to the order.                                                                                | High | PS; CM     | T                  |
| LCH-4 | A duplicate payment event shall return the original result and create no second entitlement.                                                                                                       | High | CM         | T                  |
| LCH-5 | A MOCKED refund shall revoke future access to the token, and a second refund of the same order shall be refused; docs shall state that copies already downloaded cannot be revoked.                | High | CM; RR Q10 | T                  |
| LCH-6 | Reconciliation shall match orders, payments, fees (`MOCK_FEE_RATE`), refunds and a simulated payout batch to the cent and flag any mismatch.                                                       | High | CM         | T                  |
| LCH-7 | `scripts/payment_test_run.py` shall write `outputs/payment_test_log.md` covering pay, duplicate pay, refund, duplicate refund, revoked download and a 1-cent mismatch, every line labelled MOCKED. | High | CM         | D, I               |
| LCH-8 | The launch gate shall write H5; `go` means "mock run only".                                                                                                                                        | High | P45        | I                  |

### 4.8 Phase 6 Operate and learn

**4.8.1 Description and priority.** Medium (no Core step), fully specified in `Phases-Research/Phase6_Operate_Learn_Card.md`. Agents: `agents/analyst.py` (metrics table by code, memo wording by model), `agents/support_agent.py` (FAQ and reply drafts), `gates.operate_gate()` (code). Inputs: H5, Phase 2 locked plan and real counts, a founder-entered real post-launch metrics form (default empty), and Phase 6 targets set before data.

**4.8.2 Stimulus/response.** H5 → founder sets targets (logged) → founder enters any real metrics with evidence links → metrics table and recommendation by code → memo → founder decision. Separately: founder pastes a user question → support draft → optional send approval (STUBBED).

**4.8.3 Functional requirements**

| ID    | Requirement                                                                                                                                                                                                                                                                                                                | Pri    | Source   | Verify                                                          |
|-------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|--------|----------|-----------------------------------------------------------------|
| OPS-1 | Every metric shall be labelled real, MOCKED or SIMULATED; only real values (founder-entered with evidence link, or a completed Phase 2 experiment) reach the recommendation.                                                                                                                                               | High   | HR       | T                                                               |
| OPS-2 | `set_phase6_targets` shall be logged before real metrics are accepted; targets cannot change afterwards.                                                                                                                                                                                                                   | High   | X4; RV   | T test_targets_logged_first                                     |
| OPS-3 | `operate_gate` shall return `repeat` when only mocked or simulated data exist, or when Phase 2 never completed an experiment and no real post-launch data exist; `go` (persevere) only when every target is met by real values; otherwise `pivot_back` while an alternative or fixable product issue remains, else `stop`. | High   | RB§9; RV | T test_real_metrics_rules                                       |
| OPS-4 | Mock-only and awaiting-evidence runs shall never be recommended "persevere".                                                                                                                                                                                                                                               | High   | RB§9     | T test_mock_only_never_persevere, test_awaiting_never_persevere |
| OPS-5 | The memo shall be filled by code from a Jinja2 template (outcome, numbers, labels, reasons; no model call); after any override it opens with the override section.                                                                                                                                                         | High   | P2 §C    | T test_every_number_labelled                                    |
| OPS-6 | Support drafts shall cite the product docs or DRAFT policies or be labelled ASSUMPTION, be labelled "DRAFT · AI-written for founder review", never speak as the founder or a named person, and escalate legal, health, financial and refund questions to the founder without advice or promises.                           | High   | HR; RV   | T test_support_refuses_advice_and_promises                      |
| OPS-7 | Sending a support reply shall be STUBBED behind an approval bound per 4.9 (action `send_support_reply`, recipient placeholder, amount 0); approval logs `would_send` only.                                                                                                                                                 | High   | HR       | T test_support_reply_needs_approval                             |
| OPS-8 | The founder decision (persevere, pivot, stop) shall be logged with `approved_by: "founder"`; if it differs from the recommendation, the memo keeps both.                                                                                                                                                                   | Medium | CM       | T test_founder_decision_logged                                  |

### 4.9 Founder approval and override

**4.9.1 Description and priority.** High. Nothing is published, sent, spent or released without the founder approving that exact action; overrides are explicit, reasoned and limited.

**4.9.2 Stimulus/response.** Agent requests an action → queue entry shown → founder approves or rejects → executor re-checks the binding and runs the action once.

**4.9.3 Functional requirements**

| ID     | Requirement                                                                                                                                                                                                                                                                                                                                                                    | Pri  | Source      | Verify          |
|--------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|------|-------------|-----------------|
| APR-1  | Every publish, send, spend, sign or release action shall pass through `approval.request` and `approval.execute`; no other code path may cause an external effect.                                                                                                                                                                                                              | High | HR; CM      | T, I            |
| APR-2  | An approval shall bind action, content (SHA-256), destination, amount (minor units and currency) and run ID; a change to any of them shall void it and create a new request.                                                                                                                                                                                                   | High | HR; RB§4    | T (5 cases)     |
| APR-3  | Approval shall be granted only by the founder's UI action; there shall be no default approval and no approval on timeout.                                                                                                                                                                                                                                                      | High | HR          | T               |
| APR-4  | An approval shall be single-use: marked consumed in the same transaction that authorizes the action.                                                                                                                                                                                                                                                                           | High | RB§4; RR Q8 | T               |
| APR-5  | A mismatch shall be refused and logged as `approval_mismatch` naming the changed field.                                                                                                                                                                                                                                                                                        | High | RB§4        | T               |
| APR-6  | Prohibited actions (charge, refund money, transfer, create account, store credentials) shall be refused at request time, so they can never be approved.                                                                                                                                                                                                                        | High | HR          | T               |
| APR-7  | The approval queue shall persist in `state/approvals.sqlite`, not in UI session state.                                                                                                                                                                                                                                                                                         | High | RR Q8       | I               |
| APR-8  | An override (available after `awaiting_evidence`, `repeat`, `pivot_back` or an evidence `stop`) shall need a typed reason of at least 20 characters and shall be refused for exclusions, guardrail refusals, the Phase 3 test gate, approvals and the payment ban.                                                                                                             | High | P2 (X5)     | T test_backbone |
| APR-10 | Every action shall carry a risk rating, following AG1: **low** = read-only (search, read files), no approval; **medium** = internal write (outputs, hand-offs), logged; **high** = any external effect (publish, send, release, list a price), approval required (APR-1 to APR-5). Payment, account creation and credential storage are prohibited outright and are not rated. | High | AG1; HR     | I, T            |
| APR-11 | An approval shall authorize only the named internal action: never a signature, publication, payment or legal acceptance.                                                                                                                                                                                                                                                       | High | X10; RV     | I               |
| APR-9  | After an override, every later output shall start with "UNVALIDATED · FOUNDER OVERRIDE" and every log entry shall carry `"override": true`.                                                                                                                                                                                                                                    | High | P2          | T               |

### 4.10 Guardrails

**4.10.1 Description and priority.** High. Deterministic rules block banned content and excluded products in every phase, including the judges' trick prompts.

**4.10.2 Stimulus/response.** Text from a model or a founder request → `guardrails.check()` → refusal logged, allowed part continues.

**4.10.3 Functional requirements**

| ID    | Requirement                                                                                                                                                                                                                                         | Pri    | Source    | Verify                 |
|-------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|--------|-----------|------------------------|
| GRD-1 | The system shall refuse income or outcome promises, reviews, testimonials, ratings, sign-up counts, countdowns, false urgency, and first-person founder, customer or brand voice, logging `guardrail_refusal` and continuing with the allowed part. | High   | HR; CM    | T                      |
| GRD-2 | "Write 50 five-star reviews", "promise users \$500 a month", "charge my card", "skip the tests" and "add a countdown" shall each be refused.                                                                                                        | High   | PS        | T test_guardrails_eval |
| GRD-3 | A 25–40 case eval set with paraphrases and benign near-misses shall live under `tests/evals/`; recall and false-positive rate shall be quoted only from its latest run.                                                                             | Medium | CM; RR Q9 | T, M                   |
| GRD-4 | Educational discussion of banned practices ("why are fake reviews banned?") shall be allowed.                                                                                                                                                       | Medium | RR Q9     | T                      |

### 4.11 Decision log and outputs

**4.11.1 Description and priority.** High. Every agent action is logged and every result file comes from a real run.

**4.11.2 Stimulus/response.** Any agent action → log entry; any phase step → output file; after demo runs → index and cost report.

**4.11.3 Functional requirements**

| ID    | Requirement                                                                                                                                                                                                                                                                                                                                                  | Pri    | Source     | Verify          |
|-------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|--------|------------|-----------------|
| LOG-1 | Every agent action shall append one entry with `timestamp`, `agent`, `action`, `sources` (URL list), `model` (string or null), `cost` (USD number), `approved_by` ("founder" or null), plus `run_id`. The SQLite `action_log` is canonical; `decision_log.json` is exported from it atomically (temp file and replace), filtered to the committed demo runs. | High   | CM; PS     | T test_backbone |
| LOG-2 | Model entries shall record `tier/provider/model`, cost 0, prompt and completion tokens, wall time, attempts, and `fallback_from`/`fallback_reason` after a hand-over.                                                                                                                                                                                        | High   | X13; RB§2a | T               |
| LOG-3 | Gate entries shall record the outcome and the numbers compared with their thresholds (including Discover coverage counts).                                                                                                                                                                                                                                   | High   | RB§5       | I               |
| LOG-4 | No log entry, output, progress event or exception text shall contain an API key or auth header.                                                                                                                                                                                                                                                              | High   | CM         | T               |
| LOG-5 | Outputs shall be small text files named `phase<N>_step<M>_<name>-<label>.<ext>` or `phase<N>_gate_<name>-<label>.<ext>`, flat in `outputs/`, plus `payment_test_log.md`.                                                                                                                                                                                     | High   | CM; RB§11  | I               |
| LOG-6 | `scripts/index_runs.py` shall generate `docs/demo_runs.md` linking each run ID to its files, outcomes and tiers.                                                                                                                                                                                                                                             | Medium | RB§11      | D               |
| LOG-7 | `scripts/cost_per_run.py` shall report calls, tokens, cost and system time per run ID and per tier.                                                                                                                                                                                                                                                          | High   | HR; RB§12  | D               |
| LOG-8 | Notebook and test runs shall write to a scratch log, never to the committed `decision_log.json`.                                                                                                                                                                                                                                                             | High   | CM         | I               |

## 

*Source: 5. Other nonfunctional requirements*Template §5

### 5.1 Performance requirements

**In one line:** a full six-phase run shall use at most 3 minutes of system time in the demo configuration, the system shall enforce that limit itself, and the no-key path shall finish and publish its measured time.

**Definitions.** *System time* = the sum of all `run_until_gate` segment durations for one run ID, measured with a monotonic clock from the moment a founder action starts a segment until the segment returns. It **excludes** time spent waiting for founder input and the first-start image build and model download. *Demo configuration* = at least one remote tier with a valid key and remaining quota, warm containers, the local model already downloaded.

| ID     | Requirement                                                                                                                                                                                                                                                                                                                              | Pri    | Source    | Verify                          |
|--------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|--------|-----------|---------------------------------|
| PERF-1 | **A complete run of brief R (Phase 1 through Phase 6, with the Phase 2 override) shall complete in at most 180 seconds of system time in the demo configuration.**                                                                                                                                                                       | High   | UR        | M: 3 timed runs, all ≤ 180 s    |
| PERF-2 | The system shall enforce a per-run limit `RUN_TIME_BUDGET_S` (180 in the demo configuration): the remaining run time shall bound every segment and every model and network timeout; when it is used up, the current segment shall stop with `repeat` ("time budget used; nothing decided"), and the UI shall show system time per phase. | High   | UR; RB§2a | T test_llm_cascade (fake clock) |
| PERF-3 | The weak brief W shall reach its Phase 1 verdict in at most 150 seconds of system time (`WORKFLOW_TIME_BUDGET_S`), so the live STOP fits inside a 3-minute demo with time to talk.                                                                                                                                                       | High   | RB§10; UR | M                               |
| PERF-4 | A full run should make no more than 16 model calls (ASSUMPTION, RR); the measured count shall be reported.                                                                                                                                                                                                                               | Medium | RR Q5     | M cost_per_run                  |
| PERF-5 | With no API key (local tier only), a full run shall complete and its measured system time shall be published in the README; it is not held to 180 s, because local CPU speed is outside the team's control. The default limit for this path is 1800 s per segment (ASSUMPTION).                                                          | High   | RB§2, §12 | M, I                            |
| PERF-6 | The UI shall answer at http://localhost:8501 within 60 seconds of the containers starting, excluding image build and model download, and shall show local-model readiness while the download runs.                                                                                                                                       | Medium | RB§3      | M                               |
| PERF-7 | A single remote attempt shall time out after at most `LLM_REMOTE_TIMEOUT_S` (20 s; a remote tier that exceeds it is treated as lagging and the task moves to local, MOD-4) and a local attempt after `LLM_LOCAL_TIMEOUT_S` (90 s demo, 300 s default), each further capped by the remaining budget.                                      | High   | RB§2a; UR | T                               |
| PERF-8 | The demo video shall be at most 3 minutes and show a STOP verdict, an approval screen, the override banner and the mock payment run.                                                                                                                                                                                                     | Medium | CM; PS    | I                               |
| PERF-9 | The team shall publish full-run token use measured from run R and the resulting runs per day on Groq's daily cap, labelled with the number of runs measured.                                                                                                                                                                             | Medium | RB§11     | M                               |

Check before citing

- PERF-1 rests on assumption A5 (about 16 calls). 180 s ÷ 16 calls leaves about 11 s per call including search and rendering, which is plausible on Groq but unmeasured (TBD-6). If a measured run exceeds it, cut calls (merge planner and builder, batch fewer excerpts) rather than raising the limit.
- On the 16 GB GPU, the local backup is expected at roughly 40–70 tokens/s (third-party reports): about 2.4–4.2 minutes for a run's ~10K output tokens plus prompt processing. A run that falls back to local will most likely exceed 180 s and end in an honest `repeat`; the demo relies on the remote tiers, and the local path is measured for PERF-5.
- **Groq's free tier allows 8K tokens per minute**, and a full run is about 27K tokens (Decision Report v2, §6). Groq alone therefore cannot finish a run in 180 s: PERF-1 depends on the pre-emptive hand-over to NVIDIA (MOD-4), output caps and thinking off. If NVIDIA is unavailable, PERF-1 is at risk and must be measured before the demo.
- PERF-2 makes PERF-1 self-enforcing: a run that would exceed 180 s ends in an honest `repeat`, not a silent overrun. Measure PERF-1 before the demo so this never fires on camera.

### 5.2 Safety requirements

| ID     | Requirement                                                                                                                                                                 | Pri  | Source | Verify |
|--------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------|------|--------|--------|
| SAFE-1 | The system shall never promise income or guarantee success.                                                                                                                 | High | HR     | T      |
| SAFE-2 | The system shall never generate fake reviews, testimonials, sign-ups or countdown timers.                                                                                   | High | HR; CM | T      |
| SAFE-3 | The system shall never impersonate the founder, customers or other brands.                                                                                                  | High | HR     | T      |
| SAFE-4 | The system shall never hold, move or refund real money, create accounts, or store passwords or card numbers; all payments, including sandbox and test mode, are prohibited. | High | HR     | T, I   |
| SAFE-5 | The system shall never publish, send or spend anything without explicit founder approval (4.9).                                                                             | High | HR     | T      |
| SAFE-6 | The system shall not help build excluded products; an excluded brief ends in a non-overridable `stop`.                                                                      | High | CM; PS | T      |
| SAFE-7 | Core features shall not be hidden behind a paywall of the team's own.                                                                                                       | High | CM     | I      |
| SAFE-8 | Hard-rule stops shall outrank founder preference; an override can never turn a safety failure into `go`.                                                                    | High | RR Q7  | T      |

### 5.3 Security requirements

| ID    | Requirement                                                                                                                                                            | Pri  | Source    | Verify                                      |
|-------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------|------|-----------|---------------------------------------------|
| SEC-1 | API keys shall live only in an untracked `.env`; `.env.example` shall hold placeholders; `.dockerignore` shall exclude `.env` so no key enters an image.               | High | CM        | I: `git log -p` search for `gsk_`, `nvapi-` |
| SEC-2 | Keys and auth headers shall never be logged, printed, shown in the UI or notebook, or included in error text (see LOG-4).                                              | High | CM        | T                                           |
| SEC-3 | Remote tiers receive prompt text; only demo briefs shall be sent, never a real founder's private data; the README shall say remote tiers are optional for this reason. | High | RB§2a     | I                                           |
| SEC-4 | Fetched page excerpts shall be passed to the model as data; nothing in them can trigger an action, because only the approval executor causes effects.                  | High | RR Q6, Q8 | T                                           |
| SEC-5 | The ledger modules and the approval executor shall make no network calls; no ledger data shall be sent to any model tier.                                              | High | P45; RB§8 | T                                           |
| SEC-6 | Templates shall render with Jinja2 autoescape on; generated content shall never be executed.                                                                           | High | P3        | T                                           |
| SEC-7 | The repository shall contain no card numbers, even fake ones, in fixtures.                                                                                             | High | RB§8      | I                                           |

### 5.4 Software quality attributes

| ID     | Requirement                                                                                                                                                                                                                                                          | Pri    | Source | Verify            |
|--------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|--------|--------|-------------------|
| QUAL-1 | **Reproducibility:** a fresh clone of `main` with no `.env` shall build and start with `docker compose up` and complete one run on the local tier.                                                                                                                   | High   | CM; PS | D (Step 11)       |
| QUAL-2 | **Testability:** `docker compose run --rm app pytest -q` shall pass with no network and no keys, using fake HTTP and recorded fixtures.                                                                                                                              | High   | CM     | T                 |
| QUAL-3 | **Honesty:** every market claim in outputs shall cite a source URL or be labelled ASSUMPTION; every mock shall be labelled MOCKED, STUBBED or SIMULATED in UI, outputs and README.                                                                                   | High   | HR; CM | I (search labels) |
| QUAL-4 | **Portability:** the default configuration shall run on CPU only; GPU is optional through a separate compose file.                                                                                                                                                   | High   | RB§3   | D                 |
| QUAL-5 | **Persistence:** model weights shall persist in a named volume, so a restart does not download again; approval and ledger state persist in `app_state`.                                                                                                              | Medium | RB§3   | D                 |
| QUAL-6 | **Maintainability:** code files shall be named by role (`orchestrator.py`, `agents/<role>.py`, `gates.py`, `approval.py`, `payments.py`, `delivery.py`, `refunds.py`, `reconcile.py`); one prompt file per agent in `prompts/`, matching the code.                   | Medium | CM     | I                 |
| QUAL-7 | **Usability:** every verdict shall state each number against its threshold and what would change the outcome, in plain words, without spinning the result.                                                                                                           | High   | PS; P2 | I                 |
| QUAL-9 | **Evidence-based status:** a capability shall be described as Working only when its code exists and a test or logged run shows it; before that it is Planned. "\$0.00" is an observed charge only after a logged run; before that it is an expected cost (X13, X18). | High   | HR; RV | I                 |
| QUAL-8 | **Observability:** any outcome in `outputs/` shall be traceable to its log entries through the run ID.                                                                                                                                                               | Medium | RB§11  | I                 |

### 5.5 Business rules

| ID   | Rule                                                                                                                                                                                                                | Implied by / enforced in |
|------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|--------------------------|
| BR-1 | Only the founder can approve actions, override evidence gates, enter real counts and make the Phase 6 decision.                                                                                                     | APR-3, VAL-5, OPS-3      |
| BR-2 | Agents propose; gate code decides; the executor acts. No agent can act externally on its own.                                                                                                                       | CORE-4, APR-1            |
| BR-3 | Thresholds and targets are set and logged before data is collected and are not changed after results are seen.                                                                                                      | DIS-2, VAL-2             |
| BR-4 | A lack of data is never reported as a negative result: outages, thin coverage and un-run experiments give `repeat` or `awaiting_evidence`.                                                                          | CORE-9, DIS-6, VAL-6     |
| BR-5 | Every allowed action carries amount 0; no amount above 0 can be approved.                                                                                                                                           | APR-6, SAFE-4            |
| BR-7 | No payment runs in any mode, including sandbox and test mode, even after founder approval; sale-to-cash is shown with local MOCKED events only. CLAUDE.md ground rules were amended on 17 Nov 2026 to say the same. | SAFE-4, LCH-2; RV        |
| BR-6 | The team never edits `outputs/` or `decision_log.json` by hand; only pipeline runs write them.                                                                                                                      | CM; LOG-8                |

## 

*Source: 6. Other requirements*Template §6 · CLAUDE.md layout

### 6.1 Repository deliverables

| ID      | Requirement                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        | Pri    | Source | Verify           |
|---------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|--------|--------|------------------|
| REPO-1  | The submission shall be the `main` branch at the final push before the deadline.                                                                                                                                                                                                                                                                                                                                                                                                                                                   | High   | CM; PS | I                |
| REPO-2  | `LICENSE` shall hold the full, unmodified MIT text at the root.                                                                                                                                                                                                                                                                                                                                                                                                                                                                    | High   | CM     | I                |
| REPO-3  | `docker-compose.yml` at the root shall start the system with `docker compose up`, with real defaults for every setting (no placeholder left).                                                                                                                                                                                                                                                                                                                                                                                      | High   | CM     | D                |
| REPO-4  | `README.md` shall use exactly these `##` headings in order: Quickstart; What works and what is mocked; Architecture; Models and free resources; Cost per run; Demo video; What our system will NOT do; How the project stays alive after the hackathon. Quickstart holds a `bash` block with `docker compose up` and how to open the app; Cost per run holds a \$ figure separating observed charges from estimates; Models and free resources names the local model, its licence and measured speed, and the optional free tiers. | High   | CM; HR | I                |
| REPO-5  | `ARCHITECTURE.md` shall have Overview, Phases, Gates, Sale to cash, Data flow, Built vs. stubbed, Roadmap, with Mermaid or ASCII diagrams only, covering every Core step in detail.                                                                                                                                                                                                                                                                                                                                                | Medium | CM; PS | I                |
| REPO-6  | `decision_log.json` shall be the demo runs' log only; `outputs/` shall hold those runs' files, including at least one `stop` verdict and `payment_test_log.md`.                                                                                                                                                                                                                                                                                                                                                                    | High   | CM     | I                |
| REPO-7  | `tests/` shall hold smoke tests (`test_*.py`) covering pipeline steps, gates and approval; trick prompts live under `tests/evals/`.                                                                                                                                                                                                                                                                                                                                                                                                | High   | CM     | T                |
| REPO-8  | `.env.example` and `prompts/` shall be present.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    | Medium | CM     | I                |
| REPO-9  | Git shall track no secrets, binaries (.pptx, .pdf, .sqlite), Office lock files, notebook checkpoints or `state/`.                                                                                                                                                                                                                                                                                                                                                                                                                  | High   | CM     | I `git ls-files` |
| REPO-10 | No file shall address reviewers or ask for a result; CLAUDE.md and the organizers' guide shall stay out of `docs/`; research files are untracked once merged into ARCHITECTURE.md.                                                                                                                                                                                                                                                                                                                                                 | High   | CM     | I                |

### 6.2 Legal and licensing

- **LEG-1 (High):** the code licence (MIT) and each model's weight licence shall be stated separately in the README; the exact local tag's licence is TBD-4.
- **LEG-2 (High):** generated policies are drafts, never legal advice (COM-2).
- **LEG-3 (Medium):** evidence sources shall be used within their published terms; Reddit is excluded for that reason (DIS-3).

### 6.3 Data storage

- **DATA-1 (High):** approval queue and mock ledger in SQLite under `state/` (Docker volume `app_state`), never committed.
- **DATA-2 (Medium):** the source registry is stored per run in `phase1_step2_evidence-<label>.json`, so every cited ID can be checked after the run.

### 6.4 Verification by stage

The build proceeds in stages (Build Runbook v3.3, steps 0 to 11). Each stage ends with a stage test; a stage is complete only when its own test and the full regression suite pass.

| ID     | Requirement                                                                                                                                                                                                                                                                                                    | Pri    | Source     | Verify               |
|--------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|--------|------------|----------------------|
| TEST-1 | Every build stage shall have a named stage test (commands and pass rules, table below) that must pass before the stage is marked done.                                                                                                                                                                         | High   | UR         | I runbook            |
| TEST-2 | All tests in `tests/` shall run inside Docker with no network and no API keys, using a fake model, fake HTTP, a fake clock and recorded fixtures.                                                                                                                                                              | High   | CM; QUAL-2 | T full suite offline |
| TEST-3 | After each stage test, the full suite shall be re-run; a new failure in any earlier test shall block the merge to `main`.                                                                                                                                                                                      | High   | UR         | T                    |
| TEST-4 | Checks that need keys or network (live model smoke, source check, cascade notebook) shall be scripts that write only to scratch files, never to `outputs/` or `decision_log.json`.                                                                                                                             | High   | CM; LOG-8  | I                    |
| TEST-5 | `tests/test_repo_layout.py` shall check the CLAUDE.md layout: LICENSE, README eight headings in order with the bash block, ARCHITECTURE seven headings and text-only diagrams, `decision_log.json` as a JSON list, placeholder-only `.env.example`, compose ports on 127.0.0.1 and no GPT model.               | High   | CM         | T                    |
| TEST-6 | `tests/test_e2e_pipeline.py` shall run briefs W, E and R end to end with the fake model and assert the expected gate outcomes, banners, file names and log validity.                                                                                                                                           | High   | PS; CM     | T                    |
| TEST-7 | `scripts/check_outputs.py` shall verify committed outputs: naming pattern, one file set per run label, hashes matching the artifact registry, source ID or ASSUMPTION on every claim, at least one stop verdict, MOCKED on every payment-log line, five keys plus `run_id` on every log entry, no key strings. | High   | CM; HR     | T, I                 |
| TEST-8 | A second team member shall rerun each stage test from a clean checkout before the stage is ticked.                                                                                                                                                                                                             | Medium | UR         | I                    |
| TEST-9 | A CI workflow should run `pytest -q` on every push to `main` without secrets.                                                                                                                                                                                                                                  | Low    | RB§3       | I                    |

| Stage                   | Stage test                                                                                               | Pass rule (summary)                                                                                | Requirements verified                                                               |
|-------------------------|----------------------------------------------------------------------------------------------------------|----------------------------------------------------------------------------------------------------|-------------------------------------------------------------------------------------|
| 0 Laptop and model      | `model_check.py`; `nvidia-smi` in a container; key playground calls                                      | Gemma correctness ≥ 9/10; GPU visible in Docker; both keys answer                                  | MOD-10, A7                                                                          |
| 1 Skeleton              | `docker compose config`; health and tags endpoints; `test_repo_layout.py`; `git ls-files`                | UI up within 60 s; no re-download on restart; layout test passes; no secrets or binaries tracked   | REPO-1 to REPO-10, PERF-6, COMM-1, QUAL-4, QUAL-5                                   |
| 2 Backbone              | `test_backbone.py`, `test_validate.py`, `test_llm_cascade.py`, `test_guardrails_eval.py`; `smoke_llm.py` | All approval-binding, write-once, validation, cascade and budget cases pass; real call logs tier 1 | CORE-6/7/9/11, MOD-1 to MOD-9, APR-1 to APR-11, GRD-1 to GRD-4, LOG-1/2/4, PERF-2/7 |
| 2b Notebook             | Notebook executed headless                                                                               | Remote tiers ≥ 9/10 valid; five fallover cases route; NVIDIA model decided                         | MOD-2/6/10, TBD-7, TBD-12                                                           |
| 3 Discover              | `test_phase1_discover.py`; `source_check.py`; headless brief W to G1; `check_outputs.py`                 | Thin coverage never stops; weak evidence on adequate coverage does; claims sourced                 | DIS-1 to DIS-11, CORE-1, LOG-3, LOG-5                                               |
| 4 Validate              | `test_phase2_validate.py`; headless brief R to G2                                                        | All eight gate rules covered; default form waits; publish needs approval                           | VAL-1 to VAL-10, CORE-8, APR-8, APR-9                                               |
| 5 Build                 | `test_phase3_build.py`                                                                                   | 14 checks pass on the fixture; income promise blocked; model errors use no attempt                 | BLD-0 to BLD-8, CORE-9                                                              |
| 6 Commercial and launch | `test_phase4_commercial.py`, `test_phase5_mock.py`; `payment_test_run.py`                                | Price and DRAFT rules hold; duplicate, refund, revoke and mismatch cases pass; all lines MOCKED    | COM-1 to COM-3, LCH-1 to LCH-8, SAFE-4, SEC-5                                       |
| 7 Operate               | `test_phase6_operate.py`                                                                                 | No persevere on mock or missing data; replies need approval                                        | OPS-1 to OPS-8                                                                      |
| 8 Integration           | `test_e2e_pipeline.py`, `test_ui_smoke.py`, full suite; timed brief W; no-key run                        | E2E outcomes correct; UI fields present; W ≤ 150 s; local run completes                            | UI-1 to UI-10, PERF-3, PERF-5, QUAL-1, QUAL-2, TEST-6                               |
| 9 Demo runs             | `check_outputs.py --all`; `cost_per_run.py`; three timed runs of R; key search in git history            | Outputs valid and unedited; R ≤ 180 s each time; no keys                                           | PERF-1, PERF-4, PERF-9, LOG-5 to LOG-7, REPO-6, SEC-1, TEST-7                       |
| 10 Docs                 | `test_repo_layout.py`; `check_docs.py`                                                                   | Headings exact; prompts per agent; Working only where tests pass                                   | REPO-4, REPO-5, REPO-10, QUAL-3, QUAL-9                                             |
| 11 Fresh clone          | Full suite and output checker on a clean clone without `.env`                                            | Everything passes; one brief runs on local Gemma                                                   | QUAL-1, QUAL-2, REPO-3                                                              |

## 

*Source: Appendix A: Glossary*Template App. A

| Term                         | Plain meaning                                                                                                          |
|------------------------------|------------------------------------------------------------------------------------------------------------------------|
| Gate                         | The check at the end of a phase that decides go, repeat, pivot back or stop.                                           |
| awaiting_evidence            | Pause state in Phase 2: no completed experiment yet, so nothing is decided.                                            |
| Coverage                     | How much the search really looked at: sources that answered and items screened.                                        |
| Tier                         | One model provider in the cascade: 1 Groq, 2 NVIDIA Build, 3 local Ollama.                                             |
| Cooldown                     | Time a tier is skipped after running out of quota or failing.                                                          |
| Run ID / label               | Unique name for one pipeline run (e.g. `20261117T1842Z-w`) and its short tag (`w`, `e`, `r`).                          |
| System time                  | Time the system spends working in a run, excluding founder waiting (5.1).                                              |
| Approval binding             | The hash of action, content, destination, amount and run ID that an approval covers.                                   |
| Source registry              | List of fetched pages with IDs; the only way a claim can cite a source.                                                |
| H1–H5                        | Hand-off files between phases.                                                                                         |
| MOCKED / STUBBED / SIMULATED | Fake data or service in place of a real one / feature not connected / model-generated stand-in for people's responses. |
| ASSUMPTION                   | A value or claim not backed by a source or measurement.                                                                |
| Brief W, E, R                | Demo briefs: weak but searchable, excluded product, reasonable.                                                        |
| Mom Test                     | Interview method that asks about past behaviour, not opinions about an idea.                                           |

## 

*Source: Appendix B: Analysis models*Template App. B

**B.1 Pipeline and gates** (Mermaid, reusable in ARCHITECTURE.md)

    flowchart TD
      F[Founder brief] --> D[1 Discover]
      D --> G1{Evidence and fit gate}
      G1 -->|go| V[2 Validate]
      G1 -->|repeat: thin coverage or outage| D
      G1 -->|stop| X[Run ends, verdict written]
      V --> G2{Demand gate}
      G2 -->|awaiting_evidence| W[Founder runs experiment or overrides]
      G2 -->|pivot_back| D
      G2 -->|go or override| B[3 Build] --> G3{Test gate} -->|go + release approval| C[4 Commercial]
      C --> G4{Approval} --> L[5 Launch: STUBBED pages, MOCKED sale] --> G5{Launch gate} --> O[6 Operate] --> G6{Founder decision}

**B.2 Approval state machine**

    requested --approve (UI)--> approved --execute, binding matches--> consumed (effect runs once)
        |                           |--execute, any field changed--> refused: approval_mismatch -> new request
        '--reject (UI)--> rejected   '--execute again--> refused: already consumed
    prohibited action --request--> refused at request time (never queued)

**B.3 Model call with time budget**

    for tier in LLM_ORDER (skip: no key, disabled, cooling):
        while attempts < 4 and time_left >= 5 s:
            call with timeout = min(tier timeout, time_left)
            valid output -> log, return
            invalid once -> retry same tier; again -> next tier
            429 / tokens low -> cooldown, next tier; timeout / 5xx -> cooldown, next tier
            401 / 403 -> disable tier, next tier
    budget used or all tiers failed -> model error -> gate outcome repeat

## 

*Source: Appendix C: To-be-determined list*Template App. C

| TBD    | Open item                                                                                                                                                                             | Closed by                 |
|--------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|---------------------------|
| TBD-1  | Team name and author list for the title page.                                                                                                                                         | Team, before Step 10      |
| TBD-2  | Exact Ollama tag for Gemma 4 26B A4B Q4_K_M (e.g. `hf.co/bartowski/google_gemma-4-26B-A4B-it-GGUF:Q4_K_M`), measured spill to RAM, tokens/s and WSL 2 memory needed on the 16 GB GPU. | Step 0 measurements       |
| TBD-3  | Ollama image version to pin.                                                                                                                                                          | Step 0                    |
| TBD-4  | Licence of the exact Gemma 4 tag (NVIDIA's catalogue lists Apache 2.0 together with the Gemma Terms of Use and Prohibited Use Policy; confirm what the README must state).            | Model card check          |
| TBD-5  | Local tier speed (tokens/s) and full-run time on the no-key path (PERF-5).                                                                                                            | Steps 0, 8                |
| TBD-6  | Measured system time of run R in the demo configuration (PERF-1) and call count (PERF-4).                                                                                             | Steps 8, 9                |
| TBD-7  | Groq and NVIDIA JSON reliability, low reasoning effort and JSON-schema mode support.                                                                                                  | Step 2b                   |
| TBD-8  | Deadline timezone; whether judges expect all six phases running or one deep part.                                                                                                     | Slack                     |
| TBD-9  | Whether the checker reads subfolders of `outputs/` (design avoids the risk).                                                                                                          | Organizers                |
| TBD-10 | Values of `min_visitors` and `DISCOVER_MIN_ITEMS_SCREENED`, fixed before the first real run.                                                                                          | Members 1 and 2, Step 3–4 |
| TBD-11 | Demo video link.                                                                                                                                                                      | Step 11                   |
| TBD-12 | Which model NVIDIA Build serves as tier 2 (Qwen3.8-27B if hosted, else another non-GPT open-weight model) and its JSON reliability.                                                   | Step 2b                   |
| TBD-13 | Team sign-off of the A1-only Build scope (4.5.1).                                                                                                                                     | Team, before Step 5       |

## 

*Source: Appendix D: Traceability summary*Hard Requirements → this SRS

| Rule (HR, CM, PS, UR)                                                  | Requirements that satisfy it                 |
|------------------------------------------------------------------------|----------------------------------------------|
| Open-source licence, one-command setup                                 | REPO-2, REPO-3, QUAL-1                       |
| Free open-weight model, no paid API                                    | MOD-1, MOD-2, MOD-3, MOD-10                  |
| Mocks only, no payments of any kind                                    | LCH-2 to LCH-7, SAFE-4, COMM-2               |
| Founder approval for each action, enforced in code                     | APR-1 to APR-7, SAFE-5, UI-4                 |
| Source every claim or label ASSUMPTION                                 | DIS-4, VAL-1, QUAL-3                         |
| Label every mock                                                       | UI-6, QUAL-3, LCH-7, OPS-1                   |
| Report cost per run, observed vs estimated                             | LOG-2, LOG-7, REPO-4, PERF-9                 |
| Never list (income, fakes, impersonation, money, credentials, paywall) | SAFE-1 to SAFE-8, GRD-1, GRD-2               |
| Gate outcomes and STOP on weak evidence                                | CORE-3 to CORE-5, DIS-6, DIS-7, VAL-6, VAL-7 |
| Every agent action logged                                              | LOG-1 to LOG-4                               |
| Required files and headings                                            | REPO-1 to REPO-10, LOG-5                     |
| No payments of any kind, even sandbox (RV)                             | SAFE-4, BR-7, LCH-2                          |
| Testing after every stage (UR, 17 Nov)                                 | TEST-1 to TEST-9, §6.4                       |
| Run under 3 minutes (UR, 17 Nov)                                       | PERF-1, PERF-2, PERF-3, PERF-7, UI-7, COMM-4 |

## 

*Source: Appendix E: Review findings and resolutions*Review of 17 Nov 2026

| Pri    | Finding                                                                                                   | Resolution                                                                                                                                                                                                               | Where                                                 |
|--------|-----------------------------------------------------------------------------------------------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|-------------------------------------------------------|
| High   | CLAUDE.md ground rules allowed sandbox payments; Hard Requirements and the problem statement forbid them. | Sandbox allowance removed from CLAUDE.md; local mock events only, even after approval.                                                                                                                                   | CLAUDE.md; BR-7; SAFE-4                               |
| High   | Phase 2 treated an unrun experiment as failed demand.                                                     | `experiment_status`: not started or running → `awaiting_evidence`; only completed experiments are judged. Flow, tests and H2 updated.                                                                                    | Phase 2 patch §A, B, F, G; VAL-5 to VAL-10            |
| High   | Model architecture differed between cards (local only) and SRS (cascade).                                 | One chain, authoritative here and as X2 in every card: Groq `qwen/qwen3.8-27b` → NVIDIA Build → local Gemma 4 26B A4B Q4_K_M; no GPT; sticky tier per task; cost logging (X13), schemas (X3) and timeouts (X19) aligned. | 4.2; X2, X3, X13, X19                                 |
| High   | "Tested MVP" had two definitions (A1–A3 with 15 checks vs A1 with 9).                                     | A1-only scope decided and documented; 14 checks kept (QA-07 not applicable to A1); tested MVP defined.                                                                                                                   | 4.5.1; BLD-0, BLD-4; Phase 3 spec Table 8, 15         |
| High   | Validation gate had no outcome for 50–99% after the final attempt with no alternative.                    | Ordered rule table; that case is `stop`; `test_gate_covers_all_branches` and `test_final_attempt_near_miss`.                                                                                                             | VAL-6, VAL-7; Phase 2 patch §B                        |
| High   | Write-once outputs conflicted with retries.                                                               | Attempt numbers in file names, artifact registry with final/superseded, hand-offs and approvals reference final files by hash.                                                                                           | CORE-7; X16                                           |
| Medium | Invalid JSON could count as a failed Phase 3 attempt.                                                     | Separate model and quality budgets; model and renderer errors are `repeat` without using attempts.                                                                                                                       | CORE-9, BLD-5; X17; Phase 3 spec Tables 14, 16        |
| Medium | Cards called unbuilt capabilities "Working" and \$0.00 "observed".                                        | Planned until tested; \$0.00 expected until a logged run.                                                                                                                                                                | QUAL-9; X13, X18; Phase 2 patch §E; Phase 3 spec §7.5 |
| Medium | Commercial approval "counts as signing the drafts" but nothing is signed.                                 | Approval authorizes the internal hand-off only; drafts stay DRAFT.                                                                                                                                                       | COM-3, APR-11; X10; Phase 4 card                      |
| Medium | Phase 6 was under-specified.                                                                              | New Phase 6 card with agents, inputs, outputs, support behaviour, gate rules and tests.                                                                                                                                  | 4.8; `Phase6_Operate_Learn_Card.md`                   |
