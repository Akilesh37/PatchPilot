# PatchPilot Production Deployment Guide

This guide outlines the production deployment of PatchPilot using:
- **Railway** for the FastAPI backend, static code analysis engine, and sandboxed verification worker.
- **Vercel** for the Next.js 16 enterprise developer workstation frontend.

---

## 1. System Architecture in Production

```
                                      ┌─────────────────────────────────────────┐
                                      │             Vercel Platform             │
                                      │   Next.js 16 Developer Workstation UI   │
                                      │   (https://patchpilot.vercel.app)       │
                                      └────────────────────┬────────────────────┘
                                                           │
                                             HTTPS / CORS Requests
                                    (Authorization: Bearer / X-GitHub-Token)
                                                           │
                                                           ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                                   Railway Platform                                     │
│                               Docker Container (Python 3.12)                          │
│                                                                                        │
│   FastAPI Web Service (0.0.0.0:$PORT)                                                  │
│   ├── /health (Liveness/Readiness probe)                                               │
│   ├── /api/projects & /api/migrations (REST API)                                       │
│   │                                                                                    │
│   Static Analysis & Verification Engine                                                │
│   ├── OpenJDK 17 + Apache Maven 3.9 (Installed)                                        │
│   ├── JDK Compiler Tree API AST Parser (Pre-compiled)                                  │
│   ├── Hybrid BM25 & Semantic Documentation RAG                                         │
│   ├── Transactional Patch Synthesizer & Atomic Rollback Checkpoints                    │
│   └── Tier 2 Hardened Subprocess Sandbox (Env secret-scrubbed, process-group isolated)  │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Deploying Backend to Railway

### Prerequisites
- A [Railway account](https://railway.app)
- Connected GitHub account with access to `Akilesh37/PatchPilot`

### Step-by-Step Instructions

1. **Create New Project in Railway:**
   - Log in to your [Railway Dashboard](https://railway.app/dashboard).
   - Click **"New Project"** &rarr; **"Deploy from GitHub repo"**.
   - Select `Akilesh37/PatchPilot`.

2. **Configure Build Settings:**
   Railway automatically detects the root [`Dockerfile`](../Dockerfile) and [`railway.json`](../railway.json).
   - **Builder:** `DOCKERFILE`
   - **Dockerfile Path:** `Dockerfile`

3. **Set Environment Variables in Railway:**
   Under your service's **"Variables"** tab, configure:

   | Variable | Value | Description |
   | :--- | :--- | :--- |
   | `PORT` | `8000` | Port automatically assigned by Railway |
   | `FRONTEND_ORIGINS` | `https://your-frontend.vercel.app,http://localhost:3000` | Allowed CORS origins for Next.js |
   | `DATABASE_URL` | `sqlite:////app/data_storage/patchpilot.db` | SQLite path or PostgreSQL connection string |
   | `LOG_LEVEL` | `INFO` | Logging verbosity |
   | `GITHUB_TOKEN` | *(Optional default)* | Default token for GitHub integrations (can also be passed per-request) |

4. **Add a Persistent Volume (Recommended):**
   - In the Railway service settings, click **"Add Volume"**.
   - Set the mount path to `/app/data_storage`.
   - This ensures migration history and SQLite databases persist across container restarts.

5. **Generate Public Domain:**
   - Go to **"Settings"** &rarr; **"Networking"** &rarr; click **"Generate Domain"**.
   - You will receive a URL like: `https://patchpilot-production.up.railway.app`.

6. **Verify Deployment:**
   - Open `https://<your-railway-url>/health` in your browser.
   - Expected response:
     ```json
     {
       "status": "healthy",
       "service": "PatchPilot",
       "version": "1.0.0",
       "timestamp": "2026-11-04T10:30:00Z"
     }
     ```
   - OpenAPI documentation is available at `https://<your-railway-url>/docs`.

---

## 3. Deploying Frontend to Vercel

### Prerequisites
- A [Vercel account](https://vercel.com)
- Connected GitHub account

### Step-by-Step Instructions

1. **Import Project in Vercel:**
   - Log in to [Vercel](https://vercel.com/dashboard) &rarr; click **"Add New..."** &rarr; **"Project"**.
   - Select the `Akilesh37/PatchPilot` repository.

2. **Configure Root Directory:**
   - In the project configuration screen, locate **"Root Directory"**.
   - Click **"Edit"** and select `apps/web`.

3. **Configure Build Settings:**
   - **Framework Preset:** Next.js
   - **Build Command:** `next build` (default)
   - **Install Command:** `npm install` (default)

4. **Set Environment Variables in Vercel:**
   Add the following environment variable:

   | Variable | Value | Description |
   | :--- | :--- | :--- |
   | `NEXT_PUBLIC_API_URL` | `https://<your-railway-url>` | Railway backend URL (no trailing slash) |

5. **Deploy:**
   - Click **"Deploy"**.
   - Vercel builds the static and dynamic pages with Turbopack and assigns a production domain (e.g. `https://patchpilot.vercel.app`).

6. **Update Railway CORS:**
   - Copy your assigned Vercel URL (e.g. `https://patchpilot.vercel.app`).
   - In Railway, update `FRONTEND_ORIGINS` to include your Vercel URL:
     ```
     FRONTEND_ORIGINS=https://patchpilot.vercel.app,https://*.vercel.app,http://localhost:3000
     ```

---

## 4. Local Docker Testing

To test the complete production container locally:

```bash
# 1. Build the production Docker container
docker build -t patchpilot-api:latest .

# 2. Run the container locally listening on port 8000
docker run --rm -p 8000:8000 \
  -e FRONTEND_ORIGINS="http://localhost:3000" \
  --name patchpilot-backend \
  patchpilot-api:latest

# 3. Test the healthcheck endpoint
curl http://localhost:8000/health

# 4. Test repository analysis endpoint
curl http://localhost:8000/api/rules
```

---

## 5. Security & Isolation in Cloud Production

- **Non-Privileged Sandbox Execution:** When running on cloud container hosts without nested virtualization, the backend automatically uses the Tier 2 Hardened Subprocess Sandbox.
- **Secret Purification:** The sandbox strips `AWS_*`, `GITHUB_*`, `SSH_*`, and token credentials from execution environments before running Maven or Java builds.
- **Process Group Termination:** If a build or test command times out, `os.killpg(os.getpgid(pid), signal.SIGKILL)` guarantees that background sub-processes are completely terminated.
- **Sanitized Pull Requests:** GitHub Personal Access Tokens are stripped from logs and error payloads via regex redaction (`ghp_[REDACTED]`, `[TOKEN_REDACTED]`).

