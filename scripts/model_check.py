"""Hour-one model check (gate 0): JSON correctness and speed, measured as two separate results.

Targets the local llama.cpp server (OpenAI-compatible) by default. Standard library only.
    python scripts/model_check.py [base_url]       # default http://127.0.0.1:8080/v1
Writes model_check_result.json (gitignored). Correctness decides whether a model can be the local
tier; speed only decides how it is described (runbook Step 0, MOD-10).
"""
import json
import sys
import time
import urllib.request

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8080/v1"
GATE_MIN_VALID = 9          # out of 10 briefs, after one retry each (ASSUMPTION, fixed before running)
GATE_MIN_TOKENS_PER_S = 40
GATE_MAX_SECONDS_PER_CALL = 30

SCHEMA = {"type": "object", "properties": {
    "idea_summary": {"type": "string"}, "target_customer": {"type": "string"},
    "pain_points": {"type": "array", "items": {"type": "object", "properties": {"claim": {"type": "string"}, "evidence": {"type": "string"}}, "required": ["claim", "evidence"]}},
    "alternatives": {"type": "array", "items": {"type": "object", "properties": {"name": {"type": "string"}, "score_0_to_10": {"type": "integer", "minimum": 0, "maximum": 10}}, "required": ["name", "score_0_to_10"]}},
    "excluded_category": {"type": "boolean"}, "confidence": {"type": "string", "enum": ["low", "medium", "high"]}},
    "required": ["idea_summary", "target_customer", "pain_points", "alternatives", "excluded_category", "confidence"]}
SYSTEM = ("You are the Discover agent. Return only JSON matching the schema. You have no search results, so every pain point's "
          "evidence must be the word ASSUMPTION. Give exactly 2 alternatives. Set excluded_category true for physical goods, financial, "
          "investment or crypto products, and health or legal advice products. Never promise income.")
BRIEFS = [
    "Idea: Notion templates for wedding planners. Skills: design. Budget: $200. Time: 10 h/week. Market: Egypt. Values: honesty.",
    "Idea: a browser extension that summarises Arabic news. Skills: JavaScript. Budget: $0. Time: 15 h/week. Market: MENA students.",
    "Idea: a crypto trading signal bot. Skills: Python. Budget: $500. Time: 20 h/week. Market: retail traders.",
    "Idea: an online course on Excel for accountants. Skills: accounting. Budget: $100. Time: 5 h/week. Market: junior accountants.",
    "Idea: AI-generated workout plans. Skills: fitness coaching. Budget: $300. Time: 10 h/week. Market: gym beginners.",
    "Idea: a Figma UI kit for fintech dashboards. Skills: UI design. Budget: $0. Time: 8 h/week. Market: startup designers.",
    "Idea: resume review checklists as a PDF pack. Skills: HR. Budget: $50. Time: 4 h/week. Market: fresh graduates.",
    "Idea: a Telegram bot that tracks university deadlines. Skills: Python. Budget: $0. Time: 12 h/week. Market: AUC students.",
    "Idea: handmade leather wallets sold online. Skills: crafting. Budget: $1000. Time: 20 h/week. Market: Cairo.",
    "Idea: a spreadsheet budgeting template for freelancers. Skills: finance basics. Budget: $0. Time: 6 h/week. Market: freelancers.",
]


def call(brief):
    body = {"model": "local", "messages": [{"role": "system", "content": SYSTEM}, {"role": "user", "content": brief}],
            "response_format": {"type": "json_schema", "json_schema": {"name": "out", "schema": SCHEMA}},
            "temperature": 0.2, "max_tokens": 800, "chat_template_kwargs": {"enable_thinking": False}}
    req = urllib.request.Request(BASE.rstrip("/") + "/chat/completions", data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    t = time.time()
    with urllib.request.urlopen(req, timeout=300) as r:
        data = json.loads(r.read())
    dt = time.time() - t
    toks = (data.get("usage") or {}).get("completion_tokens") or 0
    tps = (data.get("timings") or {}).get("predicted_per_second") or (toks / dt if dt else 0)
    return data["choices"][0]["message"]["content"], dt, tps


def valid(text):
    try:
        o = json.loads(text)
    except ValueError:
        return False
    if not all(k in o for k in SCHEMA["required"]):
        return False
    if o["confidence"] not in ("low", "medium", "high"):
        return False
    if not all(isinstance(a.get("score_0_to_10"), int) and 0 <= a["score_0_to_10"] <= 10 for a in o["alternatives"]):
        return False
    return all(p.get("evidence") == "ASSUMPTION" for p in o["pain_points"])


def server_up():
    try:
        with urllib.request.urlopen(BASE.rstrip("/").rsplit("/v1", 1)[0] + "/health", timeout=5) as r:
            return r.status == 200
    except Exception:  # noqa: BLE001
        return False


def main():
    if not server_up():
        print("The local model server is not running at " + BASE + ". Start it with: bash scripts/start_local_llm.sh "
              "(if it stops again, run: tail -30 state/llama-server.log). No result was written.")
        return 2
    ok, times, speeds = 0, [], []
    for i, b in enumerate(BRIEFS, 1):
        good = False
        for _ in range(2):
            try:
                text, dt, tps = call(b)
            except Exception as e:  # noqa: BLE001
                print(f"{i:2d} error {type(e).__name__}: {e}")
                if not server_up():
                    print("The local model server stopped while answering (it probably crashed). "
                          "See: tail -30 state/llama-server.log. No result was written.")
                    return 2
                continue
            times.append(dt)
            speeds.append(tps)
            if valid(text):
                good = True
                break
        ok += good
        print(f"{i:2d} valid={good} last_call={times[-1] if times else 0:.1f}s tok/s={speeds[-1] if speeds else 0:.1f}")
    avg_tps = sum(speeds) / len(speeds) if speeds else 0
    max_s = max(times) if times else 0
    correct = ok >= GATE_MIN_VALID
    fast = avg_tps >= GATE_MIN_TOKENS_PER_S and max_s <= GATE_MAX_SECONDS_PER_CALL
    summary = {"base_url": BASE, "valid": ok, "of": len(BRIEFS), "avg_tokens_per_s": round(avg_tps, 1), "max_seconds_per_call": round(max_s, 1),
               "correctness": "pass" if correct else "fail", "performance": "fast" if fast else "slow",
               "local_tier": "keep_fast" if correct and fast else "keep_slow_document_numbers" if correct else "try_next_candidate",
               "measured_at": time.strftime("%Y-%m-%dT%H:%M:%S")}
    json.dump(summary, open("model_check_result.json", "w"), indent=1)
    print(json.dumps(summary, indent=1))
    return 0 if correct else 1


if __name__ == "__main__":
    sys.exit(main())
