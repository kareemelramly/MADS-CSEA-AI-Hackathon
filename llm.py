"""One model client for every agent (SRS 4.2, runbook section 2a).

Tiers, in LLM_ORDER (default nvidia,local):
  1 nvidia  NVIDIA Build free tier, OpenAI-compatible, NVIDIA_MODEL (google/gemma-4-31b-it)
  2 local   llama.cpp `llama-server` (OpenAI-compatible) serving Gemma 4 26B A4B Q4_K_M

Switching rules (MOD-4): a tier without a key is skipped silently; the remote tier out of quota
(rate-limit headers or HTTP 429), lagging (no answer within LLM_REMOTE_TIMEOUT_S), returning 5xx
or 401/403 -> local tier at once; invalid output -> one retry on
the same tier, then next tier; at most LLM_MAX_ATTEMPTS_PER_CALL attempts; no attempt starts with
less than LLM_MIN_ATTEMPT_S left in the segment or run budget. All calls of one task stay on one
tier (MOD-5); a mid-task switch raises TierSwitched and `run_task` restarts the task.
No key or auth header ever reaches a log, progress event or exception (LOG-4).
"""
import json
import os
import re
import socket
import time
import urllib.error
import urllib.request
import uuid

import config
import validate as V

GPT_RE = re.compile(r"gpt", re.I)


class ModelError(Exception):
    """All tiers failed or the budget ran out. The orchestrator turns this into `repeat`."""

    def __init__(self, reasons, kind="model_error"):
        self.reasons = reasons
        self.kind = kind
        super().__init__("; ".join(reasons) or kind)


class TierSwitched(Exception):
    """The tier pinned to a task failed mid-task; the task restarts on a new tier."""


# ------------------------------------------------------------------ tiers
def tiers():
    out = []
    for name in config.llm_order():
        if name == "nvidia":
            out.append(dict(name="nvidia", n=1, provider="nvidia", local=False,
                            base=config.get("NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1"),
                            model=config.get("NVIDIA_MODEL", "google/gemma-4-31b-it"),
                            key=config.get("NVIDIA_API_KEY", ""),
                            extra=_json_env("NVIDIA_EXTRA_BODY", '{"chat_template_kwargs": {"enable_thinking": false}}')))
        elif name in ("local", "ollama", "llamacpp"):
            out.append(dict(name="local", n=2, provider="llamacpp", local=True,
                            base=config.get("LOCAL_BASE_URL", "http://127.0.0.1:8080/v1"),
                            model=config.get("LOCAL_MODEL", "gemma-4-26b-a4b-it-q4_k_m"),
                            key="local",
                            extra=_json_env("LOCAL_EXTRA_BODY", '{"chat_template_kwargs": {"enable_thinking": false}}')))
    for t in out:
        if GPT_RE.search(t["model"]):
            raise RuntimeError(f"GPT-family models are not allowed on any tier (MOD-3): {t['name']}")
    return out


def _json_env(name, default):
    try:
        return json.loads(os.environ.get(name, default) or "{}")
    except ValueError:
        return {}


def model_label(t):
    return f"tier{t['n']}/{t['provider']}/{t['model']}"


# ------------------------------------------------------------------ process state
_state = {"cooldown": {}, "disabled": set(), "headers": {}, "pins": {}, "fake": None}
_clock = time.monotonic


def reset_state():
    _state.update(cooldown={}, disabled=set(), headers={}, pins={})


def set_fake(fn):
    """Tests only: route every call to `fn(system, user, schema, agent, action)`."""
    _state["fake"] = fn


def set_clock(fn):
    global _clock
    _clock = fn


