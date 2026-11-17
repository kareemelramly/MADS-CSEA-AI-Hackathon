"""Model cascade with fake HTTP and a fake clock: no network, no keys (SRS MOD-1 to MOD-9, PERF-2, PERF-7)."""
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
    """Scripted responses per tier: list of 'ok', 'bad', '429', '401', '500', 'hang', 'lowtok'."""

    def __init__(self, clock, script):
        self.clock, self.script, self.calls = clock, {k: list(v) for k, v in script.items()}, []

    def __call__(self, url, headers, body, timeout):
        tier = "groq" if "groq" in url else "nvidia" if "nvidia" in url else "local"
        self.calls.append((tier, round(timeout, 1)))
        assert "Authorization" not in headers or headers["Authorization"].startswith("Bearer ")
        steps = self.script.get(tier) or ["ok"]
        step = steps.pop(0) if len(steps) > 1 else steps[0]
        self.clock.t += 1
        if step == "ok":
            return 200, {}, GOOD
        if step == "lowtok":
            return 200, {"x-ratelimit-remaining-tokens": "10", "x-ratelimit-reset-tokens": "7.5s"}, GOOD
        if step == "bad":
            return 200, {}, BAD
        if step == "429":
            return 429, {"retry-after": "41"}, ""
        if step == "401":
            return 401, {}, ""
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


def keys(mp, groq=True, nvidia=True):
    if groq:
        mp.setenv("GROQ_API_KEY", "gsk_testkeytestkey")
    if nvidia:
        mp.setenv("NVIDIA_API_KEY", "nvapi-testkeytestkey")


def ask(ctx, **kw):
    return llm.ask("sys", "user", SCHEMA, "tester", "act", ctx=ctx, **kw)


def models(env):
    return [e["model"] for e in json.load(open(env / "decision_log.json")) if e["action"] == "act"]


def test_no_keys_uses_local_only(env, setup):
    clock, mp = setup
    net = Net(clock, {})
    llm.set_transport(net)
    assert ask(mkctx(clock)) == {"answer": "ok"}
    assert [c[0] for c in net.calls] == ["local"]
    assert models(env)[0].startswith("tier3/llamacpp/")


def test_groq_429_goes_to_nvidia_at_once(env, setup):
    clock, mp = setup
    keys(mp)
    net = Net(clock, {"groq": ["429"]})
    llm.set_transport(net)
    ask(mkctx(clock))
    assert [c[0] for c in net.calls] == ["groq", "nvidia"]
    e = json.load(open(env / "decision_log.json"))[-1]
    assert e["fallback_from"] == "groq" and e["fallback_reason"] == "429"


def test_tokens_low_skips_groq_next_call(env, setup):
    clock, mp = setup
    keys(mp)
    net = Net(clock, {"groq": ["lowtok"]})
    llm.set_transport(net)
    c = mkctx(clock)
    ask(c)
    net.calls.clear()
    ask(c)
    assert [x[0] for x in net.calls] == ["nvidia"]


def test_remote_lag_moves_to_local(env, setup):
    clock, mp = setup
    keys(mp)
    net = Net(clock, {"groq": ["hang"], "nvidia": ["hang"]})
    llm.set_transport(net)
    ask(mkctx(clock))
    assert [c[0] for c in net.calls] == ["groq", "local"]       # lag rule: straight to local
    assert net.calls[0][1] <= 20


def test_401_disables_tier(env, setup):
    clock, mp = setup
    keys(mp)
    net = Net(clock, {"groq": ["401"]})
    llm.set_transport(net)
    c = mkctx(clock)
    ask(c)
    net.calls.clear()
    ask(c)
    assert "groq" not in [x[0] for x in net.calls]
    assert any(s["name"] == "groq" and s["disabled"] for s in llm.status())


