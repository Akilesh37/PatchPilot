# PatchPilot Installation and Setup Guide

## System Prerequisites
- **Python**: 3.11 or 3.12 (`python3 --version`)
- **Java Development Kit**: JDK 17, 21, or 24 (`javac -version`)
- **Build Tool**: Apache Maven 3.9+ (`mvn -version`)
- **Node.js**: Node 18, 20, or 22 (`node -v`) with npm (`npm -v`)
- **Git**: Git 2.30+ (`git --version`)
- **Container Runtime (Optional for Tier 1 Sandbox)**: Docker 20+ or Podman 4+

---

## 1. Local Environment Setup

### Step 1: Clone Repository
```bash
git clone https://github.com/patchpilot/patchpilot.git
cd patchpilot
```

### Step 2: Configure Python Virtual Environment
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r pyproject.toml 2>/dev/null || pip install fastapi uvicorn pydantic sqlalchemy rank-bm25 pytest GitPython javalang rich peft datasets python-multipart
```

### Step 3: Compile JDK 17+ AST Parser
The Java AST parser must be compiled using your local JDK:
```bash
javac migration_engine/analyzers/tools/JavaAstParser.java
```
Verify that `JavaAstParser.class` exists in `migration_engine/analyzers/tools/`.

### Step 4: Configure Frontend
```bash
cd apps/web
npm install
cd ../..
```

---

## 2. Environment Variables

Create a `.env` file in the repository root or configure your shell environment:

```bash
# Model Provider: "mock" (default, fast, deterministic) or "huggingface"
MODEL_PROVIDER=mock
MODEL_NAME_OR_PATH=Qwen/Qwen2.5-Coder-3B-Instruct
LORA_ADAPTER_PATH=checkpoints/smoke_test_lora/adapter
DEVICE=cpu  # or mps for Apple Silicon, cuda for NVIDIA GPU

# Storage & Database
STORAGE_PATH=./data_storage
DATABASE_URL=sqlite:///./patchpilot.db

# GitHub Integration (Optional: for opening automated Pull Requests)
GITHUB_TOKEN=ghp_yourPersonalAccessTokenHere
```

---

## 3. Running Test Suites

Run the complete 31-test automated test suite:
```bash
.venv/bin/pytest tests/ -v
```

Execute the multi-system benchmark harness:
```bash
.venv/bin/python3 scripts/run_benchmarks.py
```

Run the PEFT LoRA training smoke-test:
```bash
.venv/bin/python3 ml/training/train_lora.py --mode lora --smoke-test --output checkpoints/smoke_test_lora
```

---

## 4. Running the Application

### Terminal 1: Backend API Server
```bash
source .venv/bin/activate
uvicorn apps.api.main:app --host 0.0.0.0 --port 8000 --reload
```
API Documentation will be available at [http://localhost:8000/docs](http://localhost:8000/docs).

### Terminal 2: Enterprise Next.js Developer Dashboard
```bash
cd apps/web
npm run dev
```
Open [http://localhost:3000](http://localhost:3000) in your browser.

