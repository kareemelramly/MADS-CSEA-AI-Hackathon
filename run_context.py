"""RunContext: everything one run carries (runbook Step 2, SRS CORE-6, CORE-7, X16).

Output files are write-once: `ctx.out()` opens with mode "x", so an existing file is never
overwritten. A retry of the same step writes the next attempt number (`-a2`), and the earlier
artifact is marked `superseded` in `ctx.artifacts`.
"""
import csv
import hashlib
import io
import json
import os
import re
import time
from dataclasses import fields, dataclass, field, asdict
from datetime import datetime, timezone

import config
import log as logmod

OVERRIDE_BANNER = "UNVALIDATED · FOUNDER OVERRIDE"
NAME_RE = re.compile(r"^phase[1-6]_(step\d+|gate)_[a-z0-9_]+$")


def sha256_bytes(b):
    return hashlib.sha256(b).hexdigest()


def new_run_id(label):
    label = re.sub(r"[^a-z0-9]", "", (label or "x").lower())[:8] or "x"
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + label


@dataclass
class RunContext:
    brief: dict
    label: str = "x"
    run_id: str = ""
    stage: str = "p1"
    handoffs: dict = field(default_factory=dict)
    validation_status: str = "NOT_STARTED"
    overrides: list = field(default_factory=list)
    artifacts: list = field(default_factory=list)
    sources: dict = field(default_factory=dict)          # source registry: id -> record
    gates: list = field(default_factory=list)
    data: dict = field(default_factory=dict)             # phase working data
    founder: dict = field(default_factory=dict)          # founder inputs waiting to be consumed
    system_time_s: float = 0.0
    phase_time_s: dict = field(default_factory=dict)
    model_errors: dict = field(default_factory=dict)
    finished: bool = False
    final_outcome: str = ""
    deadline: float = 0.0                                # monotonic; segment budget
    run_deadline: float = 0.0                            # monotonic; whole-run budget (0 = off)

    def __post_init__(self):
        if not self.run_id:
            self.run_id = new_run_id(self.label)
        self.label = re.sub(r"[^a-z0-9]", "", (self.label or "x").lower())[:8] or "x"

    # ---------- time ----------
    def start_segment(self, clock=time.monotonic):
        now = clock()
        self._seg_start = now
        self.deadline = now + config.workflow_budget()
        rb = config.run_budget()
        if rb > 0:
            self.run_deadline = now + max(0.0, rb - self.system_time_s)
        else:
            self.run_deadline = 0.0

    def end_segment(self, clock=time.monotonic):
        start = getattr(self, "_seg_start", None)
        if start is not None:
            spent = clock() - start
            self.system_time_s += spent
            ph = self.stage[:2]
            self.phase_time_s[ph] = round(self.phase_time_s.get(ph, 0) + spent, 2)
            self._seg_start = None

    def time_left(self, clock=time.monotonic):
        now = clock()
        left = self.deadline - now if self.deadline else 1e9
        if self.run_deadline:
            left = min(left, self.run_deadline - now)
        return left

    # ---------- override ----------
    @property
    def overridden(self):
        return bool(self.overrides)

    def stamp(self, text):
        if self.overridden and not text.startswith(OVERRIDE_BANNER):
            return OVERRIDE_BANNER + "\n\n" + text
        return text

    # ---------- logging ----------
    def log(self, agent, action, sources=None, model=None, cost=0, approved_by=None, **extra):
        if self.overridden:
            extra.setdefault("override", True)
        return logmod.log(agent, action, sources=sources, model=model, cost=cost,
                          approved_by=approved_by, run_id=self.run_id, **extra)

    # ---------- outputs ----------
    def out(self, name, ext, content, phase=None, step=None, status_label=None):
        """Write one write-once output file and register it. Returns the artifact record."""
        if not NAME_RE.match(name):
            raise ValueError(f"bad output name {name!r}")
        if ext not in ("md", "json", "csv", "txt", "html"):
            raise ValueError("outputs are text formats only")
        if isinstance(content, (dict, list)):
            if self.overridden and isinstance(content, dict):
                content = {"banner": OVERRIDE_BANNER, **content}
            body = json.dumps(content, indent=2, ensure_ascii=False) + "\n"
        elif ext == "csv" and isinstance(content, list):
            body = content
        else:
            body = content if ext in ("json", "csv") or (ext == "html" and OVERRIDE_BANNER in content) else self.stamp(content)
            if ext == "csv" and self.overridden:
                body = _csv_banner(body)
        odir = config.outputs_dir()
        attempt = 1
        while True:
            path = os.path.join(odir, f"{name}_{self.label}_a{attempt}.{ext}")
            try:
                with open(path, "x", encoding="utf-8", newline="") as f:
                    f.write(body)
                break
            except FileExistsError:
                attempt += 1
        digest = sha256_bytes(body.encode("utf-8"))
        for a in self.artifacts:
            if a["name"] == name and a["ext"] == ext and a["status"] == "final":
                a["status"] = "superseded"
        m = re.match(r"phase(\d)_(step(\d+)|gate)", name)
        rec = {
            "name": name, "ext": ext, "path": os.path.relpath(path, os.path.dirname(odir)),
            "sha256": digest, "phase": int(m.group(1)) if m else phase,
            "step": (int(m.group(3)) if m and m.group(3) else "gate") if m else step,
            "attempt": attempt, "status": "final", "label": status_label,
        }
        self.artifacts.append(rec)
        self.log("orchestrator", "write_output", path=rec["path"], sha256=digest, attempt=attempt)
        return rec

    def final(self, name, ext=None):
        for a in reversed(self.artifacts):
            if a["name"] == name and a["status"] == "final" and (ext is None or a["ext"] == ext):
                return a
        return None

    def ref(self, name, ext=None):
        a = self.final(name, ext)
        return {"path": a["path"], "sha256": a["sha256"]} if a else None

    # ---------- persistence ----------
    def to_json(self):
        d = asdict(self)
        return json.dumps(d, ensure_ascii=False)

    @classmethod
    def from_json(cls, s):
        d = json.loads(s)
        known = {f.name for f in fields(cls)}
        return cls(**{k: v for k, v in d.items() if k in known})

    def save(self):
        d = os.path.join(config.state_dir(), "runs")
        os.makedirs(d, exist_ok=True)
        tmp = os.path.join(d, self.run_id + ".json.tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            f.write(self.to_json())
        os.replace(tmp, os.path.join(d, self.run_id + ".json"))


def _csv_banner(body):
    rows = list(csv.reader(io.StringIO(body)))
    width = max((len(r) for r in rows), default=1)
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow([OVERRIDE_BANNER] + [""] * (width - 1))
    w.writerows(rows)
    return buf.getvalue()
