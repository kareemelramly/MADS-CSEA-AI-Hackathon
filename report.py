"""Final run report: one readable summary of a whole run, built only from the decision log and the
files the run wrote (nothing is typed by hand).

Three forms of the same content:
  * outputs/phase<N>_step9_run_report_<label>_a<k>.md    text, committed, renders on GitHub
  * outputs/phase<N>_step9_run_report_<label>_a<k>.html  styled page, opened in the app
  * <STATE_DIR>/reports/<run_id>.pdf                       printable PDF (downloaded from the app; not in git)

<N> is the highest phase the run reached. `write_for(ctx)` runs when a run ends; `python
scripts/run_report.py --all` rebuilds the reports for every run in decision_log.json.
"""
import html
import json
import os
import re

import config
import log as logmod

PHASE_NAMES = {1: "Discover", 2: "Validate", 3: "Build", 4: "Commercial setup", 5: "Launch", 6: "Operate and learn"}
OUTCOME_WORDS = {"go": "Go on", "repeat": "Repeat", "pivot_back": "Pivot back", "stop": "Stop",
                 "awaiting_evidence": "Waiting for real evidence", "persevere": "Persevere", "pivot": "Pivot"}
LABELS = ["PAYMENTS · MOCKED (local ledger, no payment of any kind)", "PUBLISHING · STUBBED (nothing is posted or sent)",
          "PERSONAS · SIMULATED (never counted as evidence)"]


# ------------------------------------------------------------------ data
def _phase_of(path):
    m = re.search(r"phase([1-6])_", os.path.basename(path or ""))
    return int(m.group(1)) if m else 0


def _read(root, rel):
    p = os.path.join(root, rel) if not os.path.isabs(rel) else rel
    if not os.path.isfile(p):
        alt = os.path.join(config.outputs_dir(), os.path.basename(rel))
        p = alt if os.path.isfile(alt) else p
    try:
        return open(p, encoding="utf-8").read()
    except OSError:
        return ""


