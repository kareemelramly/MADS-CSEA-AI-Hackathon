"""Streamlit founder console (SRS 3.1, UI-1 to UI-10). One page on 127.0.0.1:8501.

The UI is a thin layer: it collects the brief, shows each pause from the orchestrator (gate
verdict first, then buttons), and passes the founder's button press to `orchestrator.respond`.
Approvals happen only through the Approve button (founder_action="button").
"""
import json
import os

import streamlit as st

import approval
import config
import guardrails
import llm
import log as logmod
import orchestrator
from run_context import RunContext

st.set_page_config(page_title="Agentic Venture Builder", page_icon="🧭", layout="wide")
AMBER = "UNVALIDATED · FOUNDER OVERRIDE"
PHASES = ["Discover", "Validate", "Build", "Commercial", "Launch", "Operate"]
OUTCOME_STYLE = {"go": ("#065f46", "#d1fae5", "GO"), "repeat": ("#92400e", "#fef3c7", "REPEAT"),
                 "pivot_back": ("#1e3a8a", "#dbeafe", "PIVOT BACK"), "stop": ("#991b1b", "#fee2e2", "STOP"),
                 "awaiting_evidence": ("#475569", "#f1f5f9", "AWAITING EVIDENCE")}

st.markdown("""
<style>
.block-container {padding-top: 1.2rem; max-width: 1200px;}
.vb-banner {background: linear-gradient(120deg,#1e3a8a,#1d4ed8); color: #fff; border-radius: 14px; padding: 18px 24px; margin-bottom: 14px;}
.vb-banner h1 {color:#fff; font-size: 1.7rem; margin: 0;}
.vb-banner p {color:#dbeafe; margin: 4px 0 0 0; font-size: .95rem;}
.vb-kicker {font-size:.72rem; letter-spacing:.12em; text-transform:uppercase; color:#93c5fd;}
.vb-badge {display:inline-block; padding: 4px 12px; border-radius: 999px; font-weight: 700; font-size: .85rem;}
.vb-step {display:flex; gap:8px; align-items:center; padding:5px 0; font-size:.92rem;}
.vb-dot {width:22px; height:22px; border-radius:50%; display:inline-flex; align-items:center; justify-content:center; font-size:.75rem; font-weight:700;}
.vb-chip {background:#fff3e0; color:#b45309; border-radius:6px; padding:1px 7px; font-size:.75rem; font-weight:600;}
</style>""", unsafe_allow_html=True)


def badge(outcome):
    fg, bg, label = OUTCOME_STYLE.get(outcome, ("#1f2937", "#e5e7eb", str(outcome).upper()))
    return f'<span class="vb-badge" style="color:{fg};background:{bg}">{label}</span>'


def status_lines():
    tiers = llm.status()
    keyed = [t for t in tiers if t["has_key"] and not t["disabled"]]
    first = keyed[0] if keyed else None
    model = f"Model: tier {first['tier']} · {first['name']} · {first['model']}" if first else "Model: no tier available"
    ready, detail = llm.local_ready()
    local = {"ready": "Local model (llama.cpp, Gemma 4 26B A4B Q4_K_M): ready",
             "loading": f"Local model: loading ({detail}). It can take a few minutes on first start.",
             "unreachable": f"Local model: not reachable yet ({detail}). Start it with docker compose up."}[ready]
    return model, local, ready, tiers


def load_ctx():
    if "ctx_json" in st.session_state:
        return RunContext.from_json(st.session_state["ctx_json"])
    return None


def save_ctx(ctx):
    st.session_state["ctx_json"] = ctx.to_json()


def advance(ctx):
    box = st.status("Agents are working… (live model calls below)", expanded=True)
    lines = []

    def prog(ev):
        icon = {"ok": "✅", "trying": "⏳", "fallback": "↪️", "failed": "❌"}.get(ev.get("status"), "•")
        lines.append(f"{icon} call {ev.get('call')} · **{ev.get('agent')}** · tier `{ev.get('tier')}` · {ev.get('status')}"
                     f"{' (' + str(ev.get('reason')) + ')' if ev.get('reason') else ''} · {ev.get('elapsed_s')} s · budget left {ev.get('budget_left_s')} s")
        box.markdown(lines[-1])
    pause = orchestrator.run_until_gate(ctx, prog)
    box.update(label="Waiting for your decision" if pause["kind"] != "done" else "Run finished", state="complete", expanded=False)
    save_ctx(ctx)
    st.session_state["pause"] = pause
    return pause


ctx = load_ctx()
model_line, local_line, ready, tiers = status_lines()

