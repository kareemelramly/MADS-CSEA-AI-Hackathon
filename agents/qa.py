"""QA agent (Phase 3, no model call). Runs the 14 checks that apply to archetype A1:
QA-01 to QA-06 and QA-08 to QA-15. QA-07 (script integrity) is not applicable to A1, which
contains no HTML or scripts. Results are reproducible with pytest (BLD-4)."""
import csv
import io
import os
import re

import config
import guardrails

MAX_FILE, MAX_TOTAL = 100_000, 300_000
NAME_OK = re.compile(r"^phase3_(step\d+|gate)_[a-z0-9_]+_[a-z0-9]+_a\d+\.(md|csv|txt|json)$")
CLAIM_LINE = re.compile(r"(\d+\s?%|\$\s?\d|€\s?\d|£\s?\d|\b(EGP|USD)\s?\d|\bmarket (size|share)\b|\bstud(y|ies) (show|found)\b|\bsurvey\b|\bstatistic)", re.I)
OVERRIDE = "UNVALIDATED · FOUNDER OVERRIDE"


def run(ctx, plan, files):
    """files: {role: {"path": relative path, "text": content}} for checklist, tracker, license, docs."""
    odir = os.path.dirname(config.outputs_dir())
    texts = {k: v["text"] for k, v in files.items()}
    res = []

    def add(cid, name, ok, msg=""):
        res.append({"id": cid, "name": name, "status": "pass" if ok else "fail", "evidence": msg})

    missing = [k for k, v in files.items() if not os.path.exists(os.path.join(odir, v["path"])) or not v["text"].strip()]
    add("QA-01", "Manifest complete", not missing, f"missing or empty: {missing}" if missing else f"{len(files)} files")
    big = [k for k, t in texts.items() if len(t.encode()) > MAX_FILE]
    total = sum(len(t.encode()) for t in texts.values())
    add("QA-02", "Size", not big and total <= MAX_TOTAL, f"total {total} bytes; too big: {big}")
    rows = list(csv.reader(io.StringIO(texts["tracker"])))
    widths = {len(r) for r in rows if r}
    body = texts["checklist"][len(OVERRIDE):] if texts["checklist"].startswith(OVERRIDE) else texts["checklist"]
    fmt_ok = len(widths) == 1 and body.strip().startswith("# ") and "## J1." in body
    add("QA-03", "Format validity", fmt_ok, f"CSV column counts {sorted(widths)}; checklist headings present: {fmt_ok}")
    j_ok, j_msg = True, []
    pos_doc = -1
    for i, step in enumerate(plan["journey"], 1):
        if f'<a id="j{i}"></a>' not in texts["checklist"]:
            j_ok = False
            j_msg.append(f"anchor j{i} missing")
        else:
            sect = texts["checklist"].split(f'<a id="j{i}"></a>', 1)[1].split("<a id=", 1)[0]
            if "- [ ]" not in sect:
                j_ok = False
                j_msg.append(f"J{i} has no checklist items")
        p = texts["docs"].find(f"#j{i})")
        if p < 0 or p < pos_doc:
            j_ok = False
            j_msg.append(f"J{i} missing or out of order in quick start")
        pos_doc = max(pos_doc, p)
    add("QA-04", "Journey trace", j_ok, "; ".join(j_msg) or f"{len(plan['journey'])} steps traced")
    bad_links = []
    for target, anchor in re.findall(r"\]\(([^)#\s]+)#([a-z0-9]+)\)", texts["docs"]):
        tpath = os.path.join(config.outputs_dir(), target)
        if not os.path.exists(tpath) or f'id="{anchor}"' not in open(tpath, encoding="utf-8").read():
            bad_links.append(f"{target}#{anchor}")
    add("QA-05", "Internal links", not bad_links, f"broken: {bad_links}" if bad_links else "all resolve")
    allowed = {r["url"] for r in ctx.sources.values()}
    ext = []
    for k, t in texts.items():
        if re.search(r"<script|<link|<img|@import|src=", t, re.I):
            ext.append(f"{k}: embedded resource")
        for u in re.findall(r"https?://[^\s)\"'>]+", t):
            if u not in allowed:
                ext.append(f"{k}: {u[:60]}")
    add("QA-06", "No external resources", not ext, "; ".join(ext[:5]) or "none")
    res.append({"id": "QA-07", "name": "Script integrity", "status": "n/a", "evidence": "A1 has no HTML or scripts"})
    ban = None
    for k in ("checklist", "tracker", "docs"):
        r = guardrails.check(texts[k])
        if r:
            ban = f"{k}: {r}"
            break
    add("QA-08", "Banned content", ban is None, ban or "none found")
    exc = guardrails.excluded(texts["checklist"] + " " + texts["docs"])
    add("QA-09", "Excluded category", exc is None, str(exc) if exc else "not excluded")
    unsourced = []
    for k in ("checklist", "docs"):
        for line in texts[k].splitlines():
            if CLAIM_LINE.search(line) and "ASSUMPTION" not in line and not any(u in line for u in allowed):
                unsourced.append(f"{k}: {line.strip()[:60]}")
    add("QA-10", "Claims sourced", not unsourced, "; ".join(unsourced[:3]) or "all numeric/market lines cited or ASSUMPTION")
    lab = "MOCKED" in texts["checklist"] and "## What is mocked" in texts["docs"] and all(m.split(":")[0] in texts["docs"] for m in plan["mocked"])
    if ctx.overridden:
        lab = lab and all(texts[k].startswith(OVERRIDE) for k in ("checklist", "docs", "license")) and texts["tracker"].startswith(OVERRIDE)
    add("QA-11", "Mocks and override labelled", lab, "override banner required" if ctx.overridden else "mocks labelled")
    pos, h_ok = -1, True
    for h in DOC_HEADINGS:
        p = texts["docs"].find(f"\n## {h}\n")
        if p < pos or p < 0:
            h_ok = False
        pos = max(pos, p)
    add("QA-12", "Docs headings", h_ok, ", ".join(DOC_HEADINGS))
    add("QA-13", "Licence", "SPDX-License-Identifier: MIT" in texts["license"], "MIT (OSI)")
    crit_ok = j_ok and not bad_links and 3 <= len(plan["acceptance_criteria"]) <= 6
    add("QA-14", "Acceptance criteria", crit_ok, f"{len(plan['acceptance_criteria'])} automated via QA-04/QA-05; MANUAL listed: {len(plan['manual_criteria'])}")
    badnames = [v["path"] for v in files.values() if not NAME_OK.match(os.path.basename(v["path"]))]
    add("QA-15", "Naming", not badnames, f"bad: {badnames}" if badnames else "all match phase3_step<M>_*")
    return res


DOC_HEADINGS = ["Overview", "Quick start", "How to use", "What is mocked", "Troubleshooting", "Limitations"]


def report_md(plan, qa, attempt):
    lines = ["# Phase 3 test report (QA agent, no model call)", "", f"Attempt {attempt}. Archetype A1: 14 applicable checks; QA-07 not applicable.", "",
             "| Check | Name | Result | Evidence |", "|---|---|---|---|"]
    for c in qa:
        lines.append(f"| {c['id']} | {c['name']} | {c['status']} | {c['evidence'].replace('|', '/')} |")
    lines += ["", "## Acceptance criteria", ""]
    for i, c in enumerate(plan["acceptance_criteria"], 1):
        lines.append(f"{i}. Given {c['given']}, when {c['when']}, then {c['then']} (automated via QA-04, QA-05)")
    lines += ["", "## MANUAL (not checked, never reported as passed)", ""] + [f"- [ ] {m}" for m in plan["manual_criteria"]]
    lines += ["", "## Known limitations", "", "- QA-08 and QA-10 are pattern-based and can miss paraphrased violations."]
    return "\n".join(lines) + "\n"
