"""Hour-one model check (gate 0): JSON validity and speed, thresholds fixed before running.

Usage:
    python scripts/model_check.py
    python scripts/model_check.py gpt-oss:20b      # test the fallback model

Needs only the Python standard library and a running Ollama server on localhost:11434.
"""
import json
import sys
import time
import urllib.request

MODEL = sys.argv[1] if len(sys.argv) > 1 else "hf.co/unsloth/gemma-4-26B-A4B-it-GGUF:UD-IQ4_XS"
URL = "http://localhost:11434/api/chat"
NUM_CTX = 16384

# Gate thresholds, set BEFORE the run (ASSUMPTION values; change them only before running).
GATE_MIN_VALID = 9          # out of 10 briefs, after one retry each
GATE_MIN_TOKENS_PER_S = 40  # generation speed
GATE_MAX_SECONDS_PER_CALL = 30

SCHEMA = {
    "type": "object",
    "properties": {
        "idea_summary": {"type": "string"},
        "target_customer": {"type": "string"},
        "pain_points": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "claim": {"type": "string"},
                    "evidence": {"type": "string", "description": "a source URL, or the word ASSUMPTION"},
                },
                "required": ["claim", "evidence"],
            },
        },
        "alternatives": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"name": {"type": "string"}, "score_0_to_10": {"type": "integer"}},
                "required": ["name", "score_0_to_10"],
            },
        },
        "excluded_category": {"type": "boolean"},
        "confidence": {"type": "string", "enum": ["low", "medium", "high"]},
    },
    "required": ["idea_summary", "target_customer", "pain_points", "alternatives",
                 "excluded_category", "confidence"],
}

SYSTEM = (
    "You are the Discover agent. Return only JSON matching the schema. "
    "You have no search results, so every pain point's evidence must be the word ASSUMPTION. "
    "Give exactly 2 alternatives. Set excluded_category true for physical goods, financial, "
    "investment or crypto products, and health or legal advice products. Never promise income."
)

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
    body = {
        "model": MODEL,
        "messages": [{"role": "system", "content": SYSTEM}, {"role": "user", "content": brief}],
        "format": SCHEMA,
        "stream": False,
        "think": False,
        "options": {"num_ctx": NUM_CTX, "temperature": 0.2},
    }
    req = urllib.request.Request(URL, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    start = time.time()
    with urllib.request.urlopen(req, timeout=300) as r:
        data = json.loads(r.read())
    wall = time.time() - start
    tps = data.get("eval_count", 0) / max(data.get("eval_duration", 1) / 1e9, 1e-9)
    return data["message"]["content"], wall, tps


def valid(text):
    try:
        obj = json.loads(text)
    except json.JSONDecodeError:
        return False
    if not all(k in obj for k in SCHEMA["required"]):
        return False
    if len(obj["alternatives"]) != 2:
        return False
    return all(p.get("evidence", "").startswith(("http", "ASSUMPTION")) for p in obj["pain_points"])


def main():
    results, ok = [], 0
    for i, brief in enumerate(BRIEFS, 1):
        attempt_ok = False
        for attempt in (1, 2):
            text, wall, tps = call(brief)
            attempt_ok = valid(text)
            if attempt_ok:
                break
        ok += attempt_ok
        results.append({"brief": i, "valid": attempt_ok, "attempts": attempt, "seconds": round(wall, 1),
                        "tokens_per_s": round(tps, 1), "output": text[:400]})
        print(f"[{i:2}] valid={attempt_ok} attempts={attempt} {wall:5.1f}s {tps:6.1f} tok/s")

    avg_tps = sum(r["tokens_per_s"] for r in results) / len(results)
    max_s = max(r["seconds"] for r in results)
    passed = ok >= GATE_MIN_VALID and avg_tps >= GATE_MIN_TOKENS_PER_S and max_s <= GATE_MAX_SECONDS_PER_CALL
    summary = {"model": MODEL, "valid": f"{ok}/10", "avg_tokens_per_s": round(avg_tps, 1),
               "slowest_call_s": max_s, "gate": "go" if passed else "repeat_with_fallback_model",
               "thresholds": {"min_valid": GATE_MIN_VALID, "min_tps": GATE_MIN_TOKENS_PER_S,
                              "max_s_per_call": GATE_MAX_SECONDS_PER_CALL}}
    print(json.dumps(summary, indent=2))
    with open("model_check_result.json", "w", encoding="utf-8") as f:
        json.dump({"summary": summary, "runs": results}, f, indent=2)


if __name__ == "__main__":
    main()