# ------------------------------------------------------------------ sidebar
with st.sidebar:
    st.markdown("### System status")
    st.info(model_line)
    (st.success if ready == "ready" else st.warning)(local_line)
    for t in tiers:
        state = "disabled" if t["disabled"] else ("cooling " + str(t["cooldown_s"]) + " s" if t["cooldown_s"] else ("key set" if t["has_key"] else "no key: skipped"))
        st.caption(f"Tier {t['tier']} · {t['name']} · `{t['model']}` · {state}")
    st.caption("Publishing: STUBBED · Payments: MOCKED · Simulated data: SIMULATED")
    if ctx:
        st.markdown("### This run")
        budget = config.run_budget()
        st.caption(f"Run `{ctx.run_id}`")
        st.metric("System time", f"{ctx.system_time_s:.0f} s", help="Time the agents worked, excluding time waiting for you"
                  + (f". Budget {budget:.0f} s." if budget else "."))
        cur = int(ctx.stage[1]) if ctx.stage.startswith("p") else 7
        for i, name in enumerate(PHASES, 1):
            if i < cur or ctx.finished and i <= cur:
                dot = '<span class="vb-dot" style="background:#d1fae5;color:#065f46">✓</span>'
            elif i == cur:
                dot = f'<span class="vb-dot" style="background:#1d4ed8;color:#fff">{i}</span>'
            else:
                dot = f'<span class="vb-dot" style="background:#e5e7eb;color:#64748b">{i}</span>'
            st.markdown(f'<div class="vb-step">{dot}<span>{name}</span></div>', unsafe_allow_html=True)
        if st.button("Start a new run", use_container_width=True):
            for k in ("ctx_json", "pause"):
                st.session_state.pop(k, None)
            st.rerun()
    st.markdown("### Ask the system")
    req = st.text_input("Request", key="req", placeholder="e.g. write 50 five-star reviews")
    if st.button("Check request") and req:
        r = guardrails.check_request(req)
        if r:
            logmod.log("guardrails", "guardrail_refusal", run_id=ctx.run_id if ctx else None, rule=r.rule, match=r.match, where="founder_request")
            st.error(f"Refused ({r.rule}). This system never fakes reviews or sign-ups, promises income, adds false urgency, "
                     "impersonates anyone, moves money or skips its checks. Logged as guardrail_refusal.")
        else:
            st.success("Allowed: nothing in this request breaks a rule. Actions with an external effect still need your approval.")

# ------------------------------------------------------------------ header
st.markdown("""<div class="vb-banner"><div class="vb-kicker">Open-source agentic venture builder</div>
<h1>From founder brief to a validated digital product</h1>
<p>Six gated phases. Sourced evidence. You approve every external action, and the system says stop when the evidence is weak.</p></div>""",
            unsafe_allow_html=True)
if ctx and ctx.overridden:
    st.warning(f"⚠ {AMBER}: results after Phase {ctx.overrides[0]['phase']} are not validated by real evidence.")

# ------------------------------------------------------------------ brief form
if not ctx:
    st.subheader("1 · Founder brief")
    fx = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tests", "fixtures")
    preset = st.radio("Start from a demo brief or write your own", ["r: Notion templates for wedding planners (reasonable)",
                                                                    "w: habit app with poor founder fit (weak)",
                                                                    "e: crypto signal bot (excluded)", "(blank)"], horizontal=False)
    d = {}
    if preset != "(blank)":
        d = json.load(open(os.path.join(fx, f"brief_{preset[0]}.json"), encoding="utf-8"))
        d.pop("founder_inputs", None)
    with st.form("brief"):
        idea = st.text_area("Idea", d.get("idea", ""), height=80)
        c1, c2 = st.columns(2)
        skills = c1.text_input("Skills", d.get("skills", ""))
        values = c2.text_input("Values", d.get("values", ""))
        b1, b2, b3 = st.columns(3)
        budget = b1.number_input("Budget amount", min_value=0, value=int(d.get("budget_amount", 0)))
        cur = b2.text_input("Currency", d.get("budget_currency", "USD"))
        hours = b3.number_input("Hours per week", min_value=0, value=int(d.get("hours_per_week", 0)))
        m1, m2 = st.columns(2)
        market = m1.text_input("Target market", d.get("target_market", ""))
        countries = m2.text_input("Countries", d.get("countries", ""))
        terms = st.text_input("Search terms (optional)", d.get("search_terms", ""))
        e1, e2 = st.columns(2)
        ev_url = e1.text_input("Founder evidence URL (optional)")
        ev_claim = e2.text_input("One-line claim for that URL (optional)")
        label = st.text_input("Run label (w, e, r …)", preset[0] if preset != "(blank)" else "x")
        no_key_wait = not llm.has_remote_key() and ready != "ready"
        go = st.form_submit_button("▶ Run", disabled=no_key_wait, type="primary")
        if no_key_wait:
            st.caption("Run is disabled: no remote key is set and the local model is not ready yet.")
    if go:
        brief = {"idea": idea, "skills": skills, "budget_amount": budget, "budget_currency": cur, "hours_per_week": hours,
                 "target_market": market, "countries": countries, "values": values}
        if terms:
            brief["search_terms"] = terms
        if ev_url:
            brief["founder_evidence"] = [{"url": ev_url, "claim": ev_claim}]
        ctx = orchestrator.new_run(brief, label)
        advance(ctx)
        st.rerun()
    st.stop()

