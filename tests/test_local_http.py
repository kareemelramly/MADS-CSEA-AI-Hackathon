"""Local tier over real HTTP: a tiny fake llama-server on 127.0.0.1 (no internet) answers
/health and /v1/chat/completions with schema-valid JSON, so the real `urllib` path, the
`response_format: json_schema` request and the token logging are exercised end to end."""
import json
import re
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

import llm
import orchestrator
from conftest import TestFounder, drive, gen, load_brief

SEEN = []


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_GET(self):
        if self.path == "/health":
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'{"status":"ok"}')
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        SEEN.append(body)
        schema = body["response_format"]["json_schema"]["schema"]
        user = body["messages"][-1]["content"]
        ids = re.findall(r"\[(S\d{3})\]", user)
        if "screen" in body["messages"][0]["content"].split("TASK:")[-1][:20]:
            out = {"items": [{"source_id": i, "relevant": True, "pain_point": "Planner loses track of vendor deadlines"} for i in ids[:5]]}
        else:
            out = gen(schema, ids)
        resp = {"choices": [{"message": {"role": "assistant", "content": json.dumps(out)}}],
                "usage": {"prompt_tokens": len(json.dumps(body)) // 4, "completion_tokens": len(json.dumps(out)) // 4}}
        data = json.dumps(resp).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


@pytest.fixture
def server(monkeypatch):
    srv = HTTPServer(("127.0.0.1", 0), H)
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    monkeypatch.setenv("LOCAL_BASE_URL", f"http://127.0.0.1:{srv.server_port}/v1")
    llm.set_transport(llm._http_post)
    SEEN.clear()
    yield srv
    srv.shutdown()


def test_full_run_over_local_http(env, server, fake_sources):
    assert llm.local_ready()[0] == "ready"
    b, pre = load_brief("r")
    ctx = orchestrator.new_run(b, "h")
    drive(ctx, TestFounder(pre))
    assert ctx.finished
    assert SEEN and all(s["response_format"]["type"] == "json_schema" for s in SEEN)
    assert all("Authorization" not in json.dumps(s) for s in SEEN)
    log = json.load(open(env / "decision_log.json"))
    calls = [e for e in log if (e.get("model") or "").startswith("tier2/llamacpp/")]
    assert len(calls) == len(SEEN) <= 16
    assert all(e["cost"] == 0 and e["prompt_tokens"] > 0 for e in calls)
