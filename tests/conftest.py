"""Shared offline fixtures: no network, no API keys (SRS TEST-2).

- `env`: isolates STATE_DIR, OUTPUTS_DIR and DECISION_LOG_PATH in a temp folder.
- `fake_llm`: a schema-driven FakeLLM; tests can override single actions.
- `fake_sources`: recorded-style responses for HN Algolia, Stack Exchange, GitHub and Wikipedia.
- `founder`: a test-only founder that answers pauses (the real app only answers on a UI button
  or a typed CLI answer).
"""
import json
import os
import re
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import llm  # noqa: E402
import sources  # noqa: E402

FIX = os.path.join(ROOT, "tests", "fixtures")


@pytest.fixture(autouse=True)
def env(tmp_path, monkeypatch):
    monkeypatch.setenv("STATE_DIR", str(tmp_path / "state"))
    monkeypatch.setenv("OUTPUTS_DIR", str(tmp_path / "outputs"))
    monkeypatch.setenv("DECISION_LOG_PATH", str(tmp_path / "decision_log.json"))
    for k in list(os.environ):
        if k.startswith(("LLM_", "GROQ_", "NVIDIA_", "LOCAL_", "DISCOVER_", "VALIDATE_", "MAX_BUILD", "MOCK_", "RUN_TIME", "WORKFLOW_")):
            monkeypatch.delenv(k, raising=False)
    monkeypatch.setenv("WORKFLOW_TIME_BUDGET_S", "1800")
    llm.reset_state()
    llm.set_fake(None)
    llm.set_transport(_no_network)
    sources.set_http(_no_network_get)
    yield tmp_path
    llm.set_fake(None)


def _no_network(*a, **k):
    raise OSError("network disabled in tests")


def _no_network_get(*a, **k):
    raise OSError("network disabled in tests")


def load_brief(name):
    with open(os.path.join(FIX, f"brief_{name}.json"), encoding="utf-8") as f:
        b = json.load(f)
    return b, b.pop("founder_inputs", {})


# ------------------------------------------------------------------ FakeLLM
def gen(schema, ids, key=""):
    t = schema.get("type")
    if t == "object":
        props = schema.get("properties", {})
        d = {k: gen(v, ids, k) for k, v in props.items()}
        if "source_ids" in props:
            mn = props["source_ids"].get("minItems", 0)
            d["source_ids"] = ids[:max(mn, 3)] if ids else []
            if "assumption" in props:
                d["assumption"] = not d["source_ids"]
        return d
    if t == "array":
        n = schema.get("minItems", 1) or 1
        if schema.get("maxItems"):
            n = min(n, schema["maxItems"])
        return [gen(schema["items"], ids, key) for _ in range(n)]
    if t == "string":
        if "enum" in schema:
            return schema["enum"][0]
        return f"Plain {key.replace('_', ' ')} text"
    if t == "integer":
        return 4 if schema.get("maximum") == 5 else schema.get("minimum", 1)
    if t == "boolean":
        return False
    return None


class FakeLLM:
    def __init__(self, overrides=None, relevant=True):
        self.overrides = overrides or {}
        self.relevant = relevant
        self.calls = []

    def __call__(self, system, user, schema, agent, action):
        self.calls.append(action)
        ids = re.findall(r"\[(S\d{3})\]", user)
        if action in self.overrides:
            o = self.overrides[action]
            return o(system, user, schema, ids) if callable(o) else o
        if action == "screen_evidence":
            rel = self.relevant
            return {"items": [{"source_id": i, "relevant": (rel(i) if callable(rel) else rel),
                               "pain_point": f"Person describes difficulty tracking tasks ({i})"} for i in ids[:5]]}
        return gen(schema, ids)


@pytest.fixture
def fake_llm():
    f = FakeLLM()
    llm.set_fake(f)
    return f


# ------------------------------------------------------------------ fake sources
class FakeSources:
    """scenario: rich (3 sources x many items), thin (2 sources, few items), outage."""

    def __init__(self, scenario="rich", per_source=12):
        self.scenario = scenario
        self.per = per_source

    def __call__(self, url, timeout):
        if self.scenario == "outage":
            return 503, ""
        n = self.per if self.scenario == "rich" else 3
        if "hn.algolia.com" in url:
            return 200, json.dumps({"hits": [{"objectID": f"{1000 + i}", "title": f"Ask HN: planning tool pain {i}",
                                              "comment_text": f"I keep losing track of vendors and deadlines {i}"} for i in range(n)]})
        if "api.stackexchange.com" in url:
            if self.scenario == "thin":
                return 200, json.dumps({"items": [{"question_id": 50 + i, "title": f"Tracking planner tasks {i}", "excerpt": "spreadsheet tracking"} for i in range(1)]})
            return 200, json.dumps({"items": [{"question_id": 500 + i + (100 if "stackoverflow" in url else 0), "title": f"Template for planning tasks {i}", "excerpt": "how do I track tasks"} for i in range(n // 2)]})
        if "api.github.com" in url:
            if self.scenario == "thin":
                return 403, ""
            return 200, json.dumps({"items": [{"html_url": f"https://github.com/example/planner/issues/{i}", "title": f"Checklist feature request {i}", "body": "need a checklist"} for i in range(n)]})
        if "wikipedia.org" in url:
            return 200, json.dumps({"query": {"search": [{"title": "Wedding planner", "snippet": "background"}]}})
        return 200, "<html><title>Competitor template</title><body>Price $19 one-time</body></html>"


@pytest.fixture
def fake_sources():
    f = FakeSources("rich")
    sources.set_http(f)
    return f


# ------------------------------------------------------------------ test founder
class TestFounder:
    """Answers pauses in tests. In the product only a UI button or a typed CLI answer can do this."""
    __test__ = False

    def __init__(self, prefill, script=None):
        self.prefill = prefill
        self.script = script or {}

    def answer(self, pause):
        kind, phase = pause["kind"], pause.get("phase")
        key = f"{kind}:{phase}:{pause.get('form', pause.get('action', ''))}"
        if key in self.script:
            v = self.script[key]
            return v(pause) if callable(v) else v
        if kind == "approval":
            return {"choice": "approve"}
        if kind == "input":
            form = pause["form"]
            return {"real_counts": self.prefill.get("p2_counts") or {"experiment_status": "not_started"},
                    "persona_test": self.prefill.get("p2_persona_test") or {"run": False},
                    "price_quotes": {"quotes": self.prefill.get("p4_quotes", [])},
                    "mock_sale": self.prefill.get("p5_mock_sale") or {"simulate_purchase": True, "simulate_refund": True},
                    "targets": {"targets": self.prefill.get("p6_targets", {})},
                    "metrics": {"metrics": self.prefill.get("p6_metrics", [])}}[form]
        if kind == "gate":
            opts = pause["options"]
            if phase == 6:
                return {"choice": "stop"}
            if "continue" in opts:
                return {"choice": "continue"}
            if "override" in opts:
                return {"choice": "override", "reason": self.prefill.get("override_reasons", {}).get(str(phase), "Founder accepts the risk to see later phases"),
                        "experimental_price": 15, "currency": "USD"}
            return {"choice": "stop"}
        return {"choice": "stop"}


def drive(ctx, founder, max_steps=60):
    import orchestrator
    pauses = []
    for _ in range(max_steps):
        p = orchestrator.run_until_gate(ctx)
        pauses.append(p)
        if p["kind"] == "done":
            return pauses
        orchestrator.respond(ctx, founder.answer(p), "button")
    raise AssertionError("pipeline did not finish")
