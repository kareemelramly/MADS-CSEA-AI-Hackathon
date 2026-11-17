"""Streamlit founder console (SRS 3.1, UI-1 to UI-10). One page on 127.0.0.1:8501.

The UI is a thin layer over the orchestrator. Agents run in a background thread, so clicking
anywhere while they work never interrupts a run; the page polls until the next founder decision.
The founder answers each pause with a button (`founder_action="button"`); approvals happen only
through the Approve button.
"""
import html
import json
import os
import threading
import time

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
PHASE_HELP = ["finds real people describing the problem and scores your idea",
              "designs the business and a test page to measure demand",
              "builds a small, tested product (a checklist pack)",
              "sets a price from real competitor prices and drafts policies",
              "drafts the store page and launch post; simulates a sale (MOCKED)",
              "writes a keep-going-or-change memo from real numbers"]
OUTCOME = {"go": ("var(--go)", "Good to continue"), "repeat": ("var(--repeat)", "Not enough information yet"),
           "pivot_back": ("var(--pivot)", "Try a different direction"), "stop": ("var(--stop)", "Recommendation: stop"),
           "awaiting_evidence": ("var(--await)", "Waiting for real results")}
GRAIN = ("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='160' height='160'><filter id='n'>"
         "<feTurbulence type='fractalNoise' baseFrequency='.9' numOctaves='2' stitchTiles='stitch'/></filter>"
         "<rect width='100%25' height='100%25' filter='url(%23n)' opacity='.55'/></svg>")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Instrument+Serif:ital@0;1&family=Space+Grotesk:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap');
:root{
  --ink:#0C0D0A; --ink-2:#15170F; --card:#1A1C14; --paper:#ECE8DC; --muted:#B3AE9F; --line:rgba(236,232,220,.14); --line-strong:rgba(236,232,220,.30);
  --accent:#E4FF4F; --go:#7FE3A5; --repeat:#F3C34E; --pivot:#86BEFF; --stop:#FF7262; --await:#C9C4B5;
  --serif:'Instrument Serif',Georgia,'Times New Roman',serif; --sans:'Space Grotesk',ui-sans-serif,system-ui,sans-serif;
  --mono:'IBM Plex Mono',ui-monospace,SFMono-Regular,Menlo,monospace;
}
html,body,.stApp,.stMarkdown,p,li,label,input,textarea,button{font-family:var(--sans)!important;}
.stApp{background:radial-gradient(1200px 600px at 85% -10%,rgba(228,255,79,.07),transparent 60%),
  radial-gradient(900px 500px at -10% 110%,rgba(134,190,255,.05),transparent 60%),var(--ink);}