def _http_post(url, headers, body, timeout):
    req = urllib.request.Request(url, data=json.dumps(body).encode(), headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, {k.lower(): v for k, v in r.headers.items()}, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, {k.lower(): v for k, v in (e.headers or {}).items()}, e.read().decode("utf-8", "replace")


_transport = _http_post


def set_transport(fn):
    global _transport
    _transport = fn


# ------------------------------------------------------------------ status
def _cooling(name):
    return _state["cooldown"].get(name, 0) > _clock()


def available(t):
    return bool(t["key"]) and t["name"] not in _state["disabled"] and not _cooling(t["name"])


def status():
    out = []
    for t in tiers():
        h = _state["headers"].get(t["name"], {})
        out.append({"tier": t["n"], "name": t["name"], "model": t["model"], "has_key": bool(t["key"]),
                    "disabled": t["name"] in _state["disabled"],
                    "cooldown_s": max(0, round(_state["cooldown"].get(t["name"], 0) - _clock(), 1)),
                    "remaining_tokens": h.get("x-ratelimit-remaining-tokens"),
                    "remaining_requests": h.get("x-ratelimit-remaining-requests")})
    return out


def probe_remote(timeout=4):
    """Once per segment: a cheap GET /models on each remote tier. A tier that does not answer is
    cooled down (or disabled on 401/403) before any agent call, so a failing provider costs seconds,
    not one timeout per call."""
    out = {}
    for t in tiers():
        if t["local"] or not available(t):
            continue
        req = urllib.request.Request(t["base"].rstrip("/") + "/models", headers={"Authorization": "Bearer " + t["key"]})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                out[t["name"]] = "ok" if r.status == 200 else f"HTTP {r.status}"
        except urllib.error.HTTPError as e:
            out[t["name"]] = f"HTTP {e.code}"
            if e.code in (401, 403):
                _state["disabled"].add(t["name"])
            else:
                _cool(t["name"], config.cooldown_default())
        except Exception as e:  # noqa: BLE001
            out[t["name"]] = type(e).__name__
            _cool(t["name"], config.cooldown_default())
    return out


def has_remote_key():
    return any(t["key"] and not t["local"] for t in tiers())


def local_ready(timeout=2):
    """('ready' | 'loading' | 'unreachable', detail) from llama-server's /health."""
    base = config.get("LOCAL_BASE_URL", "http://127.0.0.1:8080/v1")
    url = re.sub(r"/v1/?$", "", base) + "/health"
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            return ("ready", "ok") if r.status == 200 else ("loading", str(r.status))
    except urllib.error.HTTPError as e:
        return ("loading", f"HTTP {e.code}")
    except Exception as e:  # noqa: BLE001
        return ("unreachable", type(e).__name__)


# ------------------------------------------------------------------ helpers
def _cool(name, seconds):
    _state["cooldown"][name] = _clock() + max(0.0, float(seconds))


def _parse_reset(v):
    """Rate-limit reset headers look like '7.66s', '2m59.56s', '1h2m3s'."""
    if not v:
        return None
    try:
        return float(v)
    except ValueError:
        pass
    total, ok = 0.0, False
    for num, unit in re.findall(r"([\d.]+)(ms|h|m|s)", v):
        ok = True
        total += float(num) * {"h": 3600, "m": 60, "s": 1, "ms": 0.001}[unit]
    return total if ok else None


def _extract_json(text):
    text = re.sub(r"<think>.*?</think>", "", text or "", flags=re.S).strip()
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip())
    try:
        return json.loads(text)
    except ValueError:
        a, b = text.find("{"), text.rfind("}")
        if a >= 0 and b > a:
            return json.loads(text[a:b + 1])
        raise


def _body(t, system, user, schema, max_tokens, with_extra=True, plain_json=False):
    sys_msg = (system + "\n\nReturn only one JSON object that matches this JSON schema. "
               "No prose, no code fences.\nSCHEMA:\n" + json.dumps(schema))
    body = {"model": t["model"], "messages": [{"role": "system", "content": sys_msg},
                                              {"role": "user", "content": user}],
            "temperature": 0.2, "max_tokens": max_tokens, "stream": False}
    if t["local"] and not plain_json:
        body["response_format"] = {"type": "json_schema", "json_schema": {"name": "output", "schema": schema}}
    elif not plain_json:
        body["response_format"] = {"type": "json_object"}
    if with_extra:
        body.update(t.get("extra") or {})
    return body


def _emit(on_progress, **ev):
    if on_progress:
        try:
            on_progress(ev)
        except Exception:  # noqa: BLE001 - progress display must never break a call
            pass


