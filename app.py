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

st.set_page_config(page_title="Venture Builder · Team Delulu", layout="wide")
AMBER = "UNVALIDATED · FOUNDER OVERRIDE"
PHASES = ["Discover", "Validate", "Build", "Commercial", "Launch", "Operate"]
OUTCOME_STYLE = {"go": ("var(--go)", "Go"), "repeat": ("var(--repeat)", "Repeat"), "pivot_back": ("var(--pivot)", "Pivot back"),
                 "stop": ("var(--stop)", "Stop"), "awaiting_evidence": ("var(--await)", "Awaiting evidence")}
GRAIN = ("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='160' height='160'><filter id='n'>"
         "<feTurbulence type='fractalNoise' baseFrequency='.9' numOctaves='2' stitchTiles='stitch'/></filter>"
         "<rect width='100%25' height='100%25' filter='url(%23n)' opacity='.55'/></svg>")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Instrument+Serif:ital@0;1&family=Space+Grotesk:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap');
:root{
  --ink:#0C0D0A; --ink-2:#15170F; --paper:#ECE8DC; --muted:#A39F90; --line:rgba(236,232,220,.13); --line-strong:rgba(236,232,220,.28);
  --accent:#E4FF4F; --go:#7FE3A5; --repeat:#F3C34E; --pivot:#86BEFF; --stop:#FF7262; --await:#BEB9AA;
  --serif:'Instrument Serif',Georgia,'Times New Roman',serif; --sans:'Space Grotesk',ui-sans-serif,system-ui,sans-serif;
  --mono:'IBM Plex Mono',ui-monospace,SFMono-Regular,Menlo,monospace;
}
html,body,.stApp,[class*="css"],.stMarkdown,p,li,label,input,textarea,button{font-family:var(--sans)!important;}
.stApp{background:
  radial-gradient(1200px 600px at 85% -10%,rgba(228,255,79,.07),transparent 60%),
  radial-gradient(900px 500px at -10% 110%,rgba(134,190,255,.05),transparent 60%), var(--ink);}
.stApp::before{content:"";position:fixed;inset:0;pointer-events:none;background-image:url("GRAIN_URI");opacity:.06;mix-blend-mode:overlay;z-index:0;}
.block-container{padding-top:1.6rem;max-width:1240px;}
h1,h2,h3{font-family:var(--serif)!important;font-weight:400!important;letter-spacing:-.02em;line-height:1.05;color:var(--paper);}
code,.mono{font-family:var(--mono)!important;font-size:.82em;}
section[data-testid="stSidebar"]{background:var(--ink-2);border-right:1px solid var(--line);}
section[data-testid="stSidebar"] h3{font-size:1.35rem;margin-top:.6rem;}
/* masthead */
.mh{border-bottom:1px solid var(--line-strong);padding:0 0 18px;margin-bottom:6px;animation:rise .5s ease both;}
.mh .kicker{font-family:var(--mono);font-size:.72rem;letter-spacing:.18em;text-transform:uppercase;color:var(--accent);}
.mh h1{font-size:clamp(2.1rem,4.4vw,3.5rem);margin:.3rem 0 0;max-width:18ch;}
.mh h1 em{font-style:italic;color:var(--accent);}
.mh.compact h1{font-size:clamp(1.6rem,2.6vw,2.2rem);max-width:none;} .mh.compact p{display:none;}
.mh p{color:var(--muted);max-width:52ch;margin:.6rem 0 0;font-size:1rem;line-height:1.55;}
.meta{margin-top:2.6rem;border-left:1px solid var(--line);padding-left:18px;font-family:var(--mono);font-size:.78rem;color:var(--muted);line-height:2;animation:rise .5s .08s ease both;}
.meta b{color:var(--paper);font-weight:500;}
/* phase strip */
.strip{display:grid;grid-template-columns:repeat(6,1fr);border:1px solid var(--line);margin:14px 0 22px;animation:rise .5s .14s ease both;}
.strip div{padding:10px 12px;border-right:1px solid var(--line);font-size:.86rem;color:var(--muted);position:relative;transition:background .2s;}
.strip div:last-child{border-right:0;}
.strip div span{display:block;font-family:var(--mono);font-size:.68rem;letter-spacing:.12em;}
.strip .done{color:var(--paper);} .strip .done span{color:var(--go);}
.strip .now{color:var(--ink);background:var(--accent);} .strip .now span{color:var(--ink);}
.strip div:hover{background:rgba(236,232,220,.04);} .strip .now:hover{background:var(--accent);}
@media (max-width:760px){.strip{grid-template-columns:repeat(3,1fr);} .strip div:nth-child(3){border-right:0;} .meta{border-left:0;padding-left:0;}}
/* verdict */
.verdict{border-left:3px solid var(--c);padding:6px 0 6px 18px;margin:4px 0 14px;animation:rise .45s ease both;}
.verdict .out{font-family:var(--serif);font-size:clamp(2.2rem,4.5vw,3.4rem);color:var(--c);line-height:1;}
.verdict .lbl{font-family:var(--mono);font-size:.72rem;letter-spacing:.16em;text-transform:uppercase;color:var(--muted);}
.chip{display:inline-block;font-family:var(--mono);font-size:.72rem;letter-spacing:.06em;border:1px solid var(--line-strong);padding:1px 8px;margin:0 6px 6px 0;color:var(--paper);}
.chip.warn{border-color:var(--repeat);color:var(--repeat);}
.banner-override{border:1px solid var(--repeat);color:var(--repeat);padding:10px 14px;font-family:var(--mono);font-size:.8rem;letter-spacing:.04em;margin-bottom:10px;}
/* widgets */
.stButton>button,.stDownloadButton>button,[data-testid="stFormSubmitButton"]>button{border-radius:0!important;border:1px solid var(--line-strong)!important;
  background:transparent!important;color:var(--paper)!important;font-weight:500;letter-spacing:.01em;transition:transform .12s ease,border-color .15s,background .15s;}