.stApp::before{content:"";position:fixed;inset:0;pointer-events:none;background-image:url("GRAIN_URI");opacity:.06;mix-blend-mode:overlay;z-index:0;}
.block-container{padding-top:1.4rem;max-width:1180px;}
h1,h2,h3{font-family:var(--serif)!important;font-weight:400!important;letter-spacing:-.02em;line-height:1.08;color:var(--paper);}
h2{font-size:2.1rem!important;} h3{font-size:1.5rem!important;}
code,.mono{font-family:var(--mono)!important;font-size:.82em;}
section[data-testid="stSidebar"]{background:var(--ink-2);border-right:1px solid var(--line);}
[data-testid="stToolbar"],#MainMenu,[data-testid="stStatusWidget"]{visibility:hidden;}
[data-testid="stHeader"]{background:transparent;}
.mh{border-bottom:1px solid var(--line-strong);padding:0 0 16px;margin-bottom:8px;animation:rise .5s ease both;}
.mh .kicker{font-family:var(--mono);font-size:.72rem;letter-spacing:.18em;text-transform:uppercase;color:var(--accent);}
.mh h1{font-size:clamp(2rem,4.2vw,3.3rem);margin:.3rem 0 0;max-width:20ch;}
.mh h1 em{font-style:italic;color:var(--accent);}
.mh p{color:var(--muted);max-width:60ch;margin:.6rem 0 0;font-size:1.02rem;line-height:1.55;}
.mh.compact h1{font-size:clamp(1.5rem,2.4vw,2rem);max-width:none;} .mh.compact p{display:none;}
.steps{display:grid;grid-template-columns:repeat(3,1fr);border:1px solid var(--line);margin:18px 0 26px;}
.steps div{padding:16px 18px;border-right:1px solid var(--line);animation:rise .5s ease both;}
.steps div:nth-child(2){animation-delay:.08s} .steps div:nth-child(3){animation-delay:.16s;border-right:0;}
.steps b{display:block;font-family:var(--serif);font-weight:400;font-size:1.45rem;color:var(--paper);margin-bottom:4px;}
.steps span{font-family:var(--mono);font-size:.7rem;letter-spacing:.14em;color:var(--accent);}
.steps p{color:var(--muted);margin:4px 0 0;font-size:.93rem;line-height:1.5;}
.strip{display:grid;grid-template-columns:repeat(6,1fr);border:1px solid var(--line);margin:10px 0 18px;}
.strip div{padding:10px 12px;border-right:1px solid var(--line);font-size:.9rem;color:var(--muted);}
.strip div:last-child{border-right:0;}
.strip div span{display:block;font-family:var(--mono);font-size:.68rem;letter-spacing:.12em;}
.strip .done{color:var(--paper);} .strip .done span{color:var(--go);}
.strip .now{color:var(--ink);background:var(--accent);} .strip .now span{color:var(--ink);}
.card{border:1px solid var(--line);background:rgba(26,28,20,.65);padding:20px 22px;margin:6px 0 16px;animation:rise .45s ease both;}
.card .lbl{font-family:var(--mono);font-size:.72rem;letter-spacing:.16em;text-transform:uppercase;color:var(--muted);}
.card .big{font-family:var(--serif);font-size:clamp(1.7rem,3vw,2.5rem);line-height:1.05;color:var(--c,var(--paper));margin:.2rem 0 .4rem;}
.card p{color:var(--paper);font-size:1.02rem;line-height:1.6;margin:.4rem 0 0;}
.working{border:1px solid var(--accent);padding:18px 22px;margin:6px 0 14px;}
.working .big{font-family:var(--serif);font-size:1.9rem;color:var(--accent);}
.working .dots::after{content:"";animation:dots 1.4s steps(4,end) infinite;}
.feed{font-family:var(--mono);font-size:.8rem;color:var(--muted);line-height:1.9;margin-top:8px;}
.feed .ok{color:var(--go);} .feed .fb{color:var(--repeat);}
.chip{display:inline-block;font-family:var(--mono);font-size:.7rem;letter-spacing:.06em;border:1px solid var(--repeat);color:var(--repeat);padding:1px 8px;margin:0 6px 6px 0;}
.status{font-size:.92rem;line-height:1.6;color:var(--paper);} .status .dot{display:inline-block;width:9px;height:9px;border-radius:50%;margin-right:8px;}
.small{color:var(--muted);font-size:.9rem;line-height:1.55;}
.stButton>button,.stDownloadButton>button,[data-testid="stFormSubmitButton"]>button{border-radius:0!important;border:1px solid var(--line-strong)!important;
  background:transparent!important;color:var(--paper)!important;font-weight:500;min-height:3rem;transition:transform .12s ease,border-color .15s,background .15s;}
