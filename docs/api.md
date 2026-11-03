# PatchPilot REST API Reference

The backend API is implemented with FastAPI and documented via interactive Swagger UI at `/docs` and ReDoc at `/redoc`.

## Base URL
Default local development: `http://localhost:8000`

---

## Endpoints

### System Health
- **GET** `/health`
  - Returns service status and UTC ISO timestamp.

### Rules Registry
- **GET** `/api/rules`
  - Returns versioned registry of supported migration rules, category, constraints, replacement mappings, and documentation URLs.

### Projects
- **POST** `/api/projects`
  - Body: `{"name": "...", "description": "..."}`
  - Returns created project object.
- **GET** `/api/projects`
  - Returns list of projects ordered by creation date.
- **GET** `/api/projects/{project_id}`
  - Returns project details.

### Repository Ingestion & Analysis
- **POST** `/api/projects/{project_id}/repositories`
  - Accepts either JSON `{"local_path": "/path/to/repo"}` or multipart archive upload (`.zip`, `.tar.gz`).
  - Returns parsed repository snapshot, detected build system, Spring Boot and Java versions.
- **POST** `/api/projects/{project_id}/analyze`
  - Runs JDK 17+ Tree AST analysis, returning candidate migration sites, line numbers, risk scores, and dependency graph.
- **POST** `/api/projects/{project_id}/github-import`
  - Headers: `X-GitHub-Token: ghp_...`
  - Body: `{"repo_url": "https://github.com/org/repo.git", "branch": "main"}`
  - Clones repository safely (token redacted from git config) and registers repository snapshot.

### Migrations
- **POST** `/api/projects/{project_id}/migrations`
  - Body: `{"snapshot_id": "...", "source_version": "2.7.18", "target_version": "3.2.0", "patch_strategy": "deterministic"}`
  - Generates structured migration plan with citations and synthesizes unified patch diffs.
- **GET** `/api/migrations/{migration_id}`
  - Returns migration status, plan, patch, and verification runs.
- **GET** `/api/migrations/{migration_id}/plan`
  - Returns structured migration plan with operations, risk classification, and evidence provenance.
- **GET** `/api/migrations/{migration_id}/diff`
  - Returns patch artifact with unified diff and per-file diffs.
- **POST** `/api/migrations/{migration_id}/rollback`
  - Body: `{"reason": "..."}`
  - Atomically rolls back an applied migration and restores all modified files to pre-migration checkpoint state.

### Verification & Sandboxed Execution
- **POST** `/api/migrations/{migration_id}/verify`
  - Body: `{"max_repair_attempts": 2}`
  - Executes build and test checks in isolated execution sandbox (Tier 1 Rootless Container or Tier 2 Hardened Subprocess).
  - Triggers evidence-grounded diagnostic self-repair if errors occur.

### Human Review Controls
- **POST** `/api/migrations/{migration_id}/approve`
  - Body: `{"reviewer_name": "...", "notes": "..."}`
  - Marks patch as APPROVED.
- **POST** `/api/migrations/{migration_id}/reject`
  - Body: `{"reviewer_name": "...", "notes": "..."}`
  - Marks patch as REJECTED.

### GitHub Integration
- **GET** `/api/github/repositories`
  - Headers: `X-GitHub-Token: ghp_...`
  - Lists accessible repositories.
- **GET** `/api/github/branches?owner=org&repo=repo`
  - Headers: `X-GitHub-Token: ghp_...`
  - Lists branches for specified repository.
- **POST** `/api/migrations/{migration_id}/github-pr`
  - Headers: `X-GitHub-Token: ghp_...`
  - Body: `{"owner": "...", "repo": "...", "base_branch": "main", "title": "..."}`
  - Creates dedicated migration branch, commits changes, and opens a Pull Request with a formatted Markdown migration report. Enforces verification policy labeling (`patchpilot:verified` or `patchpilot:unverified`).

### Audit & Benchmarking
- **GET** `/api/migrations/{migration_id}/events`
  - Returns chronological audit log for a migration.
- **GET** `/api/benchmark/summary`
  - Returns multi-system benchmark metrics.
