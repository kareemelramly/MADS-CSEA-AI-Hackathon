#!/usr/bin/env bash
# Checks that this computer can run the project. Changes nothing.   bash scripts/doctor.sh
cd "$(dirname "$0")/.."
ok(){ printf "  \033[32mOK\033[0m   %s\n" "$1"; }
bad(){ printf "  \033[31mFIX\033[0m  %s\n       -> %s\n" "$1" "$2"; FAIL=1; }
FAIL=0
echo "Checking your computer..."
if ! command -v docker >/dev/null; then bad "Docker not found" "sudo apt install -y docker.io docker-compose-v2"
elif docker --version 2>/dev/null | grep -qi podman || [ -f /usr/bin/podman ] && docker version 2>&1 | grep -qi podman; then
  bad "'docker' is really Podman (no GPU in containers, old compose)" "sudo apt remove -y podman-docker && sudo apt install -y docker.io docker-compose-v2"
else ok "Docker Engine installed"; fi
docker info >/dev/null 2>&1 && ok "Docker is running and you can use it" || bad "Docker not usable by your user" "Run: sudo systemctl start docker && sudo usermod -aG docker \$USER  (then log out and in)"
docker compose version 2>/dev/null | grep -qE "v2|version 2|v5|version 5" && ! docker compose version 2>&1 | grep -qi "external compose provider" && ok "Docker Compose v2" || bad "Docker Compose v2 missing" "sudo apt install -y docker-compose-v2"
if docker info 2>/dev/null | grep -qi nvidia || docker run --rm --gpus all ubuntu:22.04 nvidia-smi -L >/dev/null 2>&1; then ok "NVIDIA GPU available to Docker"; else bad "Docker cannot see the GPU" "Install the NVIDIA Container Toolkit: sudo apt install nvidia-container-toolkit && sudo nvidia-ctk runtime configure --runtime=docker && sudo systemctl restart docker"; fi
[ -f .env ] && ok ".env exists" || bad ".env missing" "Run: cp .env.example .env"
MODEL_DIR=$(grep -E '^LOCAL_MODEL_DIR=' .env 2>/dev/null | cut -d= -f2-); MODEL_DIR=${MODEL_DIR:-./models}
if ls "$MODEL_DIR"/*Q4_K_M*.gguf >/dev/null 2>&1; then
  ok "Model file found: $(ls "$MODEL_DIR"/*Q4_K_M*.gguf | head -1) (no download needed)"
else
  FOUND=$(ls "$HOME"/models/gemma4/*.gguf "$HOME"/models/*/*.gguf 2>/dev/null | head -1)
  if [ -n "$FOUND" ]; then
    bad "The model is not in $MODEL_DIR (the folder .env points to), but it exists at $FOUND" \
        "Run: sed -i 's|^LOCAL_MODEL_DIR=.*|LOCAL_MODEL_DIR=$(dirname "$FOUND")|' .env   (create .env first with: cp .env.example .env)"
    case "$(basename "$FOUND")" in *Q4_K_M*) ;; *) echo "       -> Also run: sed -i 's|^LOCAL_MODEL_FILE=.*|LOCAL_MODEL_FILE=$(basename "$FOUND")|' .env";; esac
  else
    bad "No .gguf model file found in $MODEL_DIR or ~/models" "Set LOCAL_MODEL_DIR in .env to the folder of your .gguf file (run: find ~ -name '*.gguf' 2>/dev/null)"
  fi
fi
command -v python3 >/dev/null && ok "python3 installed" || bad "python3 missing" "sudo apt install python3"
python3 -c "import venv, ensurepip" 2>/dev/null && ok "python3 venv available" || bad "python3 venv missing" "sudo apt install python3-venv"
for p in 8501 8081; do (ss -ltn 2>/dev/null | grep -q ":$p ") && bad "Port $p is busy" "Stop whatever uses it (docker compose down)" || ok "Port $p free"; done
FREE=$(df -Pk . | awk 'NR==2{print int($4/1024/1024)}'); [ "${FREE:-0}" -ge 10 ] && ok "${FREE} GB free disk" || bad "Only ${FREE} GB free" "Free at least 10 GB for Docker images"
echo; [ $FAIL = 0 ] && echo "All good." || echo "Fix the FIX lines above, then run this again."
exit $FAIL