.stButton>button:hover,[data-testid="stFormSubmitButton"]>button:hover{border-color:var(--accent)!important;transform:translateY(-1px);}
.stButton>button[kind="primary"],[data-testid="stFormSubmitButton"]>button[kind="primaryFormSubmit"]{background:var(--accent)!important;color:var(--ink)!important;border-color:var(--accent)!important;}
.stButton>button:focus-visible,input:focus-visible,textarea:focus-visible{outline:2px solid var(--accent)!important;outline-offset:2px;}
input,textarea,[data-baseweb="select"]>div{border-radius:0!important;}
[data-testid="stTable"] table,[data-testid="stTable"] th,[data-testid="stTable"] td{border-color:var(--line)!important;font-size:.88rem;}
[data-testid="stTable"] td{font-family:var(--mono);}
[data-testid="stExpander"]{border:1px solid var(--line)!important;border-radius:0!important;}
[data-testid="stAlert"]{border-radius:0!important;background:transparent!important;border:1px solid var(--line)!important;border-left:3px solid var(--accent)!important;}
[data-testid="stAlert"] p{color:var(--paper)!important;font-size:.88rem;}
[data-testid="stAlert"] > div,[data-testid="stAlertContainer"]{background:transparent!important;}
[data-testid="stForm"]{border-radius:0!important;border:1px solid var(--line)!important;background:rgba(21,23,15,.55);}
[data-testid="stStatusWidget"],[data-testid="stToolbar"],#MainMenu{visibility:hidden;}
[data-testid="stHeader"]{background:transparent;}
.stTabs [data-baseweb="tab"]{font-family:var(--mono);font-size:.78rem;letter-spacing:.1em;text-transform:uppercase;}
.stTabs [aria-selected="true"]{color:var(--accent)!important;}
.stTabs [data-baseweb="tab-highlight"]{background:var(--accent)!important;}
.small{color:var(--muted);font-size:.84rem;}
@keyframes rise{from{opacity:0;transform:translateY(8px);}to{opacity:1;transform:none;}}
@media (prefers-reduced-motion:reduce){*{animation:none!important;transition:none!important;}}
</style>""".replace("GRAIN_URI", GRAIN), unsafe_allow_html=True)


def badge(outcome):
    c, label = OUTCOME_STYLE.get(outcome, ("var(--paper)", str(outcome).replace("_", " ").title()))
    return f'<span class="chip" style="border-color:{c};color:{c}">{label}</span>'


def verdict_block(outcome, kicker):
    c, label = OUTCOME_STYLE.get(outcome, ("var(--paper)", str(outcome)))
    return f'<div class="verdict" style="--c:{c}"><div class="lbl">{kicker}</div><div class="out">{label}</div></div>'


def phase_strip(ctx):
    cur = int(ctx.stage[1]) if ctx.stage.startswith("p") else 7
    cells = []
    for i, name in enumerate(PHASES, 1):
        cls = "done" if i < cur or (ctx.finished and i <= cur) else ("now" if i == cur and not ctx.finished else "")
        mark = "DONE" if cls == "done" else ("NOW" if cls == "now" else f"0{i}")
        cells.append(f'<div class="{cls}"><span>{mark}</span>{name}</div>')
    return '<div class="strip" role="list">' + "".join(cells) + "</div>"


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
    box = st.status("Agents at work — live model calls", expanded=True)
    lines = []

    def prog(ev):
        icon = {"ok": "●", "trying": "○", "fallback": "→", "failed": "×"}.get(ev.get("status"), "·")
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
    st.markdown("### System")
    st.info(model_line)
    (st.success if ready == "ready" else st.warning)(local_line)
    for t in tiers:
        state = "disabled" if t["disabled"] else ("cooling " + str(t["cooldown_s"]) + " s" if t["cooldown_s"] else ("key set" if t["has_key"] else "no key: skipped"))
        st.markdown(f'<div class="small mono">T{t["tier"]} · {t["name"]} · {t["model"]} · {state}</div>', unsafe_allow_html=True)
    st.markdown('<div style="margin-top:10px"><span class="chip warn">PUBLISHING · STUBBED</span><span class="chip warn">PAYMENTS · MOCKED</span>'
                '<span class="chip warn">PERSONAS · SIMULATED</span></div>', unsafe_allow_html=True)
    if ctx:
        st.markdown("### This run")
        budget = config.run_budget()
        st.caption(f"Run `{ctx.run_id}`")
        st.metric("System time", f"{ctx.system_time_s:.0f} s", help="Time the agents worked, excluding time waiting for you"
                  + (f". Budget {budget:.0f} s." if budget else "."))
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
left, right = st.columns([5, 2], gap="large")
with left:
    st.markdown(f"""<div class="mh{' compact' if ctx else ''}"><div class="kicker">Open-source agentic venture builder · Team Delulu</div>
