#!/usr/bin/env bash
# Stops the host llama-server started by scripts/start_local_llm.sh (frees the GPU for docker compose up).
cd "$(dirname "$0")/.."
if [ -f state/llama-server.pid ] && kill "$(cat state/llama-server.pid)" 2>/dev/null; then
  rm -f state/llama-server.pid; echo "Host llama-server stopped."
else
  pkill -f "llama-server.*--port 8080" && echo "Host llama-server stopped." || echo "No host llama-server was running."
fi