# ------------------------------------------------------------------ main entry
def ask(system, user, schema, agent, action, *, ctx, sources=(), task_id=None,
        on_progress=None, max_tokens=None, call_no=None):
    """Return a validated dict or raise ModelError / TierSwitched."""
    registry_ids = list(ctx.sources.keys())
    urls = [ctx.sources[s]["url"] for s in sources if s in ctx.sources] if sources else []
    max_tokens = max_tokens or config.max_tokens()
    t_start = _clock()

    if _state["fake"] is not None:
        obj = _state["fake"](system, user, schema, agent, action)
        if isinstance(obj, Exception):
            raise obj
        try:
            V.validate_output(obj, schema, registry_ids)
        except V.BadModelOutput as e:
            raise ModelError([f"fake: bad output ({e.message})"])
        ctx.log(agent, action, sources=urls, model="fake/test/fake-llm", cost=0, task_id=task_id,
                prompt_tokens=0, completion_tokens=0, attempts=1, wall_s=0)
        return obj

    task_id = task_id or f"{agent}:{action}:{uuid.uuid4().hex[:6]}"
    pin_key = (ctx.run_id, task_id)
    pinned = _state["pins"].get(pin_key)
    all_tiers = tiers()
    if pinned:
        cand = [t for t in all_tiers if t["name"] == pinned]
        if not cand or not available(cand[0]):
            _state["pins"].pop(pin_key, None)
            raise TierSwitched(f"pinned tier {pinned} unavailable")
    else:
        cand = [t for t in all_tiers if available(t)]

    attempts, reasons, first_tier, jump_local = 0, [], None, False
    for t in cand:
        if jump_local and not t["local"]:
            reasons.append(f"{t['name']}: skipped after remote lag/failure")
            continue
        if not available(t):
            continue
        first_tier = first_tier or t["name"]
        generated = 0
        with_extra = True
        plain_json = False
        while generated < 2:
            if attempts >= config.max_attempts():
                break
            left = ctx.time_left(_clock)
            if left < config.min_attempt_s():
                _emit(on_progress, call=call_no, agent=agent, task=task_id, tier=t["name"], status="failed",
                      reason="budget", elapsed_s=round(_clock() - t_start, 1), budget_left_s=round(left, 1))
                reasons.append("time budget used")
                _fail_log(ctx, agent, action, reasons, attempts)
                raise ModelError(reasons, kind="budget")
            # Pre-emptive quota check (MOD-4): skip without spending an attempt.
            h = _state["headers"].get(t["name"], {})
            est = (len(system) + len(user) + len(json.dumps(schema))) / 4 + max_tokens
            rem_tok = h.get("x-ratelimit-remaining-tokens")
            if not t["local"] and rem_tok is not None and _num(rem_tok) < est:
                _cool(t["name"], _parse_reset(h.get("x-ratelimit-reset-tokens")) or config.cooldown_default())
                reasons.append(f"{t['name']}: tokens_low ({rem_tok} < {int(est)})")
                _emit(on_progress, call=call_no, agent=agent, task=task_id, tier=t["name"], status="fallback",
                      reason="tokens_low", elapsed_s=round(_clock() - t_start, 1), budget_left_s=round(left, 1))
                break
            timeout = min(config.local_timeout() if t["local"] else config.remote_timeout(), left)
            attempts += 1
            _emit(on_progress, call=call_no, agent=agent, task=task_id, tier=t["name"], status="trying",
                  reason=None, elapsed_s=round(_clock() - t_start, 1), budget_left_s=round(left, 1))
            headers = {"Content-Type": "application/json"}
            if not t["local"]:
                headers["Authorization"] = "Bearer " + t["key"]
            url = t["base"].rstrip("/") + "/chat/completions"
            try:
                status_code, rh, text = _transport(url, headers, _body(t, system, user, schema, max_tokens, with_extra, plain_json), timeout)
            except (socket.timeout, TimeoutError) as e:  # noqa: F841
                _cool(t["name"], config.timeout_cooldown())
                reasons.append(f"{t['name']}: timeout after {timeout:.0f} s")
                _emit(on_progress, call=call_no, agent=agent, task=task_id, tier=t["name"], status="fallback",
                      reason="timeout", elapsed_s=round(_clock() - t_start, 1), budget_left_s=round(ctx.time_left(_clock), 1))
                jump_local = not t["local"]
                break
            except urllib.error.URLError as e:
                if isinstance(getattr(e, "reason", None), (socket.timeout, TimeoutError)):
                    reasons.append(f"{t['name']}: timeout after {timeout:.0f} s")
                    _cool(t["name"], config.timeout_cooldown())
                else:
                    reasons.append(f"{t['name']}: unreachable")
                    _cool(t["name"], config.cooldown_default())
                jump_local = not t["local"]
                break
            except OSError:
                reasons.append(f"{t['name']}: connection error")
                _cool(t["name"], config.cooldown_default())
                jump_local = not t["local"]
                break
            if rh:
                keep = {k: v for k, v in rh.items() if k.startswith("x-ratelimit") or k == "retry-after"}
                if keep:
                    _state["headers"][t["name"]] = keep
            if status_code == 429:
                ra = _parse_reset(rh.get("retry-after")) if rh else None
                _cool(t["name"], ra or config.cooldown_default())
                reasons.append(f"{t['name']}: 429, cooling {int(ra or config.cooldown_default())} s")
                _emit(on_progress, call=call_no, agent=agent, task=task_id, tier=t["name"], status="fallback",
                      reason="429", elapsed_s=round(_clock() - t_start, 1), budget_left_s=round(ctx.time_left(_clock), 1))
                break
            if status_code in (401, 403):
                _state["disabled"].add(t["name"])
                reasons.append(f"{t['name']}: auth {status_code}, tier disabled")
                _emit(on_progress, call=call_no, agent=agent, task=task_id, tier=t["name"], status="fallback",
                      reason="auth", elapsed_s=round(_clock() - t_start, 1), budget_left_s=round(ctx.time_left(_clock), 1))
                jump_local = not t["local"]
                break
            if status_code == 400 and with_extra and t.get("extra"):
                with_extra = False      # provider rejected an optional parameter; retry plain once
                attempts -= 1
                continue
            if status_code == 400 and not plain_json:
                plain_json = True       # server rejected the response format; retry once with the schema in the prompt only
                attempts -= 1
                continue
            if status_code == 400 and not t["local"]:
                _state["disabled"].add(t["name"])   # the provider does not accept our request shape: stop asking it
                reasons.append(f"{t['name']}: HTTP 400 (request not accepted), tier disabled")
                jump_local = True
                break
            if status_code >= 500 or status_code != 200:
                _cool(t["name"], config.cooldown_default())
                reasons.append(f"{t['name']}: HTTP {status_code}")
                _emit(on_progress, call=call_no, agent=agent, task=task_id, tier=t["name"], status="fallback",
                      reason=f"http_{status_code}", elapsed_s=round(_clock() - t_start, 1), budget_left_s=round(ctx.time_left(_clock), 1))
                jump_local = not t["local"]
                break
            try:
                data = json.loads(text)
                content = data["choices"][0]["message"].get("content") or ""
                obj = _extract_json(content)
                V.validate_output(obj, schema, registry_ids)
            except (ValueError, KeyError, IndexError, TypeError, V.BadModelOutput) as e:
                generated += 1
                msg = e.message if isinstance(e, V.BadModelOutput) else "not valid JSON"
                reasons.append(f"{t['name']}: bad output ({msg[:80]})")
                _emit(on_progress, call=call_no, agent=agent, task=task_id, tier=t["name"], status="fallback" if generated >= 2 else "trying",
                      reason="bad_json", elapsed_s=round(_clock() - t_start, 1), budget_left_s=round(ctx.time_left(_clock), 1))
                if generated == 1:
                    user = user + f"\n\nYour previous answer was rejected: {msg[:160]}. Return valid JSON only."
                continue
            usage = data.get("usage") or {}
            _state["pins"][pin_key] = t["name"]
            wall = round(_clock() - t_start, 2)
            _emit(on_progress, call=call_no, agent=agent, task=task_id, tier=t["name"], status="ok",
                  reason=None, elapsed_s=wall, budget_left_s=round(ctx.time_left(_clock), 1))
            extra = {}
            if first_tier and first_tier != t["name"]:
                extra = {"fallback_from": first_tier, "fallback_reason": _reason_code(reasons)}
            ctx.log(agent, action, sources=urls, model=model_label(t), cost=0, task_id=task_id,
                    tier=t["n"], prompt_tokens=usage.get("prompt_tokens"),
                    completion_tokens=usage.get("completion_tokens"), attempts=attempts, wall_s=wall, **extra)
            return obj
        if pinned:
            _state["pins"].pop(pin_key, None)
            raise TierSwitched("; ".join(reasons))
    if not reasons:
        reasons.append("no model tier available (no key, disabled or cooling down)")
    _fail_log(ctx, agent, action, reasons, attempts)
    raise ModelError(reasons)


def _num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return 1e12


def _reason_code(reasons):
    joined = " ".join(reasons)
    for code in ("tokens_low", "429", "timeout", "auth", "bad output", "HTTP", "unreachable"):
        if code in joined:
            return {"bad output": "bad_json", "HTTP": "http_error"}.get(code, code)
    return "other"


def _fail_log(ctx, agent, action, reasons, attempts):
    ctx.log(agent, "model_error", sources=[], model=None, cost=0, failed_action=action,
            reasons=reasons[-6:], attempts=attempts)


def run_task(ctx, task_id, fn, restarts=2):
    """Run a multi-call task on one tier; if its tier fails mid-task, restart it on the next."""
    for i in range(restarts + 1):
        try:
            return fn(task_id)
        except TierSwitched:
            ctx.log("llm", "task_restart", task_id=task_id, restart=i + 1)
            if i == restarts:
                raise ModelError([f"task {task_id} could not finish on one tier"])
