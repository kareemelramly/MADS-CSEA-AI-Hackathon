#!/usr/bin/env bash
# Opens the app WITHOUT Docker: model on the GPU (host llama-server, no download) + Streamlit in a
# Python virtual environment. Open http://localhost:8501   Stop with Ctrl+C.
set -e
cd "$(dirname "$0")/.."
bash scripts/start_local_llm.sh
[ -d .venv ] || python3 -m venv .venv
source .venv/bin/activate
pip install -q -r requirements.txt
if [ -f .env ]; then set -a; source .env; set +a; fi
export LOCAL_BASE_URL="http://127.0.0.1:8080/v1" STATE_DIR="$PWD/state/ui" OUTPUTS_DIR="$PWD/state/ui/outputs" DECISION_LOG_PATH="$PWD/state/ui/ui_decision_log.json"
mkdir -p "$OUTPUTS_DIR"
echo "Open http://localhost:8501"
exec streamlit run app.py --server.port=8501 --server.address=127.0.0.1 --server.headless=true --browser.gatherUsageStats=false