<h1>From a founder's brief to a <em>tested</em> product, or an honest stop.</h1>
<p>Six gated phases with sourced evidence. Code decides every gate, you approve every external action,
publishing is stubbed and payments are mocked.</p></div>""".replace("{' compact' if ctx else ''}", ""), unsafe_allow_html=True)
with right:
    if ctx:
        budget = config.run_budget()
        st.markdown(f"""<div class="meta">RUN <b>{ctx.run_id}</b><br>LABEL <b>{ctx.label}</b><br>
STAGE <b>{ctx.stage}</b><br>AGENT TIME <b>{ctx.system_time_s:.0f} s</b>{f" / {budget:.0f} s" if budget else ""}<br>
VALIDATION <b>{ctx.validation_status}</b></div>""", unsafe_allow_html=True)
    else:
        st.markdown(f"""<div class="meta">MODEL <b>{model_line.replace("Model: ", "")}</b><br>
LOCAL <b>{ready}</b><br>RULES <b>approval-gated · mocked money</b></div>""", unsafe_allow_html=True)
if ctx:
    st.markdown(phase_strip(ctx), unsafe_allow_html=True)
if ctx and ctx.overridden:
    st.warning(f"{AMBER}: results after Phase {ctx.overrides[0]['phase']} are not validated by real evidence.")

# ------------------------------------------------------------------ brief form
if not ctx:
    st.markdown("## The founder brief")
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
        go = st.form_submit_button("Run the agents", disabled=no_key_wait, type="primary")
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
        st.markdown(verdict_block(ctx.final_outcome, "Run finished"), unsafe_allow_html=True)
        st.write("All files are listed in the **Files from this run** tab. Every agent action is in the **Decision log** tab.")
    elif kind in ("gate", "error"):
        outcome = pause.get("gate", {}).get("outcome") or pause.get("outcome")
        title = "Model or time-budget problem" if kind == "error" else f"Phase {pause.get('phase')} · {PHASES[pause.get('phase', 1) - 1]} gate"
        v_col, n_col = st.columns([3, 2], gap="large")
        with v_col:
            st.markdown(verdict_block(outcome, title), unsafe_allow_html=True)
            st.markdown(pause["verdict"])
        with n_col:
            nums = pause.get("gate", {}).get("numbers")
            if nums:
                st.table({"Measure": [k.replace("threshold_", "≥ ").replace("_", " ") for k in nums.keys()], "Value": [str(v) for v in nums.values()]})
        opts = pause["options"]
        help_txt = {"continue": "go to the next phase", "retry": "run this step again", "pivot": "go back and try the recommended alternative",
                    "override": "continue anyway; every later output is stamped UNVALIDATED", "stop": "end this run",
                    "enter_results": "enter experiment results again", "try_again": "repeat the failed model step",
                    "persevere": "keep going with this product"}
        st.markdown('<div class="small">' + "<br>".join(f"<b>{o.replace('_', ' ').title()}</b> — {help_txt.get(o, '')}" for o in opts) + "</div>",
                    unsafe_allow_html=True)
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
        st.markdown(verdict_block("awaiting_evidence", "Founder approval required").replace("Awaiting evidence", "Approve or reject"), unsafe_allow_html=True)
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
        st.markdown(f"## Phase {pause['phase']} — your input")
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
        with st.expander(f"{'final' if a_['status'] == 'final' else 'superseded'} · {name}"):
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
