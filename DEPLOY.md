# 🚀 Deploying Warranty Shield — Public URL for Your Resume

This guide gets you a **free public link** (e.g. `https://warranty-shield-yourname.streamlit.app`)
that anyone — recruiters included — can open with one click.

---

## Option A: Streamlit Community Cloud (recommended — free, zero-config)

Best choice for a resume project. Fully free, no credit card, deploys straight from GitHub.

### Step 1 — Push the project to GitHub

```bash
git init
git add .
git commit -m "Warranty Shield: explainable warranty-claim risk triage"
git branch -M main
git remote add origin https://github.com/R0hithReddyG/warranty-shield.git
git push -u origin main
```

> Tip: make sure `.env` is **not** committed (add it to `.gitignore`). All settings have safe defaults, so the app runs without it.

### Step 2 — Deploy

1. Go to **https://share.streamlit.io** and sign in with your GitHub account.
2. Click **"Create app" → "Paste GitHub repo URL"** (or authorize repo access and pick the repo).
3. Fill in:
   - **Repository:** `R0hithReddyG/warranty-shield`
   - **Branch:** `main`
   - **Main file path:** `app/main.py`
   - **App URL:** pick a nice slug, e.g. `warranty-shield` → `https://warranty-shield.streamlit.app`
4. Click **Deploy!**

First deploy takes 2–5 minutes (installs `requirements.txt` automatically). The platform
wakes the app on demand; after ~7 days of inactivity it sleeps and redeploys on the next visit.

### Step 3 — Put it on your resume

```
Warranty Shield — Explainable warranty-claim risk triage (Python, Streamlit, LangGraph)
🔗 Live demo: https://warranty-shield.streamlit.app
🔗 Code: https://github.com/R0hithReddyG/warranty-shield
```

---

## Option B: Docker (Render / Railway / Fly.io / any cloud)

If you want more control or a paid tier with always-on hosting, use the included `Dockerfile`.

### Render (free tier available)

1. Push to GitHub (as above).
2. On https://render.com → **New → Web Service** → connect your repo.
3. Settings:
   - **Environment:** Docker
   - **Port:** `8501` (Render auto-detects from the EXPOSE directive)
   - **Health check path:** `/healthz`
4. Deploy — you get a public URL like `https://warranty-shield.onrender.com`.

### Railway / Fly.io

```bash
# Railway
npm i -g @railway/cli
railway login && railway init && railway up

# Fly.io
flyctl launch          # detects the Dockerfile
flyctl deploy
```

---

## Option C: Hugging Face Spaces (free, Docker-based)

1. Create a new **Space** at https://huggingface.co/spaces → choose **Docker** template.
2. Push the repo contents; HF builds the included `Dockerfile`.
3. Public URL: `https://huggingface.co/spaces/<your-username>/warranty-shield`.

---

## Pre-deploy checklist

- ✅ `requirements.txt` at repo root (cloud platforms install it automatically)
- ✅ `.streamlit/config.toml` (theme + headless server settings)
- ✅ `app/main.py` as the entry point
- ✅ `.env` excluded from git (add to `.gitignore`) — defaults work without it
- ✅ No secrets in code — LangGraph/LLM keys are optional and only needed if you enable agentic mode

## Local production-style test before pushing

```bash
# Docker test
docker build -t warranty-shield .
docker run -p 8501:8501 warranty-shield
# → http://localhost:8501
```

## Troubleshooting

| Problem | Fix |
| --- | --- |
| Deploy fails on missing module | Ensure `requirements.txt` is committed at repo root |
| App sleeps after inactivity | Normal on free tiers; first visitor wakes it (~30 s) |
| Port binding errors on Docker platforms | Never hardcode; use `$PORT` (the Dockerfile already does) |
| Blank page | Check the app logs on the platform dashboard; run `pytest` locally first |