def test_cooldown_expiry_returns_to_groq(env, setup):
    clock, mp = setup
    keys(mp)
    net = Net(clock, {"groq": ["429", "ok"]})
    llm.set_transport(net)
    c = mkctx(clock)
    ask(c)
    clock.t += 60
    net.calls.clear()
    ask(c)
    assert net.calls[0][0] == "groq"


def test_bad_json_twice_moves_tier(env, setup):
    clock, mp = setup
    keys(mp)
    net = Net(clock, {"groq": ["bad", "bad", "ok"]})
    llm.set_transport(net)
    ask(mkctx(clock))
    assert [c[0] for c in net.calls] == ["groq", "groq", "nvidia"]


def test_all_fail_is_model_error_and_repeat(env, setup):
    clock, mp = setup
    keys(mp)
    net = Net(clock, {"groq": ["500"], "nvidia": ["500"], "local": ["500"]})
    llm.set_transport(net)
    with pytest.raises(llm.ModelError):
        ask(mkctx(clock))


def test_max_attempts_per_call(env, setup):
    clock, mp = setup
    keys(mp)
    net = Net(clock, {"groq": ["bad"], "nvidia": ["bad"], "local": ["bad"]})
    llm.set_transport(net)
    with pytest.raises(llm.ModelError):
        ask(mkctx(clock))
    assert len(net.calls) <= 4


def test_budget_bounds_hanging_tiers(env, setup):
    clock, mp = setup
    keys(mp)
    net = Net(clock, {"groq": ["hang"], "nvidia": ["hang"], "local": ["hang"]})
    llm.set_transport(net)
    c = mkctx(clock, budget=30)
    start = clock.t
    with pytest.raises(llm.ModelError):
        ask(c)
    assert clock.t - start <= 30 + 1


def test_no_key_in_logs_events_or_errors(env, setup):
    clock, mp = setup
    keys(mp)
    events = []
    net = Net(clock, {"groq": ["401"], "nvidia": ["500"], "local": ["500"]})
    llm.set_transport(net)
    with pytest.raises(llm.ModelError) as ei:
        ask(mkctx(clock), on_progress=events.append)
    blob = open(env / "decision_log.json").read() + json.dumps(events) + str(ei.value) + json.dumps(llm.status())
    assert "gsk_" not in blob and "nvapi-" not in blob
    assert [e["status"] for e in events][0] == "trying"


def test_sticky_tier_restarts_task(env, setup):
    clock, mp = setup
    keys(mp)
    net = Net(clock, {"groq": ["ok", "429"], "nvidia": ["ok"]})
    llm.set_transport(net)
    c = mkctx(clock)
    seen = []

    def task(tid):
        a = ask(c, task_id=tid)
        b = ask(c, task_id=tid)
        seen.append((a, b))
        return a

    llm.run_task(c, "T1", task)
    tiers = [x[0] for x in net.calls]
    assert tiers == ["groq", "groq", "nvidia", "nvidia"]          # restarted from its first call on NVIDIA
    logd = json.load(open(env / "decision_log.json"))
    assert any(e["action"] == "task_restart" for e in logd)


def test_budget_error_becomes_repeat_in_orchestrator(env, setup, fake_sources):
    clock, mp = setup
    net = Net(clock, {"local": ["hang"]})
    llm.set_transport(net)
    import json as _j
    from conftest import load_brief
    b, _ = load_brief("r")
    mp.setenv("WORKFLOW_TIME_BUDGET_S", "10")
    ctx = orchestrator.new_run(b, "t")
    p = orchestrator.run_until_gate(ctx, clock=clock)
    assert p["kind"] == "error" and p["outcome"] == "repeat"
    assert "nothing decided" in p["verdict"]
    assert not any(e.get("outcome") == "stop" for e in _j.load(open(env / "decision_log.json")))


def test_no_gpt_model_allowed(env, monkeypatch):
    monkeypatch.setenv("GROQ_MODEL", "openai/gpt-oss-20b")
    with pytest.raises(RuntimeError):
        llm.tiers()