.stButton>button:hover,[data-testid="stFormSubmitButton"]>button:hover{border-color:var(--accent)!important;transform:translateY(-1px);}
.stButton>button[kind="primary"],[data-testid="stFormSubmitButton"]>button[kind="primaryFormSubmit"]{background:var(--accent)!important;color:var(--ink)!important;border-color:var(--accent)!important;font-weight:600;}
.stButton>button:focus-visible,input:focus-visible,textarea:focus-visible{outline:2px solid var(--accent)!important;outline-offset:2px;}
input,textarea,[data-baseweb="select"]>div{border-radius:0!important;}
[data-testid="stForm"]{border-radius:0!important;border:1px solid var(--line)!important;background:rgba(21,23,15,.55);}
[data-testid="stTable"] td{font-family:var(--mono);font-size:.86rem;}
[data-testid="stExpander"]{border:1px solid var(--line)!important;border-radius:0!important;}
[data-testid="stAlert"]{border-radius:0!important;background:transparent!important;border:1px solid var(--line)!important;border-left:3px solid var(--accent)!important;}
[data-testid="stAlert"] > div,[data-testid="stAlertContainer"]{background:transparent!important;}
[data-testid="stAlert"] p{color:var(--paper)!important;}
.stTabs [data-baseweb="tab"]{font-family:var(--mono);font-size:.78rem;letter-spacing:.1em;text-transform:uppercase;}
.stTabs [aria-selected="true"]{color:var(--accent)!important;} .stTabs [data-baseweb="tab-highlight"]{background:var(--accent)!important;}
.paper{background:#F7F4EA;color:#1C1C17;padding:22px 26px;border:1px solid #d9d4c4;font-size:.98rem;line-height:1.6;}
.paper h1,.paper h2,.paper h3{color:#1C1C17!important;font-family:var(--serif)!important;}
@media (max-width:760px){.steps,.strip{grid-template-columns:1fr 1fr;} .steps div{border-right:0;border-bottom:1px solid var(--line);}}
@keyframes rise{from{opacity:0;transform:translateY(8px);}to{opacity:1;transform:none;}}
@keyframes dots{0%{content:"";}25%{content:".";}50%{content:"..";}75%{content:"...";}}
@media (prefers-reduced-motion:reduce){*{animation:none!important;transition:none!important;}}
</style>""".replace("GRAIN_URI", GRAIN), unsafe_allow_html=True)


# ------------------------------------------------------------------ background runs
@st.cache_resource
def _jobs():
    return {}


def start_job(ctx):
    job = {"lines": [], "done": False, "pause": None, "error": None, "ctx": ctx, "started": time.time()}

    def work():
        try:
            job["pause"] = orchestrator.run_until_gate(ctx, lambda ev: job["lines"].append(ev))
        except Exception as e:  # noqa: BLE001 - shown to the founder, never swallowed
            job["error"] = f"{type(e).__name__}: {e}"
        finally:
            job["done"] = True
    _jobs()[ctx.run_id] = job
    threading.Thread(target=work, daemon=True).start()
    st.session_state["job"] = ctx.run_id
    st.session_state["ctx_json"] = ctx.to_json()


def collect_job():
    """Returns True while the agents are still working."""
    rid = st.session_state.get("job")
    if not rid:
        return False
    job = _jobs().get(rid)
    if not job:
        st.session_state.pop("job", None)
        return False
    if not job["done"]:
        return True
    st.session_state["ctx_json"] = job["ctx"].to_json()
    st.session_state["pause"] = job["pause"] or {"kind": "error", "phase": 1, "outcome": "repeat", "options": ["try_again", "stop"],
                                                  "id": "err.ui", "verdict": f"Something went wrong: {job['error']}. Nothing was decided."}
    _jobs().pop(rid, None)
    st.session_state.pop("job", None)
    return False


def friendly(ev):
    who = ev.get("agent", "agent").replace("_", " ")
    where = "the local model" if ev.get("tier") == "local" else "NVIDIA's model"
    stt = ev.get("status")
    if stt == "ok":
        return f'<span class="ok">done</span> · {who} finished (via {where}, {ev.get("elapsed_s")} s)'
    if stt == "fallback":
        return f'<span class="fb">switching</span> · {who}: {where} unavailable, using the local model'
    if stt == "trying":
        return f"working · {who} is thinking (via {where})"
    return f"{stt} · {who}"


# ------------------------------------------------------------------ state
working = collect_job()
ctx = RunContext.from_json(st.session_state["ctx_json"]) if "ctx_json" in st.session_state else None
tiers = llm.status()
ready, detail = llm.local_ready()
remote_on = any(t["has_key"] and t["name"] != "local" and not t["disabled"] for t in tiers)
model_line = "Model: NVIDIA Gemma 4 31B first, local Gemma 4 as backup" if remote_on else "Model: local Gemma 4 26B (on this computer)"
local_line = {"ready": "Local model: ready", "loading": "Local model: still loading, please wait a minute",
              "unreachable": "Local model: not running yet. Start it with: bash scripts/start_app_nodocker.sh"}[ready]

# ------------------------------------------------------------------ sidebar (essentials only)
with st.sidebar:
    st.markdown("### Status")
    st.info(model_line)
    (st.success if ready == "ready" else st.warning)(local_line)
    st.markdown('<span class="chip">PUBLISHING · STUBBED</span><span class="chip">PAYMENTS · MOCKED</span>'
                '<span class="chip">PERSONAS · SIMULATED</span>', unsafe_allow_html=True)
    st.markdown('<div class="small">Nothing is posted, sent or charged. Every outside action needs your approval.</div>',
                unsafe_allow_html=True)
    if ctx and not working:
        st.write("")
        if st.button("Start a new idea", use_container_width=True):
            for k in ("ctx_json", "pause", "job"):
                st.session_state.pop(k, None)
            st.rerun()

# ------------------------------------------------------------------ masthead
st.markdown(f"""<div class="mh{' compact' if ctx else ''}"><div class="kicker">Open-source agentic venture builder · Team Delulu</div>
<h1>From an idea to a <em>tested</em> digital product, or an honest stop.</h1>
<p>Describe your idea. A team of AI agents researches it, builds it and prepares the launch, and stops at every
checkpoint so you decide. If the evidence is weak, it tells you to stop.</p></div>""", unsafe_allow_html=True)


def strip(ctx):
    cur = int(ctx.stage[1]) if ctx.stage.startswith("p") else 7
    cells = []
    for i, name in enumerate(PHASES, 1):
        cls = "done" if i < cur or (ctx.finished and i <= cur) else ("now" if i == cur and not ctx.finished else "")
        mark = "DONE" if cls == "done" else ("NOW" if cls == "now" else f"STEP {i}")
        cells.append(f'<div class="{cls}"><span>{mark}</span>{name}</div>')
    return '<div class="strip">' + "".join(cells) + "</div>"


def card(kicker, title, color, body=""):
    st.markdown(f'<div class="card" style="--c:{color}"><div class="lbl">{kicker}</div><div class="big">{title}</div>'
                f'{"<p>" + body + "</p>" if body else ""}</div>', unsafe_allow_html=True)


# ------------------------------------------------------------------ home: brief form
if not ctx:
    st.markdown("""<div class="steps">
<div><span>STEP 1</span><b>Describe your idea</b><p>Pick an example below or write your own: the idea, your skills, budget and time.</p></div>
<div><span>STEP 2</span><b>Agents do the work</b><p>Six phases: research, validation, build, pricing, launch, learning. Each one ends at a checkpoint.</p></div>
<div><span>STEP 3</span><b>You decide</b><p>At every checkpoint you read a plain verdict and press a button. Nothing goes out without you.</p></div>
</div>""", unsafe_allow_html=True)
    st.markdown("## Your idea")
    fx = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tests", "fixtures")
    choices = {"Notion templates for wedding planners (a reasonable idea: goes through all six phases)": "r",
               "A habit-tracking app by a founder with no matching skills (a weak idea: expect a stop)": "w",
               "A crypto trading signal bot (not allowed: stops immediately)": "e", "Write my own idea": ""}
    pick = st.radio("Start from an example", list(choices.keys()))
    code = choices[pick]
    d = {}
    if code:
        d = json.load(open(os.path.join(fx, f"brief_{code}.json"), encoding="utf-8"))
        d.pop("founder_inputs", None)
    with st.form("brief"):
        idea = st.text_area("Idea", d.get("idea", ""), height=80, help="One or two sentences: what you want to sell, and to whom.")
        c1, c2 = st.columns(2)
        skills = c1.text_input("Your skills", d.get("skills", ""))
        values = c2.text_input("Your values", d.get("values", ""), help="What you will not compromise on, e.g. honesty, privacy.")
        b1, b2, b3 = st.columns(3)
        budget = b1.number_input("Budget", min_value=0, value=int(d.get("budget_amount", 0)))
        cur = b2.text_input("Currency", d.get("budget_currency", "USD"))
        hours = b3.number_input("Hours per week you can spend", min_value=0, value=int(d.get("hours_per_week", 0)))
        m1, m2 = st.columns(2)
        market = m1.text_input("Who it is for", d.get("target_market", ""))
        countries = m2.text_input("Countries", d.get("countries", ""))
        with st.expander("Optional details"):
            terms = st.text_input("Search words the agents should use", d.get("search_terms", ""))
            e1, e2 = st.columns(2)
            ev_url = e1.text_input("A link that shows people have this problem")
            ev_claim = e2.text_input("What that link shows, in one line")
            label = st.text_input("Run name (a short tag added to every file name, e.g. r)", code or "mine", max_chars=8)
        no_model = not remote_on and ready != "ready"
        go = st.form_submit_button("Start the agents", disabled=no_model, type="primary", use_container_width=True)
        if no_model:
            st.caption("The button unlocks when the local model is ready (see Status on the left).")
    if go:
        brief = {"idea": idea, "skills": skills, "budget_amount": budget, "budget_currency": cur, "hours_per_week": hours,
                 "target_market": market, "countries": countries, "values": values}
        if terms:
            brief["search_terms"] = terms
        if ev_url:
            brief["founder_evidence"] = [{"url": ev_url, "claim": ev_claim}]
        start_job(orchestrator.new_run(brief, label or "mine"))
        st.rerun()
    with st.expander("Try to make the system break a rule"):
        req = st.text_input("Ask for something", key="req", placeholder="e.g. write 50 five-star reviews")
        if st.button("Check request") and req:
            r = guardrails.check_request(req)
            if r:
                logmod.log("guardrails", "guardrail_refusal", run_id=None, rule=r.rule, match=r.match, where="founder_request")
                st.error(f"Refused ({r.rule.replace('_', ' ')}). This system never fakes reviews or sign-ups, promises income, "
                         "adds false urgency, impersonates anyone, moves money or skips its checks.")
            else:
                st.success("Allowed: this does not break a rule. Anything that goes outside still needs your approval.")
    st.stop()

# ------------------------------------------------------------------ run view
st.markdown(strip(ctx), unsafe_allow_html=True)
if ctx.overridden:
    st.warning(f"{AMBER}: you chose to continue without real evidence after Phase {ctx.overrides[0]['phase']}. "
               "Every file from here on is stamped as unvalidated.")

if working:
    @st.fragment(run_every=1.5)
    def progress():
        if not collect_job():
            st.rerun(scope="app")
        job = _jobs().get(st.session_state.get("job"), {})
        c = job.get("ctx") or ctx
        cur = int(c.stage[1]) if c.stage.startswith("p") else 6
        lines = [friendly(ev) for ev in job.get("lines", []) if ev.get("status") in ("ok", "fallback")][-8:]
        st.markdown(f"""<div class="working"><div class="big">The agents are working<span class="dots"></span></div>
<div class="small">Phase {cur} · {PHASES[cur - 1]}: the agent {PHASE_HELP[cur - 1]}. This usually takes under a minute.
You do not need to do anything; this page updates by itself.</div>
<div class="feed">{"<br>".join(lines) or "starting…"}</div></div>""", unsafe_allow_html=True)
    progress()
    st.stop()

pause = st.session_state.get("pause") or ctx.data.get("pause") or {"kind": "done" if ctx.finished else "none"}


def answer(ans):
    try:
        orchestrator.respond(ctx, ans, "button")
    except (approval.ApprovalError, ValueError) as e:
        st.error(f"Not accepted: {e}")
        return
    st.session_state.pop("pause", None)
    start_job(ctx)
    st.rerun()


def option_label(o, phase):
    nxt = PHASES[phase] if phase and phase < 6 else ""
    return {"continue": f"Continue to {nxt}" if nxt else "Continue", "retry": "Try this step again",
            "pivot": "Switch to the suggested alternative" if phase != 6 else "Pivot to something else",
            "override": "Continue anyway (I accept the risk)", "stop": "Stop here", "enter_results": "Enter experiment results",
            "try_again": "Try again", "persevere": "Keep going (persevere)"}.get(o, o.replace("_", " ").title())


tab_run, tab_files, tab_log = st.tabs(["Your decision", "Documents created", "Activity log"])
with tab_run:
    kind = pause["kind"]
    if kind == "none":
        if st.button("Continue", type="primary"):
            start_job(ctx)
            st.rerun()
    elif kind == "done":
        c, word = OUTCOME.get(ctx.final_outcome, ("var(--paper)", str(ctx.final_outcome)))
        card("Run finished", word, c, "Everything the agents produced is in <b>Documents created</b>; every step they took is in <b>Activity log</b>.")
    elif kind in ("gate", "error"):
        phase = pause.get("phase") or 1
        outcome = pause.get("gate", {}).get("outcome") or pause.get("outcome")
        c, word = OUTCOME.get(outcome, ("var(--paper)", str(outcome)))
        kicker = "Something went wrong, nothing was decided" if kind == "error" else f"Checkpoint · Phase {phase} · {PHASES[phase - 1]}"
        card(kicker, word, c, html.escape(pause["verdict"]))
        nums = pause.get("gate", {}).get("numbers")
        if nums:
            with st.expander("See the numbers behind this verdict"):
                st.table({"Measure": [k.replace("threshold_", "required: ").replace("_", " ") for k in nums.keys()],
                          "Value": [str(v) for v in nums.values()]})
        opts = pause["options"]
        st.markdown("### What do you want to do?")
        reason, exp_price = "", 0.0
        if "override" in opts:
            reason = st.text_area("Only if you continue anyway: say why, in at least 20 characters", key=f"r_{pause['id']}")
            if phase == 4:
                exp_price = st.number_input("Experimental price in USD (marked ASSUMPTION)", min_value=0.0, value=0.0)
        cols = st.columns(len(opts))
        for i, o in enumerate(opts):
            if cols[i].button(option_label(o, phase), key=f"{pause['id']}_{o}", use_container_width=True,
                              type="primary" if i == 0 else "secondary"):
                ans = {"choice": o}
                if o == "override":
                    ans["reason"] = reason
                    if phase == 4:
                        ans.update(experimental_price=exp_price, currency="USD")
                answer(ans)
    elif kind == "approval":
        what = {"publish_landing_page": "publish the test landing page", "release_product": "release the finished product to the next phase",
                "commercial_setup": "accept the price and the draft policies", "publish_store_page": "publish the store page",
                "post_launch_message": "post the launch message", "send_support_reply": "send a support reply"}.get(pause["action"], pause["action"])
        card("Your approval is needed", f"Allow the agents to {what}?", "var(--accent)",
             "Nothing happens unless you press Approve. This is a demo: publishing and posting are STUBBED (only written to the log), "
             "and no money ever moves. Your approval covers exactly the content below; if anything changes, you will be asked again.")
        st.table({"Field": ["Action", "Destination", "Amount", "Run ID", "Content SHA-256"],
                  "Value": [pause["action"], pause["destination"], f"{pause['amount_minor']} {pause['currency']} (no money moves)",
                            pause["run_id"], pause["content_sha256"]]})
        st.markdown("#### What you are approving")
        if pause["action"] == "publish_landing_page":
            st.components.v1.html(pause["content"], height=460, scrolling=True)
        elif pause["action"] in ("publish_store_page", "post_launch_message"):
            with st.container(border=True):
                st.markdown(pause["content"])
        else:
            try:
                st.json(json.loads(pause["content"]), expanded=1)
            except ValueError:
                st.code(pause["content"][:6000], language=None)
        a, r = st.columns(2)
        if a.button("Approve", key=pause["id"] + "_a", type="primary", use_container_width=True):
            answer({"choice": "approve"})
        if r.button("Reject", key=pause["id"] + "_r", use_container_width=True):
            answer({"choice": "reject"})
    elif kind == "input":
        form = pause["form"]
        titles = {"real_counts": "Did you run the landing-page test?", "persona_test": "Run a quick simulated reaction test?",
                  "price_quotes": "What do competitors charge?", "mock_sale": "Simulate a sale (MOCKED)",
                  "targets": "Set your goals before seeing any numbers", "metrics": "Any real numbers since launch?"}
        card(f"Phase {pause['phase']} · {PHASES[pause['phase'] - 1]} · your input", titles.get(form, "Your input"), "var(--paper)", html.escape(pause.get("help", "")))
        if form == "real_counts":
            with st.form("counts"):
                status = st.selectbox("Status of the test", ["not_started", "running", "completed", "abandoned"],
                                      format_func=lambda x: {"not_started": "I have not run it yet", "running": "It is running now",
                                                             "completed": "It is finished", "abandoned": "I stopped it early"}[x])
                s1, s2 = st.columns(2)
                started, ended = s1.text_input("Started on (date)"), s2.text_input("Ended on (date)")
                vis = st.text_input("Real visitors (leave blank if you do not know)")
                sig = st.number_input("Real sign-ups", min_value=0, value=0)
                st.caption("Only real numbers. Simulated numbers can never be entered here.")
                if st.form_submit_button("Submit real results", type="primary"):
                    answer({"experiment_status": status, "started_at": started or None, "ended_at": ended or None,
                            "visitors": int(vis) if vis.strip().isdigit() else None, "signups": int(sig)})
        elif form == "persona_test":
            c1, c2 = st.columns(2)
            if c1.button("Yes, run the simulated test", type="primary", use_container_width=True):
                answer({"run": True})
            if c2.button("No, skip it", use_container_width=True):
                answer({"run": False})
        elif form == "price_quotes":
            st.caption("One competitor per line: name | link | price | currency | kind (one_time, subscription or free). "
                       "Each link is opened; a link that does not load is not counted.")
            demo = ""
            if ctx.label == "r":
                b = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "tests", "fixtures", "brief_r.json"), encoding="utf-8"))
                demo = "\n".join(f"{q['name']} | {q['url']} | {q['amount']} | {q['currency']} | {q['kind']}" for q in b["founder_inputs"]["p4_quotes"])
            txt = st.text_area("Competitor prices", value=demo, height=170)
            if st.button("Submit prices", type="primary"):
                qs = []
                for line in txt.splitlines():
                    p = [x.strip() for x in line.split("|")]
                    if len(p) == 5:
                        try:
                            amt = float(p[2])
                            qs.append({"name": p[0], "url": p[1], "amount": amt, "currency": p[3].upper(), "kind": p[4],
                                       "display": f"${amt:g}" if p[3].upper() == "USD" else p[2]})
                        except ValueError:
                            pass
                answer({"quotes": qs})
        elif form == "mock_sale":
            sp = st.checkbox("Simulate one purchase (MOCKED, no money moves)", value=True)
            sr = st.checkbox("Then simulate a refund (MOCKED)", value=True)
            if st.button("Run the simulated sale", type="primary"):
                answer({"simulate_purchase": sp, "simulate_refund": sr})
        elif form == "targets":
            c1, c2 = st.columns(2)
            t1 = c1.number_input("Goal: waitlist sign-ups", min_value=0, value=100)
            t2 = c2.number_input("Goal: paying customers", min_value=0, value=5)
            if st.button("Lock these goals", type="primary"):
                answer({"targets": {"waitlist_signups": t1, "paying_customers": t2}})
        elif form == "metrics":
            st.caption("One per line: name | number | link that proves it. Numbers without a link count as SIMULATED, not real.")
            txt = st.text_area("Real numbers (leave empty if you have none)")
            if st.button("Submit", type="primary"):
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
        st.write("No documents yet.")
    for a_ in reversed(ctx.artifacts):
        path = os.path.join(root, a_["path"])
        name = os.path.basename(path)
        with st.expander(f"{name}{'' if a_['status'] == 'final' else '  (older version)'}"):
            try:
                body = open(path, encoding="utf-8").read()
            except OSError:
                continue
            if name.endswith(".md"):
                with st.container(border=True):
                    st.markdown(body)
            elif name.endswith(".html"):
                st.components.v1.html(body, height=380, scrolling=True)
            elif name.endswith(".json"):
                st.json(json.loads(body), expanded=1)
            else:
                st.code(body[:5000], language=None)
            st.download_button("Download", body, file_name=name, key="dl_" + name)

with tab_log:
    rows = logmod.entries(run_id=ctx.run_id)
    if rows:
        st.dataframe([{k: (json.dumps(v) if isinstance(v, (list, dict)) else v) for k, v in r.items()
                       if k in ("timestamp", "agent", "action", "model", "cost", "approved_by", "outcome")} for r in rows],
                     use_container_width=True, hide_index=True)
