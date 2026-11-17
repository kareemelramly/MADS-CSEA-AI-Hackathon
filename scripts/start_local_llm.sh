#!/usr/bin/env bash
# Start the local tier on the host: llama.cpp llama-server with Gemma 4 26B A4B Q4_K_M on a 16 GB GPU.
# Uses the GGUF already on disk; downloads nothing. Leaves the server running in the background.
set -euo pipefail
LLAMA_BIN="${LLAMA_BIN:-$HOME/llama.cpp/build/bin/llama-server}"
MODEL="${LOCAL_GGUF:-$(ls "$HOME"/models/gemma4/*Q4_K_M*.gguf 2>/dev/null | head -1)}"
PORT="${LOCAL_PORT:-8080}"
LOG="${LLAMA_LOG:-$(dirname "$0")/../state/llama-server.log}"
mkdir -p "$(dirname "$LOG")"

if curl -sf "http://127.0.0.1:$PORT/health" >/dev/null 2>&1; then
  echo "llama-server already answering on 127.0.0.1:$PORT"; exit 0
fi
[ -x "$LLAMA_BIN" ] || { echo "llama-server not found at $LLAMA_BIN (set LLAMA_BIN)"; exit 1; }
[ -f "$MODEL" ] || { echo "No Q4_K_M .gguf found in ~/models/gemma4 (set LOCAL_GGUF)"; exit 1; }

echo "Starting llama-server with $MODEL (log: $LOG)"
nohup "$LLAMA_BIN" -m "$MODEL" \
  -ngl 99 --n-cpu-moe 6 \
  -c 16384 -fa on \
  --cache-type-k q8_0 --cache-type-v q8_0 \
  --jinja -np 1 --alias gemma-4-26b-a4b-it-q4_k_m \
  --host 127.0.0.1 --port "$PORT" >"$LOG" 2>&1 &
echo $! > "$(dirname "$LOG")/llama-server.pid"

for i in $(seq 1 180); do
  if curl -sf "http://127.0.0.1:$PORT/health" >/dev/null 2>&1; then echo "ready after ${i}s"; exit 0; fi
  sleep 1
done
echo "llama-server did not become ready in 180 s; see $LOG"; exit 1
