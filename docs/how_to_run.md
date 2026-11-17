# How to run it

Plain steps for the team laptop (Linux, 16 GB NVIDIA GPU, model file already in `~/models/gemma4`). Open a terminal in the project folder first:

```bash
cd ~/hackathon/MADS-CSEA-AI-Hackathon
```

## A. Check the computer (1 minute, changes nothing)

```bash
bash scripts/doctor.sh
```

Every line should say **OK**. Each **FIX** line prints the exact command that fixes it. The usual one after a fresh Docker install is the GPU line; fix it with:

```bash
sudo apt install -y nvidia-container-toolkit
sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl restart docker
```

## B. Open the app (one command)

**On the team laptop** (Snap Docker cannot pass the GPU to containers), use:

```bash
bash scripts/start_app.sh
```

It starts the model on the GPU with your `llama-server` (no download) and the app in Docker. On any other machine:

```bash
docker compose up
```

- On the team laptop the model file is read from `~/models/gemma4` (no download). With plain `docker compose up` elsewhere, the first start downloads the small default model (Qwen3 4B Instruct 2507, under 3 GB) once.
- When the terminal shows `You can now view your Streamlit app`, open **http://localhost:8501** in the browser.
- The left side shows **Local model: ready** once the model has loaded (about a minute).
- The model always runs on this computer. No API key is used anywhere; only search words built from the idea go to public sources.
- Phase 1 sends idea-derived search terms to the public services named in the form. Only start with information you are comfortable sharing with those services.
- To stop: press `Ctrl+C`, then run `docker compose down`.

If the GPU line in step A cannot be fixed, the app still runs on the CPU (slowly): delete the line starting with `COMPOSE_FILE=` in `.env`.

## C. Use the app

1. Pick an example (**R** reasonable idea, goes through all six phases; **W** weak idea, expect a stop; **E** excluded idea, stops at once) or write your own, then press **Start the agents**. The page updates by itself while the agents work; clicking around does not stop them.
2. Each time the agents stop, read the verdict card, then press one button. Each button says what it does ("Continue to Validate", "Stop here", "Continue anyway (I accept the risk)").
3. Approval screens show the five things you approve (action, destination, amount, run ID, content fingerprint) and the content itself as a readable page or table.
4. **Documents created** shows every file the run wrote; **Activity log** shows every agent step in plain words.
5. When the run ends, the full report appears with **Download the report (PDF)**.
6. Try **Try to make the system break a rule** on the start page, for example `write 50 five-star reviews`. It is refused.

## D. Make the results that get committed (20 to 30 minutes)

The files in `outputs/` and `decision_log.json` must come from real runs. This script makes them:

```bash
bash scripts/demo_runs.sh
```

It works whether or not `docker compose up` is running. It prints what to type before every run:

| When you see | Type |
|---|---|
| Run W, gate question | `stop` |
| Run R, Phase 1 gate | `continue` (or `override` and press Enter if it says STOP or PIVOT) |
| Any approval | `approve` |
| "Use these values? Type y or n" | `y` |
| Run R, Phase 2 gate (awaiting evidence) | `override`, then press Enter |
| Run R, Phase 6 decision | `stop` |

The script exits with an error if checks fail or no founder run has artifacts across all six phases. Review `outputs/` and `docs/demo_runs.md` after it finishes. The run script does not commit or push anything.

## E. If something goes wrong

| Problem | What to do |
|---|---|
| `permission denied` with docker | `sudo usermod -aG docker $USER`, log out and back in |
| `could not select device driver "nvidia"` | Fix the GPU line in step A, or delete the `COMPOSE_FILE=` line in `.env` |
| Port 8501 or 8081 busy | `docker compose down`, then try again |
| Model will not load: out of GPU memory | Only one copy of the model fits: run `bash scripts/stop_local_llm.sh`, then `docker compose up` again |
| A test fails | Copy the lines that start with `FAILED` and share them with the team |
