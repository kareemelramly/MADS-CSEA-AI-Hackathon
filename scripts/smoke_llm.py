"""One real model call through the cascade; logs to a scratch file only (never the committed log).
    python scripts/smoke_llm.py"""
import json
import os
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.environ.setdefault("DECISION_LOG_PATH", os.path.join(ROOT, "scratch_decision_log.json"))
os.environ.setdefault("STATE_DIR", os.path.join(tempfile.gettempdir(), "vb_smoke_state"))
import llm  # noqa: E402
from run_context import RunContext  # noqa: E402

ctx = RunContext(brief={}, label="smoke")
ctx.start_segment()
schema = {"type": "object", "properties": {"greeting": {"type": "string"}, "confidence": {"type": "string", "enum": ["low", "medium", "high"]}},
          "required": ["greeting", "confidence"]}
print("tiers:", json.dumps(llm.status()))
print("local:", llm.local_ready())
out = llm.ask("You are a test agent.", "Say hi in five words.", schema, "smoke", "smoke_call", ctx=ctx,
              on_progress=lambda e: print("  progress:", e))
print("answer:", out)
print("log entry:", json.load(open(os.environ["DECISION_LOG_PATH"]))[-1])
