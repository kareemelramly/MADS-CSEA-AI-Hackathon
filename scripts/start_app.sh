#!/usr/bin/env bash
# One command on the team laptop: starts the model on the GPU (host llama-server, no download)
# and the app in Docker. Then open http://localhost:8501      Stop with Ctrl+C.
set -e
cd "$(dirname "$0")/.."
bash scripts/start_local_llm.sh
echo "Starting the app in Docker... open http://localhost:8501 when you see 'You can now view your Streamlit app'."
docker compose -f docker-compose.yml -f docker-compose.host-llm.yml up --build app