def summarize(entries, run_id, root=None):
    """Collect everything the report shows for one run from its log entries."""
    root = root or os.path.dirname(os.path.abspath(__file__))
    E = [e for e in entries if e.get("run_id") == run_id]
    s = {"run_id": run_id, "label": run_id.rsplit("-", 1)[-1], "idea": None, "started": None, "ended": None,
         "outcome": None, "reason": None, "system_time_s": None, "gates": [], "choices": [], "overrides": [],
         "approvals": [], "stubbed": [], "ledger": [], "refusals": [], "files": [], "models": {}, "calls": 0,
         "prompt_tokens": 0, "completion_tokens": 0, "model_wall_s": 0.0, "cost": 0.0, "sources": [],
         "model_errors": 0, "max_phase": 0, "pain_points": [], "memo": "", "price": "", "store": ""}
    for e in E:
        a = e["action"]
        s["cost"] += float(e.get("cost") or 0)
        for u in e.get("sources") or []:
            if u not in s["sources"]:
                s["sources"].append(u)
        if a == "start_run":
            s["idea"], s["started"] = e.get("brief_idea"), e["timestamp"]
        elif a == "end_run":
            s["outcome"], s["reason"], s["ended"] = e.get("outcome"), e.get("reason"), e["timestamp"]
            s["system_time_s"] = e.get("system_time_s")
        elif e["agent"] == "gate":
            s["gates"].append({"gate": a, "phase": _phase_of(a + "_"), "outcome": e.get("outcome"),
                               "reasons": e.get("reasons") or [], "numbers": e.get("numbers") or {}})
        elif a in ("gate_decision", "phase6_decision"):
            s["choices"].append({"phase": e.get("phase", 6), "choice": e.get("choice")})
        elif a == "override":
            s["overrides"].append({"phase": e.get("phase"), "was": e.get("original_outcome"), "reason": e.get("reason")})
        elif a.startswith("approval_") and a in ("approval_approved", "approval_rejected"):
            s["approvals"].append({"status": a.split("_", 1)[1], "action": e.get("requested_action") or "",
                                   "by": e.get("approved_by"), "detail": e.get("approval_id", "")})
        elif a in ("would_publish", "would_send"):
            s["stubbed"].append({"what": a.replace("_", " "), "destination": e.get("destination", ""), "stub": e.get("stub")})
        elif a.startswith("mock_"):
            s["ledger"].append({"event": a, "detail": {k: v for k, v in e.items() if k in ("amount_minor", "currency", "order_id", "allowed", "reason", "matched", "issues", "net_minor", "fee_minor")}})
        elif a == "guardrail_refusal":
            s["refusals"].append({"rule": e.get("rule"), "match": e.get("match")})
        elif a == "model_error":
            s["model_errors"] += 1
        elif a == "write_output":
            s["files"].append(e["path"])
            s["max_phase"] = max(s["max_phase"], _phase_of(e["path"]))
        if e.get("model") and a not in ("model_error",):
            s["models"][e["model"]] = s["models"].get(e["model"], 0) + 1
            s["calls"] += 1
            s["prompt_tokens"] += int(e.get("prompt_tokens") or 0)
            s["completion_tokens"] += int(e.get("completion_tokens") or 0)
            s["model_wall_s"] += float(e.get("wall_s") or 0)
    # approvals: pair the request entries with their status
    for g in s["gates"]:
        if not g["phase"]:
            m = re.search(r"([1-6])", g["gate"])
            g["phase"] = int(m.group(1)) if m else 0
        s["max_phase"] = max(s["max_phase"], g["phase"])
    # verdict text from the gate JSON files
    verdicts = {}
    for f in s["files"]:
        if "_gate_" in f and f.endswith(".json"):
            try:
                body = json.loads(_read(root, f))
                verdicts.setdefault(_phase_of(f), []).append(body.get("gate", {}).get("verdict", ""))
            except ValueError:
                pass
    for f in s["files"]:          # phases whose gate is written only as Markdown (e.g. Phase 6)
        if "_gate_" in f and f.endswith(".md") and not verdicts.get(_phase_of(f)):
            m = re.search(r"\*\*Outcome:\*\*[^\n]*\n\s*\n([^\n|#]+)", _read(root, f))
            if m:
                verdicts.setdefault(_phase_of(f), []).append(m.group(1).strip())
    for g in s["gates"]:
        vs = verdicts.get(g["phase"]) or []
        g["verdict"] = vs.pop(0) if vs else ""
    # key content
    for f in s["files"]:
        b = os.path.basename(f)
        if b.startswith("phase1_step2_evidence") and f.endswith(".json"):
            try:
                ev = json.loads(_read(root, f))
                reg = {r.get("source_id") or r.get("id"): r for r in ev.get("registry", []) if isinstance(r, dict)}
                s["pain_points"] = [{"text": x.get("pain_point", ""), "url": (reg.get(x["source_id"]) or {}).get("url", ""),
                                     "signal": x.get("signal", "")} for x in ev.get("relevant", [])]
            except (ValueError, KeyError, TypeError):
                pass
        elif b.startswith("phase6_step") and "memo" in b and f.endswith(".md"):
            s["memo"] = _read(root, f)
        elif b.startswith("phase4_step") and "pric" in b and f.endswith(".md"):
            s["price"] = _read(root, f)
        elif b.startswith("phase5_step") and "store" in b and f.endswith(".md"):
            s["store"] = _read(root, f)
    s["sources"] = [u for u in s["sources"] if u.startswith("http")]
    return s


# ------------------------------------------------------------------ markdown
def _num(n):
    return f"{n:,}"


