Put a local model file here (or set LOCAL_MODEL_DIR in .env to the folder that holds it):

    Qwen3-4B-Instruct-2507-Q4_K_M.gguf      default for `docker compose up` (runs on a laptop CPU)
    gemma-4-26B-A4B-it-UD-Q4_K_M.gguf       GPU override: docker compose -f docker-compose.yml -f docker-compose.gpu.yml up

When the file is present, the `llm` container loads it and downloads nothing. When it is missing, it
downloads the default (`unsloth/Qwen3-4B-Instruct-2507-GGUF:Q4_K_M`, or Gemma with the GPU override)
once into a Docker volume. .gguf files are ignored by git.