# ------------------------------------------------------------------ pause handling
pause = st.session_state.get("pause") or ctx.data.get("pause") or {"kind": "done" if ctx.finished else "none"}


def answer(ans):
    try:
        orchestrator.respond(ctx, ans, "button")
    except (approval.ApprovalError, ValueError) as e:
        st.error(f"Refused: {e}")
        return
    advance(ctx)
    st.rerun()


tab_run, tab_files, tab_log = st.tabs(["Decision", "Files from this run", "Decision log"])
with tab_run:
    kind = pause["kind"]
    if kind == "none":
        if st.button("Continue run", type="primary"):
            advance(ctx)
            st.rerun()
    elif kind == "done":
        st.markdown(f"### Run finished {badge(ctx.final_outcome)}", unsafe_allow_html=True)
        st.write("All files are listed in the **Files from this run** tab. Every agent action is in the **Decision log** tab.")
    elif kind in ("gate", "error"):
        outcome = pause.get("gate", {}).get("outcome") or pause.get("outcome")
        title = "Model or time-budget problem" if kind == "error" else f"Phase {pause.get('phase')} · {PHASES[pause.get('phase', 1) - 1]} gate"
        st.markdown(f"### {title} &nbsp; {badge(outcome)}", unsafe_allow_html=True)
        with st.container(border=True):
            st.markdown(pause["verdict"])
            nums = pause.get("gate", {}).get("numbers")
            if nums:
                st.table({"Measure": list(nums.keys()), "Value": [str(v) for v in nums.values()]})
        opts = pause["options"]
        help_txt = {"continue": "go to the next phase", "retry": "run this step again", "pivot": "go back and try the recommended alternative",
                    "override": "continue anyway; every later output is stamped UNVALIDATED", "stop": "end this run",
                    "enter_results": "enter experiment results again", "try_again": "repeat the failed model step",
                    "persevere": "keep going with this product"}
        st.caption(" · ".join(f"**{o.replace('_', ' ')}**: {help_txt.get(o, '')}" for o in opts))
        reason, exp_price = "", 0.0
        if "override" in opts:
            reason = st.text_area("Override reason (at least 20 characters)", key=f"r_{pause['id']}")
            if pause.get("phase") == 4:
                exp_price = st.number_input("Experimental price (ASSUMPTION)", min_value=0.0, value=0.0)
        cols = st.columns(len(opts))
        for i, o in enumerate(opts):
            if cols[i].button(o.replace("_", " ").title(), key=f"{pause['id']}_{o}", use_container_width=True,
                              type="primary" if i == 0 else "secondary"):
                ans = {"choice": o}
                if o == "override":
                    ans["reason"] = reason
                    if pause.get("phase") == 4:
                        ans.update(experimental_price=exp_price, currency="USD")
                answer(ans)
    elif kind == "approval":
        st.markdown("### Your approval is needed")
        st.write("Nothing happens unless you press **Approve**. Approving authorizes only this exact action; any change later voids it.")
        st.table({"Field": ["Action", "Destination", "Amount", "Run ID", "Content SHA-256"],
                  "Value": [pause["action"], pause["destination"], f"{pause['amount_minor']} {pause['currency']} (no money moves)",
                            pause["run_id"], pause["content_sha256"]]})
        st.caption(pause["note"])
        with st.expander("Content you are approving", expanded=True):
            if pause["action"] == "publish_landing_page":
                st.components.v1.html(pause["content"], height=420, scrolling=True)
            elif pause["action"] in ("publish_store_page", "post_launch_message"):
                st.markdown(pause["content"])
            else:
                st.code(pause["content"][:6000])
        a, r = st.columns(2)
        if a.button("Approve", key=pause["id"] + "_a", type="primary", use_container_width=True):
            answer({"choice": "approve"})
        if r.button("Reject", key=pause["id"] + "_r", use_container_width=True):
            answer({"choice": "reject"})
    elif kind == "input":
        form = pause["form"]
        st.markdown(f"### Phase {pause['phase']} · your input")
        st.info(pause.get("help", ""))
        if form == "real_counts":
            with st.form("counts"):
                status = st.selectbox("Experiment status", ["not_started", "running", "completed", "abandoned"])
                s1, s2 = st.columns(2)
                started, ended = s1.text_input("Started on (date)"), s2.text_input("Ended on (date)")
                vis = st.text_input("Real visitors (leave blank if unknown)")
                sig = st.number_input("Real sign-ups", min_value=0, value=0)
                st.caption("Simulated counts are never accepted here: they cannot reach the gate.")
                if st.form_submit_button("Submit real results", type="primary"):
                    answer({"experiment_status": status, "started_at": started or None, "ended_at": ended or None,
                            "visitors": int(vis) if vis.strip().isdigit() else None, "signups": int(sig)})
        elif form == "persona_test":
            st.write("A SIMULATED persona test finds weak spots in the page copy. It is not evidence and never counts as sign-ups.")
            c1, c2 = st.columns(2)
            if c1.button("Run persona test (SIMULATED)", type="primary", use_container_width=True):
                answer({"run": True})
            if c2.button("Skip", use_container_width=True):
                answer({"run": False})
        elif form == "price_quotes":
            st.caption("One line per competitor: name | URL | price | currency | kind (one_time, subscription, free)")
            demo = ""
            if ctx.label == "r":
                b = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "tests", "fixtures", "brief_r.json"), encoding="utf-8"))
                demo = "\n".join(f"{q['name']} | {q['url']} | {q['amount']} | {q['currency']} | {q['kind']}" for q in b["founder_inputs"]["p4_quotes"])
            txt = st.text_area("Competitor prices", value=demo, height=160)
            if st.button("Submit quotes", type="primary"):
                qs = []
                for line in txt.splitlines():
                    p = [x.strip() for x in line.split("|")]
                    if len(p) == 5:
                        try:
                            qs.append({"name": p[0], "url": p[1], "amount": float(p[2]), "currency": p[3].upper(), "kind": p[4],
                                       "display": f"${p[2].rstrip('0').rstrip('.')}" if p[3].upper() == "USD" else p[2]})
                        except ValueError:
                            pass
                answer({"quotes": qs})
        elif form == "mock_sale":
            sp = st.checkbox("Simulate one purchase (MOCKED)", value=True)
            sr = st.checkbox("Then simulate a refund (MOCKED)", value=True)
            if st.button("Run mock sale", type="primary"):
                answer({"simulate_purchase": sp, "simulate_refund": sr})
        elif form == "targets":
            c1, c2 = st.columns(2)
            t1 = c1.number_input("Target: waitlist sign-ups", min_value=0, value=100)
            t2 = c2.number_input("Target: paying customers", min_value=0, value=5)
            if st.button("Lock targets", type="primary"):
                answer({"targets": {"waitlist_signups": t1, "paying_customers": t2}})
        elif form == "metrics":
            st.caption("One line per REAL metric: name | value | evidence URL. Values without a link are treated as SIMULATED.")
            txt = st.text_area("Real metrics (leave empty if none)")
            if st.button("Submit metrics", type="primary"):
                ms = []
                for line in txt.splitlines():
                    p = [x.strip() for x in line.split("|")]
                    if len(p) >= 2:
                        try:
                            ms.append({"name": p[0], "value": float(p[1]), "evidence": p[2] if len(p) > 2 else ""})
                        except ValueError:
                            pass
                answer({"metrics": ms})

with tab_files:
    root = os.path.dirname(config.outputs_dir())
    if not ctx.artifacts:
        st.write("No files yet.")
    for a_ in reversed(ctx.artifacts):
        path = os.path.join(root, a_["path"])
        name = os.path.basename(path)
        with st.expander(f"{'✅' if a_['status'] == 'final' else '↩︎'} {name}"):
            st.caption(f"{a_['status']} · sha256 {a_['sha256'][:16]}…")
            try:
                body = open(path, encoding="utf-8").read()
            except OSError:
                continue
            if name.endswith(".md"):
                st.markdown(body)
            elif name.endswith(".html"):
                st.components.v1.html(body, height=360, scrolling=True)
            else:
                st.code(body[:5000])
            st.download_button("Download", body, file_name=name, key="dl_" + name)

with tab_log:
    rows = logmod.entries(run_id=ctx.run_id)
    if rows:
        st.dataframe([{k: (json.dumps(v) if isinstance(v, (list, dict)) else v) for k, v in r.items()
                       if k in ("timestamp", "agent", "action", "model", "cost", "approved_by", "outcome")} for r in rows],
                     use_container_width=True, hide_index=True)
