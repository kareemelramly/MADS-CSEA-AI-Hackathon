# Design decisions

The choices behind the system, with the alternative we rejected and why. Each one traces to our architecture decision record (ADR) numbering.

| # | Decision | Rejected alternative | Why |
|---|---|---|---|
| ADR-01 | A fixed Python state machine runs the six phases; agents are role functions with one prompt and one JSON schema each | An LLM "manager" agent or a swarm that decides what to do next | Every transition is known and testable offline; a gate can never be skipped by a model's wording; 15–16 model calls per full run instead of 25–100+ |
| ADR-02 | One approval executor is the only path to any effect; approval binds action, content hash, destination, amount and run ID, and is single-use | A boolean "approved" flag in the UI | A changed page, price or recipient after approval is refused and logged with the changed field; a consumed approval cannot fire twice |
| ADR-03 | Every loop is bounded: 1 search broadening, 1 repair per tier, 4 attempts per call, 3 builds, 2 demand experiments, at most one pivot per gate | Open-ended retries | Runs always end, and the founder sees why |
| ADR-04 | SQLite is the source of truth; `decision_log.json` is exported atomically from it | Appending to JSON directly | Crash-safe log, approvals and mock ledger |
| ADR-05 | No agent framework | LangGraph, CrewAI, AutoGen | The approval executor and gates would still be custom; plain Python keeps the code small and auditable |
| ADR-06 | Code owns every business and safety decision; checks run in the order hard rules → data completeness → locked thresholds → founder | Asking the model "should we continue?" | The model proposes text; numbers and outcomes come from code with thresholds logged before data |
| ADR-07 | Rules first: deterministic guardrails on every generated text and every request | A second "critic" model as the safety gate | Reproducible, testable, no extra calls; a critic can be added later for quality only |
| ADR-08 | Missing data is never a negative verdict: thin search → `repeat`, unrun experiment → `awaiting_evidence`, model outage → `repeat` | Treating zero sign-ups from an unrun test as failure | Honest results; the system says "stop" only after evidence was really examined |
| — | Source registry: the model sees source IDs and excerpts, code renders the URLs | Letting the model write links | Invented links become impossible; unsourced claims print as ASSUMPTION |
| — | Product scope A1 (checklist pack) built from a team template; model fills text only | Model-generated code or HTML | Fourteen deterministic checks can prove the product works without running generated code |
| — | Local model first-class (llama.cpp, Gemma 4 26B A4B Q4_K_M); remote tier optional with automatic fallback | Depending on a hosted API | A fresh clone with no keys still runs everything at $0 |
