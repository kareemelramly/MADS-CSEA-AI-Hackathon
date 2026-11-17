# FAQ

**Does it cost anything to run?** No. The model runs locally through llama.cpp; observed model and API charges are $0.00 per run ([cost_report.md](cost_report.md)). Electricity and hardware are not counted (ASSUMPTION).

**Does my idea leave my computer?** Only short search words built from it, sent to keyless public APIs (HN Algolia, Stack Exchange, GitHub search, Wikipedia for background). The brief, drafts and model stay local.

**Can the AI decide that my idea is good?** No. The model writes text and JSON; plain code in `gates.py` decides every gate against thresholds logged before any data.

**What if I disagree with a STOP?** For evidence-based gates you can continue with a typed reason of at least 20 characters. The original verdict stays in the log, an amber bar stays on screen, and every later file is stamped UNVALIDATED. Excluded products, guardrail refusals, the test gate and the payment ban cannot be overridden.

**Will it publish or post anything for me?** No. Publishing, posting and sending are STUBBED: after you approve an exact action, the system only records what it would have done.

**Does it take payments?** No payment of any kind runs, not even sandbox or test mode. The sale-to-cash flow is a MOCKED local SQLite ledger used to prove delivery, refund and reconciliation logic.

**Which products does it refuse?** Physical goods; financial, investment or crypto products; health or legal advice products.

**How do I run it?** `docker compose up`, then open http://localhost:8501. Step-by-step help: [how_to_run.md](how_to_run.md).

**How do I contribute a new agent?** Add `agents/<role>.py`, one prompt in `prompts/<role>.md`, a JSON schema in `schemas/`, and an offline test; `pytest -q` must pass without network or keys.