def to_markdown(s):
    out = s["outcome"] or "not finished"
    L = [f"# Run report · {s['label']} · {s['run_id']}", "",
         "Generated by code from `decision_log.json` and this run's files. Nothing here is typed by hand.", "",
         f"**Idea:** {s['idea']}", "",
         f"**Result:** {OUTCOME_WORDS.get(out, out)} (`{out}`). Reason: {s['reason'] or 'run not finished'}.", "",
         f"**Furthest phase reached:** Phase {s['max_phase']} of 6 ({PHASE_NAMES.get(s['max_phase'], '-')}).", "",
         "| Measure | Value |", "|---|---|",
         f"| Model calls | {s['calls']} ({', '.join(f'{m} × {n}' for m, n in s['models'].items()) or 'none'}) |",
         f"| Tokens (prompt / completion) | {_num(s['prompt_tokens'])} / {_num(s['completion_tokens'])} |",
         f"| Cost | ${s['cost']:.2f} (local open-weight model, no paid API) |",
         f"| Agent time | {s['system_time_s'] if s['system_time_s'] is not None else '-'} s (excludes time waiting for the founder) |",
         f"| Model errors handled | {s['model_errors']} |",
         f"| Files written | {len(s['files'])} |", "",
         "Labels: " + " · ".join(LABELS), ""]
    if s["overrides"]:
        L += ["> **UNVALIDATED · FOUNDER OVERRIDE.** The founder continued past an evidence gate. Every later file carries this banner.", ""]
        L += [f"> Phase {o['phase']} (gate said `{o['was']}`): \"{o['reason']}\"" for o in s["overrides"]] + [""]
    L += ["## Gates and founder decisions", "", "| Phase | Gate result | Founder chose | Why (computed by code) |", "|---|---|---|---|"]
    choices = {}
    for c in s["choices"]:
        choices.setdefault(c["phase"], []).append(c["choice"])
    for g in s["gates"]:
        ch = choices.get(g["phase"], [])
        L.append(f"| {g['phase']} · {PHASE_NAMES.get(g['phase'], '')} | `{g['outcome']}` | {ch.pop(0) if ch else _auto(g)} | "
                 f"{(g.get('verdict') or '; '.join(map(str, g['reasons']))).replace('|', '/')[:400]} |")
    if s["pain_points"]:
        L += ["", "## Evidence the system counted (Phase 1)", ""]
        L += [f"- {p['text']} ({p['signal']}) [source]({p['url']})" for p in s["pain_points"]]
    if s["approvals"] or s["stubbed"]:
        L += ["", "## Founder approvals", ""]
        L += [f"- {a['status']}: {a['action'] or 'action'} (approved_by: {a['by'] or '-'})" for a in s["approvals"]]
        L += [f"- STUBBED effect: {x['what']} → {x['destination'] or 'nowhere (stub)'}" for x in s["stubbed"]]
    if s["ledger"]:
        L += ["", "## MOCKED sale to cash (local ledger only)", ""]
        L += [f"- {x['event'].replace('_', ' ')} {json.dumps(x['detail']) if x['detail'] else ''}" for x in s["ledger"]]
    if s["refusals"]:
        L += ["", "## Guardrail refusals", ""] + [f"- {r['rule']}: '{r['match']}'" for r in s["refusals"]]
    if s["memo"]:
        L += ["", "## Phase 6 memo (as written by the run)", "", _demote(s["memo"])]
    L += ["", "## Files this run wrote", ""] + [f"- [{os.path.basename(f)}]({os.path.basename(f)})" for f in s["files"]]
    if s["sources"]:
        L += ["", "## Sources cited by agents", ""] + [f"- {u}" for u in s["sources"][:40]]
    return "\n".join(L) + "\n"


def _auto(g):
    """What happened at a gate that needed no founder choice."""
    return {"go": "continued (go)", "repeat": "automatic retry"}.get(g["outcome"], "-")


def _demote(md):
    return re.sub(r"^(#{1,5}) ", lambda m: "#" * min(6, len(m.group(1)) + 2) + " ", md, flags=re.M)


