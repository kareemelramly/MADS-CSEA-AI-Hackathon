#!/usr/bin/env bash
# Produces the committed demo results (outputs/, decision_log.json, docs/) from REAL runs.
# Run from the repo folder:   bash scripts/demo_runs.sh
# It never commits or pushes. You answer every question yourself; this file tells you what to type.
set -uo pipefail
cd "$(dirname "$0")/.."
ROOT="$(pwd)"
B="\033[1m"; G="\033[32m"; Y="\033[33m"; R="\033[31m"; X="\033[0m"
step(){ printf "\n${B}━━━ %s ━━━${X}\n" "$1"; }
tip(){ printf "${Y}%s${X}\n" "$1"; }
die(){ printf "${R}%s${X}\n" "$1"; exit 1; }

step "Step 1 of 8 · Find or start the local model (no download)"
if curl -sf http://127.0.0.1:8081/health >/dev/null 2>&1; then
  LOCAL_URL="http://127.0.0.1:8081/v1"; echo "Using the model already running inside docker compose (port 8081)."
else
  LOCAL_URL="http://127.0.0.1:8080/v1"
  bash scripts/start_local_llm.sh || die "The local model did not start. Open state/llama-server.log and send me its last lines."
fi

step "Step 2 of 8 · Prepare Python (first time takes about a minute)"
if [ ! -d .venv ]; then python3 -m venv .venv || die "Run: sudo apt install python3-venv   then run this script again."; fi
# shellcheck disable=SC1091
source .venv/bin/activate
pip install -q -r requirements.txt || die "pip install failed; check your internet connection."

step "Step 3 of 8 · Automatic tests (no internet, no keys)"
python -m pytest -q || die "Some tests failed. Copy the lines starting with FAILED and send them to me."

step "Step 4 of 8 · Check the free remote models with your .env keys"
python scripts/check_keys.py

step "Step 5 of 8 · Check that the local model answers in valid JSON (about 3 minutes)"
if [ -f model_check_result.json ] && grep -q '"correctness": "pass"' model_check_result.json; then
  echo "Already passed earlier: $(grep -E 'valid|avg_tokens' model_check_result.json | tr -d '\n ')"
elif ! python scripts/model_check.py "$LOCAL_URL"; then
  tip "The local model failed the 9-out-of-10 check (details in model_check_result.json)."
  read -r -p "Continue anyway? Bad answers become an honest 'repeat'. Type y or n: " ans
  [ "$ans" = "y" ] || exit 1
fi

curl -sf "${LOCAL_URL%/v1}/health" >/dev/null 2>&1 || { tail -25 state/llama-server.log 2>/dev/null; die "The local model server is not running (log above). Send Claude the lines above."; }

step "Step 6 of 8 · Clear old results (moved to state/, nothing is deleted)"
STAMP=$(date -u +%Y%m%dT%H%M%SZ)
mkdir -p "state/previous_outputs_$STAMP"
find outputs -maxdepth 1 -type f ! -name .gitkeep -exec mv {} "state/previous_outputs_$STAMP/" \;
[ -f decision_log.json ] && cp decision_log.json "state/previous_outputs_$STAMP/"
if [ -f .env ]; then set -a; source .env; set +a; fi
export STATE_DIR="$ROOT/state" OUTPUTS_DIR="$ROOT/outputs" DECISION_LOG_PATH="$ROOT/decision_log.json"
export LOCAL_BASE_URL="$LOCAL_URL"
python -c "import log; log.reset()"

step "Step 7 of 8 · Three demo runs (you answer the questions)"
printf "${B}Run W: weak idea (habit app, founder with no matching skills).${X}\n"
tip "  Follow the green line that starts with → at every question."
python -m orchestrator --brief tests/fixtures/brief_w.json --label w

printf "\n${B}Run E: excluded idea (crypto signal bot). No questions: it must stop by itself.${X}\n"
python -m orchestrator --brief tests/fixtures/brief_e.json --label e

printf "\n${B}Run R: reasonable idea (Notion templates for wedding planners), all six phases.${X}\n"
tip "  Follow the green line that starts with → at every question (about 15 questions)."
tip "  When asked for an override reason, just press Enter to use the prepared one."
python -m orchestrator --brief tests/fixtures/brief_r.json --label r

step "Step 8 of 8 · Payment test log, run index, cost report, final checks"
python scripts/payment_test_run.py > /dev/null && echo "payment_test_log.md written (all MOCKED)"
python scripts/index_runs.py
python scripts/cost_per_run.py > /dev/null && echo "docs/cost_report.md written; README cost and speed lines updated"
python scripts/check_outputs.py --all
python scripts/check_docs.py

printf "\n${G}${B}Finished.${X} Tell Claude \"done\" so it can review outputs/, decision_log.json and docs/.\n"
printf "Nothing was committed or pushed.\n"
