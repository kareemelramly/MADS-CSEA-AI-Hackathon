"""Check the optional remote tiers with your .env keys (never prints a key, writes nothing to the
committed log). For NVIDIA Build it lists the served models, confirms the configured model
exists (picking the closest open-weight Gemma model if not, and updating .env), and makes one tiny
JSON call.        python scripts/check_keys.py
"""
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENV = os.path.join(ROOT, ".env")
PROVIDERS = {
    "nvidia": {"key": "NVIDIA_API_KEY", "base": "NVIDIA_BASE_URL", "model": "NVIDIA_MODEL", "base_default": "https://integrate.api.nvidia.com/v1",
               "prefer": ["google/gemma-4-31b-it", "google/gemma-3-12b-it"],
               "extra": {"chat_template_kwargs": {"enable_thinking": False}}},
}


def read_env():
    env = {}
    if os.path.exists(ENV):
        for line in open(ENV, encoding="utf-8"):
            if "=" in line and not line.lstrip().startswith("#"):
                k, v = line.rstrip("\n").split("=", 1)
                env[k.strip()] = v.strip()
    return env


def set_env(key, value):
    lines = open(ENV, encoding="utf-8").read().splitlines()
    for i, l in enumerate(lines):
        if l.startswith(key + "="):
            lines[i] = f"{key}={value}"
            break
    else:
        lines.append(f"{key}={value}")
    open(ENV, "w", encoding="utf-8").write("\n".join(lines) + "\n")


def req(url, key, body=None, timeout=25):
    r = urllib.request.Request(url, data=json.dumps(body).encode() if body else None,
                               headers={"Authorization": "Bearer " + key, "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(r, timeout=timeout) as resp:
            return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return e.code, {"error": e.read().decode("utf-8", "replace")[:200]}
    except Exception as e:  # noqa: BLE001
        return 0, {"error": type(e).__name__}


def main():
    env = read_env()
    ok_any = False
    for name, p in PROVIDERS.items():
        key = env.get(p["key"]) or os.environ.get(p["key"], "")
        print(f"\n[{name}]")
        if not key:
            print("  no key in .env: tier skipped (that is fine; the local model still works)")
            continue
        base = env.get(p["base"]) or p["base_default"]
        st, data = req(base.rstrip("/") + "/models", key)
        if st != 200:
            print(f"  provider refused the key (HTTP {st}). This tier is skipped; runs continue on the other tiers."
                  )
            continue
        ids = [m["id"] for m in data.get("data", []) if not re.search("gpt", m["id"], re.I)]
        want = env.get(p["model"]) or p["prefer"][0]
        model = want if want in ids else next((m for m in p["prefer"] if m in ids), None) or next((m for m in ids if "gemma" in m.lower()), None)
        if not model:
            print(f"  no suitable open-weight model served; available: {ids[:8]}")
            continue
        if model != want:
            print(f"  '{want}' is not served here; using '{model}' instead (written to .env)")
            set_env(p["model"], model)
        else:
            print(f"  model '{model}' is served")
        body = {"model": model, "messages": [{"role": "user", "content": 'Return {"ok": true} as JSON only.'}],
                "max_tokens": 50, "temperature": 0, "response_format": {"type": "json_object"}, **p["extra"]}
        t = time.time()
        st, out = req(base.rstrip("/") + "/chat/completions", key, body)
        if st == 400:
            body = {k: v for k, v in body.items() if k not in p["extra"]}
            st, out = req(base.rstrip("/") + "/chat/completions", key, body)
        if st == 200:
            ok_any = True
            print(f"  test call OK in {time.time() - t:.1f} s: {out['choices'][0]['message']['content'][:60]!r}")
        else:
            print(f"  test call failed: HTTP {st} {str(out.get('error'))[:120]}")
    print("\nResult:", "at least one remote tier works" if ok_any else "no remote tier works; runs use the local model only")
    return 0


if __name__ == "__main__":
    sys.exit(main())