# ------------------------------------------------------------------ html
CSS = """
body{font:15px/1.55 system-ui,-apple-system,'Segoe UI',sans-serif;color:#1d1f1a;background:#fbfaf6;margin:0}
main{max-width:920px;margin:0 auto;padding:36px 28px 60px}
.k{font:600 11px/1 ui-monospace,Menlo,monospace;letter-spacing:.14em;text-transform:uppercase;color:#5c5a50}
h1{font:600 30px/1.15 Georgia,serif;margin:10px 0 6px} h2{font:600 19px/1.3 Georgia,serif;margin:30px 0 10px;border-bottom:1px solid #d8d4c6;padding-bottom:6px}
.res{display:inline-block;padding:6px 12px;border:1px solid currentColor;font-weight:600;margin:8px 0}
.go{color:#17663b}.stop{color:#a52a1d}.repeat,.awaiting_evidence{color:#7a5a00}.pivot_back{color:#1d4f91}
.grid{display:grid;grid-template-columns:repeat(4,1fr);border:1px solid #d8d4c6;margin:16px 0}
.grid div{padding:12px;border-right:1px solid #d8d4c6}.grid div:last-child{border-right:0}.grid b{display:block;font-size:20px}
table{border-collapse:collapse;width:100%;font-size:14px}th,td{border:1px solid #d8d4c6;padding:7px 9px;text-align:left;vertical-align:top}
th{background:#ece8dc}.warn{background:#fff3d6;border:1px solid #e0b84a;padding:10px 14px;margin:14px 0}
.chips span{display:inline-block;border:1px solid #8a8678;font:600 10px/1 ui-monospace,monospace;letter-spacing:.1em;padding:5px 7px;margin:0 6px 6px 0}
.phases{display:grid;grid-template-columns:repeat(6,1fr);gap:0;border:1px solid #d8d4c6}
.phases div{padding:10px 8px;border-right:1px solid #d8d4c6;font-size:13px}.phases div:last-child{border-right:0}
.phases .on{background:#1d1f1a;color:#fbfaf6}.memo{background:#fff;border:1px solid #d8d4c6;padding:14px 18px;white-space:pre-wrap;font-size:14px}
a{color:#1d4f91}
@media print{body{background:#fff}main{padding:0}}
"""


def to_html(s):
    e = html.escape
    out = s["outcome"] or "not finished"
    phases = "".join(f'<div class="{"on" if i <= s["max_phase"] else ""}">{i} · {n}</div>' for i, n in PHASE_NAMES.items())
    choices = {}
    for c in s["choices"]:
        choices.setdefault(c["phase"], []).append(c["choice"])
    rows = ""
    for g in s["gates"]:
        ch = choices.get(g["phase"], [])
        rows += (f'<tr><td>{g["phase"]} · {e(PHASE_NAMES.get(g["phase"], ""))}</td><td class="{e(str(g["outcome"]))}"><b>{e(OUTCOME_WORDS.get(g["outcome"], str(g["outcome"])))}</b></td>'
                 f'<td>{e(str(ch.pop(0) if ch else _auto(g)))}</td><td>{e((g.get("verdict") or "; ".join(map(str, g["reasons"])))[:600])}</td></tr>')
    pains = "".join(f'<li>{e(p["text"])} <span class="k">{e(p["signal"])}</span> <a href="{e(p["url"])}">source</a></li>' for p in s["pain_points"])
    appr = "".join(f'<li>{e(a["status"])}: {e(a["action"] or "action")} (approved_by: {e(str(a["by"] or "-"))})</li>' for a in s["approvals"])
    appr += "".join(f'<li>STUBBED: {e(x["what"])}</li>' for x in s["stubbed"])
    ledger = "".join(f'<li>{e(x["event"].replace("_", " "))} {e(json.dumps(x["detail"])) if x["detail"] else ""}</li>' for x in s["ledger"])
    files = "".join(f'<li>{e(os.path.basename(f))}</li>' for f in s["files"])
    srcs = "".join(f'<li><a href="{e(u)}">{e(u)}</a></li>' for u in s["sources"][:40])
    ov = "".join(f'<p>Phase {o["phase"]} (gate said <code>{e(str(o["was"]))}</code>): “{e(o["reason"] or "")}”</p>' for o in s["overrides"])
    models = ", ".join(f"{e(m)} × {n}" for m, n in s["models"].items()) or "none"
    return f"""<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Run report · {e(s['label'])}</title><style>{CSS}</style></head><body><main>
<div class="k">Run report · {e(s['run_id'])} · generated from the decision log</div>
<h1>{e(str(s['idea']))}</h1>
<div class="res {e(out)}">Result: {e(OUTCOME_WORDS.get(out, out))}</div>
<p>{e(s['reason'] or 'Run not finished.')}</p>
<div class="phases">{phases}</div>
<div class="grid"><div><span class="k">Phases reached</span><b>{s['max_phase']} of 6</b></div>
<div><span class="k">Model calls</span><b>{s['calls']}</b></div>
<div><span class="k">Tokens</span><b>{_num(s['prompt_tokens'] + s['completion_tokens'])}</b></div>
<div><span class="k">Cost</span><b>${s['cost']:.2f}</b></div></div>
<p class="k">Model: {models} · agent time {s['system_time_s'] if s['system_time_s'] is not None else '-'} s · model errors handled: {s['model_errors']}</p>
<div class="chips">{''.join(f'<span>{e(x)}</span>' for x in LABELS)}</div>
{f'<div class="warn"><b>UNVALIDATED · FOUNDER OVERRIDE.</b> The founder continued past an evidence gate; every later file carries this banner.{ov}</div>' if s['overrides'] else ''}
<h2>Gates and founder decisions</h2>
<table><tr><th>Phase</th><th>Gate result</th><th>Founder chose</th><th>Why (computed by code)</th></tr>{rows or '<tr><td colspan=4>No gate reached.</td></tr>'}</table>
{f'<h2>Evidence the system counted</h2><ul>{pains}</ul>' if pains else ''}
{f'<h2>Founder approvals</h2><ul>{appr}</ul>' if appr else ''}
{f'<h2>MOCKED sale to cash</h2><p>Local SQLite ledger only. No payment of any kind ran.</p><ul>{ledger}</ul>' if ledger else ''}
{f'<h2>Phase 6 memo</h2><div class="memo">{e(s["memo"])}</div>' if s['memo'] else ''}
<h2>Files this run wrote</h2><ul>{files}</ul>
{f'<h2>Sources cited by agents</h2><ul>{srcs}</ul>' if srcs else ''}
</main></body></html>"""


