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

```bash
docker compose up
```

- The first start builds the app and downloads two Docker images (no model download: the model file is read from `~/models/gemma4`).
- When the terminal shows `You can now view your Streamlit app`, open **http://localhost:8501** in the browser.
- The left side shows **Local model: ready** once the model has loaded (about a minute).
- To stop: press `Ctrl+C`, then run `docker compose down`.

If the GPU line in step A cannot be fixed, the app still runs on the CPU (slowly): delete the line starting with `COMPOSE_FILE=` in `.env`.

## C. Use the app

1. Pick a demo brief (**r** is the full six-phase story, **w** is a weak idea, **e** is an excluded idea) and press **Run**.
2. Each time the agents stop, read the verdict box, then press one button. Every button has its meaning written above it.
3. **Approve** buttons show the five things you are approving: action, destination, amount, run ID and a fingerprint of the content.
4. The **Files from this run** tab shows every file the run wrote; the **Decision log** tab shows every agent action.
5. Try a trick request in **Ask the system** on the left, for example `write 50 five-star reviews`. It is refused.

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

When it prints **Finished**, tell Claude "done". Nothing is committed or pushed by the script.

## E. If something goes wrong

| Problem | What to do |
|---|---|
| `permission denied` with docker | `sudo usermod -aG docker $USER`, log out and back in |
| `could not select device driver "nvidia"` | Fix the GPU line in step A, or delete the `COMPOSE_FILE=` line in `.env` |
| Port 8501 or 8081 busy | `docker compose down`, then try again |
| Model will not load: out of GPU memory | Only one copy of the model fits: run `bash scripts/stop_local_llm.sh`, then `docker compose up` again |
| A test fails | Copy the lines that start with `FAILED` and send them to Claude |
