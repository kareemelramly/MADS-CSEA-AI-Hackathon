#!/usr/bin/env bash
# Start the local tier on the host: llama.cpp llama-server with Gemma 4 26B A4B Q4_K_M on a 16 GB GPU.
# Uses the GGUF already on disk; downloads nothing. Leaves the server running in the background.
# If the GPU is short on memory it retries with more expert layers on the CPU (slower but works).
LLAMA_BIN="${LLAMA_BIN:-$HOME/llama.cpp/build/bin/llama-server}"
MODEL="${LOCAL_GGUF:-$(ls "$HOME"/models/gemma4/*Q4_K_M*.gguf 2>/dev/null | head -1)}"
PORT="${LOCAL_PORT:-8080}"
DIR="$(cd "$(dirname "$0")/.." && pwd)/state"; mkdir -p "$DIR"
LOG="$DIR/llama-server.log"

if curl -sf "http://127.0.0.1:$PORT/health" >/dev/null 2>&1; then echo "Local model already running on port $PORT."; exit 0; fi
[ -x "$LLAMA_BIN" ] || { echo "llama-server not found at $LLAMA_BIN (set LLAMA_BIN)"; exit 1; }
[ -f "$MODEL" ] || { echo "No Q4_K_M .gguf found in ~/models/gemma4 (set LOCAL_GGUF)"; exit 1; }

# Free GPU memory held by an old copy of the server that no longer answers.
if pgrep -f "llama-server.*--port $PORT" >/dev/null; then
  echo "An old llama-server is not answering; stopping it."; pkill -f "llama-server.*--port $PORT"; sleep 3
fi

for CPU_MOE in 6 12 20 99; do
  echo "Starting the local model (expert layers on CPU: $CPU_MOE) ... first load takes up to a minute."
  nohup "$LLAMA_BIN" -m "$MODEL" -ngl 99 --n-cpu-moe "$CPU_MOE" -c 16384 -fa on \
    --cache-type-k q8_0 --cache-type-v q8_0 --jinja -np 1 --alias gemma-4-26b-a4b-it-q4_k_m \
    --host 127.0.0.1 --port "$PORT" >"$LOG" 2>&1 &
  PID=$!; echo $PID > "$DIR/llama-server.pid"
  for i in $(seq 1 180); do
    if curl -sf "http://127.0.0.1:$PORT/health" >/dev/null 2>&1; then echo "Local model ready after ${i}s."; exit 0; fi
    if ! kill -0 "$PID" 2>/dev/null; then break; fi
    sleep 1
  done
  kill "$PID" 2>/dev/null
  if grep -qi "out of memory" "$LOG"; then echo "GPU memory too small at this setting; trying with more layers on the CPU."; continue; fi
  echo "The local model did not start. Last lines of $LOG:"; tail -15 "$LOG"; exit 1
done
echo "The GPU has no free memory even with all expert layers on the CPU. Run: nvidia-smi   and close the programs listed there."
exit 1