# ------------------------------------------------------------------ pdf
def to_pdf(s, path):
    """Printable PDF with reportlab. Returns the path, or None if reportlab is not installed."""
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
        from reportlab.lib.units import mm
        from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
    except ImportError:
        return None
    e = html.escape
    ss = getSampleStyleSheet()
    body = ParagraphStyle("b", parent=ss["BodyText"], fontSize=9.5, leading=13)
    small = ParagraphStyle("s", parent=body, fontSize=8, leading=10.5, textColor=colors.HexColor("#4a483f"))
    h1 = ParagraphStyle("h1", parent=ss["Title"], fontSize=18, leading=22, alignment=0, spaceAfter=4)
    h2 = ParagraphStyle("h2", parent=ss["Heading2"], fontSize=12.5, leading=16, spaceBefore=10, spaceAfter=4,
                        textColor=colors.HexColor("#1d1f1a"))
    out = s["outcome"] or "not finished"
    col = {"go": "#17663b", "stop": "#a52a1d"}.get(out, "#7a5a00")
    story = [Paragraph(f"RUN REPORT · {e(s['run_id'])}", small), Paragraph(e(str(s["idea"])), h1),
             Paragraph(f'<font color="{col}"><b>Result: {e(OUTCOME_WORDS.get(out, out))}</b></font> · {e(s["reason"] or "run not finished")}', body),
             Spacer(1, 6)]
    grid = [["Phases reached", "Model calls", "Tokens", "Cost"],
            [f"{s['max_phase']} of 6", str(s["calls"]), _num(s["prompt_tokens"] + s["completion_tokens"]), f"${s['cost']:.2f}"]]
    t = Table(grid, colWidths=[44 * mm] * 4)
    t.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#c9c4b5")), ("FONTSIZE", (0, 0), (-1, 0), 7.5),
                           ("FONTSIZE", (0, 1), (-1, 1), 13), ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#5c5a50")),
                           ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 6)]))
    story += [t, Spacer(1, 4), Paragraph("Model: " + e(", ".join(f"{m} × {n}" for m, n in s["models"].items()) or "none")
                                         + f" · agent time {s['system_time_s'] if s['system_time_s'] is not None else '-'} s", small),
              Paragraph(" · ".join(e(x) for x in LABELS), small)]
    if s["overrides"]:
        story.append(Paragraph("<b>UNVALIDATED · FOUNDER OVERRIDE.</b> " + " ".join(
            f'Phase {o["phase"]} (gate said {e(str(o["was"]))}): “{e(o["reason"] or "")}”' for o in s["overrides"]), body))
    story.append(Paragraph("Gates and founder decisions", h2))
    choices = {}
    for c in s["choices"]:
        choices.setdefault(c["phase"], []).append(c["choice"])
    rows = [[Paragraph("<b>Phase</b>", small), Paragraph("<b>Gate</b>", small), Paragraph("<b>Founder</b>", small), Paragraph("<b>Why (code)</b>", small)]]
    for g in s["gates"]:
        ch = choices.get(g["phase"], [])
        rows.append([Paragraph(f"{g['phase']} · {e(PHASE_NAMES.get(g['phase'], ''))}", small),
                     Paragraph(e(OUTCOME_WORDS.get(g["outcome"], str(g["outcome"]))), small),
                     Paragraph(e(str(ch.pop(0) if ch else _auto(g))), small),
                     Paragraph(e((g.get("verdict") or "; ".join(map(str, g["reasons"])))[:500]), small)])
    gt = Table(rows, colWidths=[30 * mm, 26 * mm, 22 * mm, 98 * mm], repeatRows=1)
    gt.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#c9c4b5")),
                            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#ece8dc")), ("VALIGN", (0, 0), (-1, -1), "TOP")]))
    story.append(gt)
    if s["pain_points"]:
        story.append(Paragraph("Evidence the system counted (Phase 1)", h2))
        story += [Paragraph(f'• {e(p["text"])} <font color="#5c5a50">({e(p["signal"])})</font> <link href="{e(p["url"])}"><font color="#1d4f91">{e(p["url"][:70])}</font></link>', small)
                  for p in s["pain_points"]]
    if s["approvals"] or s["stubbed"]:
        story.append(Paragraph("Founder approvals", h2))
        story += [Paragraph(f'• {e(a["status"])}: {e(a["action"] or "action")} (approved_by: {e(str(a["by"] or "-"))})', small) for a in s["approvals"]]
        story += [Paragraph(f'• STUBBED: {e(x["what"])}', small) for x in s["stubbed"]]
    if s["ledger"]:
        story.append(Paragraph("MOCKED sale to cash (local ledger only, no payment of any kind)", h2))
        story += [Paragraph(f'• {e(x["event"].replace("_", " "))} {e(json.dumps(x["detail"])) if x["detail"] else ""}', small) for x in s["ledger"]]
    if s["memo"]:
        story.append(Paragraph("Phase 6 memo", h2))
        for line in s["memo"].splitlines():
            if line.strip():
                story.append(Paragraph(e(re.sub(r"[#*`]", "", line)), small))
    story.append(Paragraph("Files this run wrote", h2))
    story += [Paragraph("• " + e(os.path.basename(f)), small) for f in s["files"]]

    def footer(c, d):
        c.saveState()
        c.setFont("Helvetica", 7)
        c.setFillColor(colors.HexColor("#6b6859"))
        c.drawString(14 * mm, 9 * mm, f"Agentic Venture Builder · run {s['run_id']} · generated from decision_log.json")
        c.drawRightString(A4[0] - 14 * mm, 9 * mm, f"Page {d.page}")
        c.restoreState()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    SimpleDocTemplate(path, pagesize=A4, leftMargin=14 * mm, rightMargin=14 * mm, topMargin=14 * mm, bottomMargin=16 * mm,
                      title=f"Run report {s['run_id']}").build(story, onFirstPage=footer, onLaterPages=footer)
    return path


def pdf_path(run_id):
    return os.path.join(config.state_dir(), "reports", f"{run_id}.pdf")


# ------------------------------------------------------------------ entry points
def write_for(ctx):
    """Called when a run ends. Writes the .md and .html report as outputs and the PDF to state/."""
    try:
        s = summarize(logmod.entries(run_id=ctx.run_id), ctx.run_id)
        s["label"] = ctx.label
        n = max(1, s["max_phase"])
        md = ctx.out(f"phase{n}_step9_run_report", "md", to_markdown(s))
        ctx.out(f"phase{n}_step9_run_report", "html", to_html(s))
        pdf = to_pdf(s, pdf_path(ctx.run_id))
        ctx.data["report_pdf"] = pdf
        return md
    except Exception as ex:  # noqa: BLE001 - a report problem must never change a run's outcome
        ctx.log("orchestrator", "run_report_failed", error=f"{type(ex).__name__}: {ex}"[:200])
        return None
