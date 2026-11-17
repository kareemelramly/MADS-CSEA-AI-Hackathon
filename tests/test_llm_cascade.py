"""Local model client with fake HTTP and a fake clock: no network (SRS MOD-1 to MOD-9, PERF-2, PERF-7).
Only one provider exists: the llama.cpp server on this machine. No hosted API is called."""
import json
import socket

import pytest

import llm
import orchestrator
from run_context import RunContext

SCHEMA = {"type": "object", "properties": {"answer": {"type": "string"}}, "required": ["answer"]}
GOOD = json.dumps({"choices": [{"message": {"content": json.dumps({"answer": "ok"})}}], "usage": {"prompt_tokens": 10, "completion_tokens": 5}})
BAD = json.dumps({"choices": [{"message": {"content": "not json at all"}}]})


class Clock:
    def __init__(self):
        self.t = 1000.0

    def __call__(self):
        return self.t


class Net:
    """Scripted responses: list of 'ok', 'bad', '400', '500', 'hang'."""

    def __init__(self, clock, script):
        self.clock, self.script, self.calls, self.bodies = clock, list(script), [], []

    def __call__(self, url, headers, body, timeout):
        self.calls.append((url, round(timeout, 1)))
        self.bodies.append(body)
        assert "Authorization" not in headers
        step = self.script.pop(0) if len(self.script) > 1 else (self.script[0] if self.script else "ok")
        self.clock.t += 1
        if step == "ok":
            return 200, {}, GOOD
        if step == "bad":
            return 200, {}, BAD
        if step == "400":
            return 400, {}, ""
        if step == "500":
            return 500, {}, ""
        if step == "hang":
            self.clock.t += timeout
            raise socket.timeout("timed out")
        raise AssertionError(step)


@pytest.fixture
def setup(monkeypatch):
    clock = Clock()
    llm.set_clock(clock)
    yield clock, monkeypatch
    import time
    llm.set_clock(time.monotonic)


def mkctx(clock, budget=1800):
    import os
    os.environ["WORKFLOW_TIME_BUDGET_S"] = str(budget)
    c = RunContext(brief={}, label="t")
    c.start_segment(clock)
    return c


def ask(ctx, **kw):
    return llm.ask("sys", "user", SCHEMA, "tester", "act", ctx=ctx, **kw)


def models(env):
    return [e["model"] for e in json.load(open(env / "decision_log.json")) if e["action"] == "act"]


def test_only_the_local_tier_exists_even_with_hosted_settings(env, monkeypatch):
    monkeypatch.setenv("LLM_ORDER", "nvidia,groq,local")
    monkeypatch.setenv("NVIDIA_API_KEY", "nvapi-testkeytestkey")
    ts = llm.tiers()
    assert [t["name"] for t in ts] == ["local"] and ts[0]["local"]


def test_local_answer_is_logged_with_model_and_zero_cost(env, setup):
    clock, mp = setup
    net = Net(clock, ["ok"])
    llm.set_transport(net)
    assert ask(mkctx(clock)) == {"answer": "ok"}
    assert len(net.calls) == 1 and net.calls[0][0].endswith("/v1/chat/completions")
    entry = [e for e in json.load(open(env / "decision_log.json")) if e["action"] == "act"][0]
    assert entry["model"].startswith("local/llamacpp/") and entry["cost"] == 0
    assert net.bodies[0]["response_format"]["type"] == "json_schema"


def test_bad_json_retries_once_with_the_error(env, setup):
    clock, mp = setup
    net = Net(clock, ["bad", "ok"])
    llm.set_transport(net)
    assert ask(mkctx(clock)) == {"answer": "ok"}
    assert len(net.calls) == 2
    assert "previous answer was rejected" in net.bodies[1]["messages"][1]["content"]


def test_bad_json_twice_is_model_error(env, setup):
    clock, mp = setup
    net = Net(clock, ["bad", "bad", "ok"])
    llm.set_transport(net)
    with pytest.raises(llm.ModelError):
        ask(mkctx(clock))
    assert len(net.calls) == 2


def test_server_error_is_model_error(env, setup):
    clock, mp = setup
    llm.set_transport(Net(clock, ["500"]))
    with pytest.raises(llm.ModelError):
        ask(mkctx(clock))


def test_400_retries_without_extras_then_plain_json(env, setup):
    clock, mp = setup
    net = Net(clock, ["400", "400", "ok"])
    llm.set_transport(net)
    assert ask(mkctx(clock)) == {"answer": "ok"}
    assert "chat_template_kwargs" in net.bodies[0] and "chat_template_kwargs" not in net.bodies[1]
    assert "response_format" not in net.bodies[2]


def test_max_attempts_per_call(env, setup):
    clock, mp = setup
    net = Net(clock, ["bad"])
    llm.set_transport(net)
    with pytest.raises(llm.ModelError):
        ask(mkctx(clock))
    assert len(net.calls) <= 4


def test_budget_bounds_a_hanging_server(env, setup):
    clock, mp = setup
    llm.set_transport(Net(clock, ["hang"]))
    c = mkctx(clock, budget=30)
    start = clock.t
    with pytest.raises(llm.ModelError):
        ask(c)
    assert clock.t - start <= 30 + 1


def test_no_attempt_starts_without_budget(env, setup):
    clock, mp = setup
    net = Net(clock, ["ok"])
    llm.set_transport(net)
    c = mkctx(clock, budget=3)
    with pytest.raises(llm.ModelError) as ei:
        ask(c)
    assert ei.value.kind == "budget" and net.calls == []


def test_failure_is_logged_without_secrets(env, setup):
    clock, mp = setup
    mp.setenv("NVIDIA_API_KEY", "nvapi-testkeytestkey")
    events = []
    llm.set_transport(Net(clock, ["500"]))
    with pytest.raises(llm.ModelError) as ei:
        ask(mkctx(clock), on_progress=events.append)
    blob = open(env / "decision_log.json").read() + json.dumps(events) + str(ei.value) + json.dumps(llm.status())
    assert "nvapi-" not in blob
    assert events[0]["status"] == "trying"
    assert any(e["action"] == "model_error" for e in json.load(open(env / "decision_log.json")))


def test_budget_error_becomes_repeat_in_orchestrator(env, setup, fake_sources):
    clock, mp = setup
    llm.set_transport(Net(clock, ["hang"]))
    from conftest import load_brief
    b, _ = load_brief("r")
    mp.setenv("WORKFLOW_TIME_BUDGET_S", "10")
    ctx = orchestrator.new_run(b, "t")
    p = orchestrator.run_until_gate(ctx, clock=clock)
    assert p["kind"] == "error" and p["outcome"] == "repeat"
    assert "nothing decided" in p["verdict"]
    assert not any(e.get("outcome") == "stop" for e in json.load(open(env / "decision_log.json")))


def test_no_gpt_model_allowed(env, monkeypatch):
    monkeypatch.setenv("LOCAL_MODEL", "gpt-oss-20b")
    with pytest.raises(RuntimeError):
        llm.tiers()


def test_untrusted_model_endpoint_is_rejected(env, monkeypatch):
    monkeypatch.setenv("LOCAL_BASE_URL", "https://api.example.com/v1")
    with pytest.raises(RuntimeError, match="LOCAL_BASE_URL"):
        llm.tiers()
