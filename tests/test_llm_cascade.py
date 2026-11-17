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
        tier = "nvidia" if "nvidia" in url else "local"
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
        if step == "400":
            return 400, {}, ""
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


def keys(mp, nvidia=True):
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
    assert models(env)[0].startswith("tier2/llamacpp/")


def test_remote_429_goes_to_local_at_once(env, setup):
    clock, mp = setup
    keys(mp)
    net = Net(clock, {"nvidia": ["429"]})
    llm.set_transport(net)
    ask(mkctx(clock))
    assert [c[0] for c in net.calls] == ["nvidia", "local"]
    e = json.load(open(env / "decision_log.json"))[-1]
    assert e["fallback_from"] == "nvidia" and e["fallback_reason"] == "429"


def test_tokens_low_skips_remote_next_call(env, setup):
    clock, mp = setup
    keys(mp)
    net = Net(clock, {"nvidia": ["lowtok"]})
    llm.set_transport(net)
    c = mkctx(clock)
    ask(c)
    net.calls.clear()
    ask(c)
    assert [x[0] for x in net.calls] == ["local"]


def test_remote_lag_moves_to_local(env, setup):
    clock, mp = setup
    keys(mp)
    net = Net(clock, {"nvidia": ["hang"]})
    llm.set_transport(net)
    ask(mkctx(clock))
    assert [c[0] for c in net.calls] == ["nvidia", "local"]
    assert net.calls[0][1] <= 20


def test_401_disables_tier(env, setup):
    clock, mp = setup
    keys(mp)
    net = Net(clock, {"nvidia": ["401"]})
    llm.set_transport(net)
    c = mkctx(clock)
    ask(c)
    net.calls.clear()
    ask(c)
    assert "nvidia" not in [x[0] for x in net.calls]
    assert any(s["name"] == "nvidia" and s["disabled"] for s in llm.status())


def test_cooldown_expiry_returns_to_remote(env, setup):
    clock, mp = setup
    keys(mp)
    net = Net(clock, {"nvidia": ["429", "ok"]})
    llm.set_transport(net)
    c = mkctx(clock)
    ask(c)
    clock.t += 60
    net.calls.clear()
    ask(c)
    assert net.calls[0][0] == "nvidia"


def test_bad_json_twice_moves_tier(env, setup):
    clock, mp = setup
    keys(mp)
    net = Net(clock, {"nvidia": ["bad", "bad", "ok"]})
    llm.set_transport(net)
    ask(mkctx(clock))
    assert [c[0] for c in net.calls] == ["nvidia", "nvidia", "local"]


def test_all_fail_is_model_error_and_repeat(env, setup):
    clock, mp = setup
    keys(mp)
    net = Net(clock, {"nvidia": ["500"], "local": ["500"]})
    llm.set_transport(net)
    with pytest.raises(llm.ModelError):
        ask(mkctx(clock))


def test_max_attempts_per_call(env, setup):
    clock, mp = setup
    keys(mp)
    net = Net(clock, {"nvidia": ["bad"], "local": ["bad"]})
    llm.set_transport(net)
    with pytest.raises(llm.ModelError):
        ask(mkctx(clock))
    assert len(net.calls) <= 4


def test_budget_bounds_hanging_tiers(env, setup):
    clock, mp = setup
    keys(mp)
    net = Net(clock, {"nvidia": ["hang"], "local": ["hang"]})
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
    net = Net(clock, {"nvidia": ["401"], "local": ["500"]})
    llm.set_transport(net)
    with pytest.raises(llm.ModelError) as ei:
        ask(mkctx(clock), on_progress=events.append)
    blob = open(env / "decision_log.json").read() + json.dumps(events) + str(ei.value) + json.dumps(llm.status())
    assert "nvapi-" not in blob
    assert [e["status"] for e in events][0] == "trying"


def test_sticky_tier_restarts_task(env, setup):
    clock, mp = setup
    keys(mp)
    net = Net(clock, {"nvidia": ["ok", "429"], "local": ["ok"]})
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
    assert tiers == ["nvidia", "nvidia", "local", "local"]          # restarted from its first call on the local tier
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
    monkeypatch.setenv("NVIDIA_MODEL", "openai/gpt-oss-20b")
    with pytest.raises(RuntimeError):
        llm.tiers()


def test_remote_rejecting_request_shape_is_disabled_and_local_answers(env, setup):
    clock, mp = setup
    keys(mp)
    net = Net(clock, {"nvidia": ["400"]})
    llm.set_transport(net)
    c = mkctx(clock)
    assert ask(c) == {"answer": "ok"}
    assert [x[0] for x in net.calls][-1] == "local"
    net.calls.clear()
    ask(c)
    assert [x[0] for x in net.calls] == ["local"]          # never asked again in this session
