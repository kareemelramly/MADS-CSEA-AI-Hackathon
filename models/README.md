Put the local model file here (or set LOCAL_MODEL_DIR in .env to the folder that holds it):

    gemma-4-26B-A4B-it-UD-Q4_K_M.gguf

When the file is present, `docker compose up` loads it and downloads nothing. When it is missing, the
`llm` container downloads `unsloth/gemma-4-26B-A4B-it-GGUF:UD-Q4_K_M` once into a Docker volume.
.gguf files are ignored by git.
