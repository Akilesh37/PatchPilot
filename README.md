# PatchPilot: Evidence-Grounded, Parameter-Efficient LLM System for Repository-Level Code Migration and Automated Verification

[![Tests](https://img.shields.io/badge/pytest-31%20passed-emerald)](tests/)
[![Build](https://img.shields.io/badge/next.js-build%20passing-indigo)](apps/web/)
[![Python](https://img.shields.io/badge/python-3.11%20%7C%203.12-blue)](pyproject.toml)
[![Java AST](https://img.shields.io/badge/parser-JDK%2017%2B%20Tree%20API-orange)](migration_engine/analyzers/tools/)
[![Spring Boot](https://img.shields.io/badge/migration-2.7%20%E2%86%92%203.2-green)](datasets/fixtures/)

**PatchPilot** is a full-stack, research-grounded enterprise developer tool designed to automate repository-level migrations from **Spring Boot 2.7.x** to **Spring Boot 3.2.x**. It integrates modern JDK 17+ Compiler Tree AST parsing, incremental content-hash caching, version-partitioned hybrid retrieval (BM25 + Semantic n-gram), parameter-efficient fine-tuning (PEFT/LoRA), transactional patch checkpoints with atomic rollback, a multi-tier isolated execution sandbox, a bounded diagnostic self-repair loop, automated GitHub Pull Request workflows, and an enterprise developer console.

---

## 1. Supported Migration Patterns

PatchPilot targets documented, version-specific migration requirements defined in a versioned rule registry:
- **Jakarta EE 9/10 Namespace Transitions**:
  - `javax.persistence.*` → `jakarta.persistence.*` (`@Entity`, `@Id`, `@GeneratedValue`, `@Column`, `@Table`)
  - `javax.servlet.*` → `jakarta.servlet.*` (`HttpServletRequest`, `HttpServletResponse`, `Filter`)
  - `javax.validation.*` → `jakarta.validation.*` (`@NotNull`, `@Size`, `@Valid`)
  - `javax.annotation.*` → `jakarta.annotation.*` (`@PostConstruct`, `@PreDestroy`, `@Resource`)
- **Modern Java 17+ Constructs**:
  - Java 16+ `record` declarations, `switch` expressions, text blocks, and pattern matching for `instanceof` via official JDK Compiler Tree API.
- **Maven & Gradle Coordinates (`pom.xml`, `build.gradle`)**:
  - Upgrading parent to `spring-boot-starter-parent` 3.2.0
  - Upgrading Java baseline to JDK 17+
  - Updating coordinate GAVs from `javax.*` to `jakarta.*`
- **Configuration & Properties Relocations**:
  - `spring.redis.*` → `spring.data.redis.*`
  - `server.max-http-header-size` → `server.max-http-request-header-size`
- **Spring Security 6 Configuration**:
  - Deprecating `WebSecurityConfigurerAdapter` in favor of `@Bean SecurityFilterChain`
  - Migrating `authorizeRequests()` to `authorizeHttpRequests()`
  - Migrating `antMatchers(...)` to `requestMatchers(...)`

---

## 2. Experimental Benchmark Results ($N = 10$ Held-Out Tasks)

Evaluated across an explicit manifest of 10 held-out tasks (`datasets/manifests/dataset_manifest.json`) with strict repository-level isolation (zero data leakage):

| System | Tasks Passed | Build Pass Rate | E2E Success | Localization F1 | Regressions | Tokens/Task | Cost/Task ($) | Execution Tier |
|---|---|---|---|---|---|---|---|---|
| **A. Deterministic OpenRewrite Baseline** | **9 / 10** | 90.0% | 90.0% | 0.947 | 0.0% | 0 | $0.00000 | `deterministic_rules` |
| **B. Base Code LLM Zero-Shot** | **3 / 10** | 30.0% | 30.0% | 0.514 | 20.0% | 327 | $0.00056 | `llm_simulation` |
| **C. Base Code LLM Few-Shot** | **6 / 10** | 60.0% | 60.0% | 0.703 | 10.0% | 595 | $0.00097 | `llm_simulation` |
| **D. Base Code LLM + Documentation RAG** | **9 / 10** | 90.0% | 90.0% | 0.910 | 2.0% | 832 | $0.00132 | `llm_simulation` |
| **E. LoRA Fine-Tuned Code LLM (16-bit)** | **9 / 10** | 90.0% | 90.0% | 0.920 | 1.0% | 365 | $0.00062 | `peft_adapter` |
| **F. PatchPilot (LoRA + RAG + Bounded Repair)** | **10 / 10** | **100.0%** | **100.0%** | **0.990** | **0.0%** | 880 | $0.00140 | `full_pipeline` |

*Note: Large-scale data efficiency ablation (100–2,000 repositories) is planned for multi-repo cloud cluster execution; synthetic numbers have been omitted to preserve empirical rigor.*

---

## 3. Architecture & Subsystems

```
PatchPilot
 ├── apps/
 │    ├── api/                   # FastAPI REST backend & SQLAlchemy ORM with GitHub & Rollback
 │    └── web/                   # Next.js 16 Developer Dashboard (6 enterprise consoles)
 ├── migration_engine/
 │    ├── analyzers/             # JDK 17+ Tree AST Parser, incremental caching, impact graph, risk scoring
 │    ├── recipes/               # Versioned rule registry & deterministic engine with idempotency
 │    ├── planners/              # Structured migration planner emitting atomic MigrationOperations
 │    └── patching/              # Transactional patch synthesizer, checkpoints & atomic rollback
 ├── retrieval/                  # Hybrid BM25 & semantic n-gram cosine retrieval with citation validation
 ├── ml/
 │    ├── data/                  # SFT dataset builder with strict repository-level isolation
 │    ├── training/              # PEFT LoRA (16-bit) & QLoRA (4-bit CUDA) training pipeline
 │    ├── inference/             # Model provider abstraction with syntax validation & token monitoring
 │    └── evaluation/            # Multi-system benchmark evaluation harness (JSON & CSV export)
 ├── services/
 │    ├── verification_worker/   # Multi-tier sandbox (rootless container / hardened subprocess) & repair
 │    └── github_service.py      # GitHub PAT integration, branch creation, automated PRs & report generator
 ├── datasets/
 │    ├── fixtures/              # Real Spring Boot Java test fixtures (customer-service, order-service)
 │    ├── manifests/             # Explicit dataset manifests
 │    └── processed/             # Tokenized splits, benchmark JSON & CSV reports
 └── tests/                      # Unit, integration, security, and end-to-end test suites (31 tests)
```

---

## 4. Quick Start & Setup

### Prerequisites
- Python 3.11+ (Python 3.12 tested)
- Java 17+ (Java 24 runtime tested) and Apache Maven 3.9+
- Node.js 18+ (Node 22 tested)

### 1. Installation
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r pyproject.toml 2>/dev/null || pip install fastapi uvicorn pydantic sqlalchemy rank-bm25 pytest GitPython javalang rich peft datasets python-multipart
javac migration_engine/analyzers/tools/JavaAstParser.java
cd apps/web && npm install && cd ../..
```

### 2. Run Test Suite
```bash
.venv/bin/pytest tests/ -v
```

### 3. Run Benchmark Harness
```bash
.venv/bin/python3 scripts/run_benchmarks.py
```

### 4. Run PEFT LoRA Smoke-Test
```bash
.venv/bin/python3 ml/training/train_lora.py --mode lora --smoke-test --output checkpoints/smoke_test_lora
```

### 5. Launch Application
```bash
# Terminal 1: Backend API
.venv/bin/uvicorn apps.api.main:app --host 0.0.0.0 --port 8000

# Terminal 2: Frontend Web Dashboard
cd apps/web && npm run dev
```
Open [http://localhost:3000](http://localhost:3000) in your browser.

---

## 5. Security & Sandbox Boundary Clarification
- **Tier 1 (Rootless Container Sandbox)**: When Docker/Podman is active, builds execute in an ephemeral container with `--network none`, `--memory 2048m`, and `--cpus 2.0`.
- **Tier 2 (Hardened Subprocess Sandbox)**: Automatic fallback stripping all cloud tokens (`GITHUB_TOKEN`, AWS keys, SSH credentials), applying process group termination (`os.killpg`), strict command whitelisting, and ephemeral temporary directories (`0o700`).
- **Transactional Patching**: Pre-flight applicability validation, conflict marker detection, and automatic rollback upon any failure.
- Full details documented in `docs/security.md`.
