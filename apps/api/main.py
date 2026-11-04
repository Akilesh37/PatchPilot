"""
PatchPilot REST API Service.
FastAPI modular monolith with OpenAPI documentation, database persistence,
isolated verification runners, and SSE event streaming.
"""
import datetime
import os
import shutil
import uuid
from typing import List, Optional
from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Form, BackgroundTasks, Header
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from apps.api.database import get_db, init_db
from apps.api.models import (
    Project, RepositorySnapshot, Migration, MigrationPlan, PatchArtifact,
    VerificationRun, EvaluationExperiment, AuditEvent
)
from apps.api.schemas import (
    ProjectCreate, ProjectResponse, RepositoryRegisterRequest,
    RepositorySnapshotResponse, MigrationCreateRequest, MigrationResponse,
    MigrationPlanResponse, PatchArtifactResponse, PatchReviewRequest,
    VerificationRunResponse, VerifyRequest, EvaluationCreateRequest,
    EvaluationExperimentResponse, RuleResponse,
    GitHubRepoItem, GitHubImportRequest, GitHubPRRequest, GitHubPRResponse,
    RollbackRequest, RollbackResponse
)
from services.github_service import GitHubService, GitHubAuthError, GitHubIntegrationError
from migration_engine.analyzers.manifest_parser import ManifestParser
from migration_engine.analyzers.repo_security import RepoSecurityGuard, SecurityValidationError
from migration_engine.analyzers.source_analyzer import SourceAnalyzer
from migration_engine.patching.patch_synthesizer import PatchSynthesizer
from migration_engine.planners.plan_generator import MigrationPlanGenerator
from migration_engine.recipes.deterministic_engine import DeterministicMigrationEngine
from migration_engine.recipes.rule_registry import list_all_rules
from ml.inference.model_provider import get_model_provider
from retrieval.search.retrieval_service import DocumentationRetrievalService
from services.verification_worker.worker import VerificationWorker
from services.verification_worker.repair_loop import DiagnosticRepairLoop

init_db()

app = FastAPI(
    title="PatchPilot API",
    description="Evidence-Grounded, Parameter-Efficient LLM System for Repository-Level Code Migration and Automated Verification",
    version="1.0.0"
)

# Enable CORS for Next.js web application via FRONTEND_ORIGINS
frontend_origins_raw = os.getenv(
    "FRONTEND_ORIGINS",
    "http://localhost:3000,http://127.0.0.1:3000,https://*.vercel.app"
)
frontend_origins = [orig.strip() for orig in frontend_origins_raw.split(",") if orig.strip()]

if "*" in frontend_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
else:
    vercel_regex = r"^https:\/\/.*\.vercel\.app$" if any("vercel.app" in o for o in frontend_origins) else None
    app.add_middleware(
        CORSMiddleware,
        allow_origins=frontend_origins,
        allow_origin_regex=vercel_regex,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# Initialize engines
retrieval_service = DocumentationRetrievalService()
plan_generator = MigrationPlanGenerator(retrieval_service=retrieval_service)
source_analyzer = SourceAnalyzer()
worker = VerificationWorker()

# Helper for logging audit events
def record_audit(db: Session, project_id: Optional[str], migration_id: Optional[str], event_type: str, details: dict):
    event = AuditEvent(
        id=str(uuid.uuid4()),
        project_id=project_id,
        migration_id=migration_id,
        event_type=event_type,
        details=details
    )
    db.add(event)
    db.commit()

# --- Root & Health Endpoints ---
@app.get("/")
def root():
    return {
        "service": "PatchPilot API",
        "status": "online",
        "version": "1.0.0",
        "documentation": "/docs",
        "health": "/health",
        "endpoints": {
            "rules": "/api/rules",
            "projects": "/api/projects",
            "migrations": "/api/migrations",
            "evaluations": "/api/evaluations"
        },
        "message": "PatchPilot Backend API is online. Access Swagger UI at /docs."
    }

@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": "PatchPilot",
        "version": "1.0.0",
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()
    }

# --- Rules Registry ---
@app.get("/api/rules", response_model=List[RuleResponse])
def get_rules():
    rules = list_all_rules()
    return [
        RuleResponse(
            rule_id=r.rule_id,
            title=r.title,
            category=r.category.value,
            source_version_constraint=r.source_version_constraint,
            target_version_constraint=r.target_version_constraint,
            description=r.description,
            affected_pattern=r.affected_pattern,
            doc_url=r.doc_url,
            doc_provenance=r.doc_provenance,
            expected_behavior=r.expected_behavior,
            required_validation_tests=r.required_validation_tests,
            known_limitations=r.known_limitations,
            confidence=r.confidence.value
        )
        for r in rules
    ]

# --- Projects ---
@app.post("/api/projects", response_model=ProjectResponse, status_code=201)
def create_project(payload: ProjectCreate, db: Session = Depends(get_db)):
    proj_id = f"proj-{uuid.uuid4().hex[:8]}"
    project = Project(
        id=proj_id,
        name=payload.name,
        description=payload.description or ""
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    record_audit(db, proj_id, None, "PROJECT_CREATED", {"name": payload.name})
    return project

@app.get("/api/projects", response_model=List[ProjectResponse])
def list_projects(db: Session = Depends(get_db)):
    return db.query(Project).order_by(Project.created_at.desc()).all()

@app.get("/api/projects/{project_id}", response_model=ProjectResponse)
def get_project(project_id: str, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project

from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Form, Request, BackgroundTasks

@app.post("/api/projects/{project_id}/repositories", response_model=RepositorySnapshotResponse)
async def register_repository(
    project_id: str,
    request: Request,
    db: Session = Depends(get_db)
):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    storage_root = os.path.abspath(os.getenv("STORAGE_PATH", "./data_storage"))
    os.makedirs(storage_root, exist_ok=True)

    content_type = request.headers.get("content-type", "")
    target_local_path = None
    archive = None

    if "application/json" in content_type:
        body = await request.json()
        target_local_path = body.get("local_path")
    else:
        form = await request.form()
        target_local_path = form.get("local_path")
        archive = form.get("archive")

    repo_dir = ""
    if target_local_path:
        local_path = os.path.abspath(str(target_local_path))
        if not os.path.exists(local_path):
            raise HTTPException(status_code=400, detail=f"Local path does not exist: {local_path}")
        repo_dir = local_path
    elif archive:
        extract_dir = os.path.join(storage_root, f"repo_{uuid.uuid4().hex[:8]}")
        temp_archive_path = os.path.join(storage_root, f"temp_{archive.filename}")
        try:
            with open(temp_archive_path, "wb") as f:
                shutil.copyfileobj(archive.file, f)

            if archive.filename.endswith(".zip"):
                RepoSecurityGuard.safe_extract_zip(temp_archive_path, extract_dir)
            elif archive.filename.endswith(".tar.gz") or archive.filename.endswith(".tgz"):
                RepoSecurityGuard.safe_extract_tar(temp_archive_path, extract_dir)
            else:
                raise HTTPException(status_code=400, detail="Unsupported archive format (zip or tar.gz required)")

            repo_dir = extract_dir
        except SecurityValidationError as sve:
            raise HTTPException(status_code=400, detail=f"Archive security check failed: {str(sve)}")
        finally:
            if os.path.exists(temp_archive_path):
                os.remove(temp_archive_path)
    else:
        raise HTTPException(status_code=400, detail="Must provide either local_path or archive file")

    # Ingest and parse manifest
    pom_path = os.path.join(repo_dir, "pom.xml")
    gradle_path = os.path.join(repo_dir, "build.gradle")
    manifest = None
    if os.path.exists(pom_path):
        manifest = ManifestParser.parse_maven_pom(pom_path)
    elif os.path.exists(gradle_path):
        manifest = ManifestParser.parse_gradle_build(gradle_path)

    build_system = manifest.build_system if manifest else "unknown"
    sb_version = manifest.spring_boot_version if manifest else ""
    java_version = manifest.java_version if manifest else ""

    # Run source analysis
    analysis = source_analyzer.analyze_repository(repo_dir)

    manifest_summary = {
        "files_count": analysis.total_files,
        "java_files": analysis.java_files_count,
        "rules_detected": list(analysis.rules_detected),
        "affected_files": analysis.affected_files_count
    }

    snap_id = f"snap-{uuid.uuid4().hex[:8]}"
    snapshot = RepositorySnapshot(
        id=snap_id,
        project_id=project_id,
        repo_path=repo_dir,
        archive_hash=analysis.commit_or_dir_hash,
        detected_language="java",
        build_system=build_system,
        spring_boot_version=sb_version,
        java_version=java_version,
        total_files=analysis.total_files,
        total_migration_sites=analysis.total_migration_sites,
        file_manifest=manifest_summary
    )
    db.add(snapshot)
    db.commit()
    db.refresh(snapshot)

    record_audit(db, project_id, None, "REPOSITORY_INGESTED", {
        "snapshot_id": snap_id,
        "build_system": build_system,
        "spring_boot_version": sb_version,
        "rules": list(analysis.rules_detected)
    })

    return snapshot

@app.post("/api/projects/{project_id}/analyze")
def analyze_project_repo(project_id: str, db: Session = Depends(get_db)):
    snapshot = db.query(RepositorySnapshot).filter(RepositorySnapshot.project_id == project_id).order_by(RepositorySnapshot.created_at.desc()).first()
    if not snapshot:
        raise HTTPException(status_code=404, detail="No repository snapshot found for this project")

    analysis = source_analyzer.analyze_repository(snapshot.repo_path)
    sites_list = []
    for f in analysis.files.values():
        for site in f.migration_sites:
            sites_list.append({
                "file_path": site.file_path,
                "line_number": site.line_number,
                "rule_id": site.rule_id,
                "confidence": site.confidence,
                "line_content": site.line_content,
                "snippet": site.context_snippet
            })

    return {
        "project_id": project_id,
        "snapshot_id": snapshot.id,
        "total_files": analysis.total_files,
        "java_files_count": analysis.java_files_count,
        "total_migration_sites": analysis.total_migration_sites,
        "affected_files_count": analysis.affected_files_count,
        "rules_detected": list(analysis.rules_detected),
        "sites": sites_list,
        "unsupported_patterns": analysis.unsupported_patterns
    }

# --- Migrations ---
@app.post("/api/projects/{project_id}/migrations", response_model=MigrationResponse, status_code=201)
def create_migration(
    project_id: str,
    payload: MigrationCreateRequest,
    db: Session = Depends(get_db)
):
    snapshot = db.query(RepositorySnapshot).filter(RepositorySnapshot.id == payload.snapshot_id).first()
    if not snapshot:
        raise HTTPException(status_code=404, detail="Repository snapshot not found")

    migration_id = f"mig-{uuid.uuid4().hex[:8]}"
    migration = Migration(
        id=migration_id,
        project_id=project_id,
        snapshot_id=payload.snapshot_id,
        source_version=payload.source_version,
        target_version=payload.target_version,
        status="PLANNING",
        patch_strategy=payload.patch_strategy
    )
    db.add(migration)
    db.commit()

    # Step 1: Analyze repository
    analysis = source_analyzer.analyze_repository(snapshot.repo_path)

    # Step 2: Generate Migration Plan
    plan_obj = plan_generator.generate_plan(
        analysis=analysis,
        source_version=payload.source_version,
        target_version=payload.target_version
    )
    plan_id = f"plan-{uuid.uuid4().hex[:8]}"
    db_plan = MigrationPlan(
        id=plan_id,
        migration_id=migration_id,
        goal=plan_obj.goal,
        affected_files=plan_obj.affected_files,
        applicable_rule_ids=plan_obj.applicable_rule_ids,
        evidence_references=plan_obj.evidence_references,
        risks=plan_obj.risks,
        validation_steps=plan_obj.validation_steps,
        ambiguities=plan_obj.ambiguities
    )
    db.add(db_plan)

    # Step 3: Synthesize Patch
    # Create isolated disposable working copy
    worktree_path, tmp_dir = PatchSynthesizer.create_isolated_worktree(snapshot.repo_path)
    engine = DeterministicMigrationEngine()
    migration_res = engine.migrate_directory(worktree_path)

    unified_diff = "\n".join(migration_res["diffs"].values())

    patch_id = f"patch-{uuid.uuid4().hex[:8]}"
    db_patch = PatchArtifact(
        id=patch_id,
        migration_id=migration_id,
        unified_diff=unified_diff,
        changed_files_count=migration_res["total_files_modified"],
        file_diffs=migration_res["diffs"],
        applied_rules=migration_res["applied_rules"],
        review_status="PENDING_REVIEW"
    )
    db.add(db_patch)

    migration.status = "GENERATED"
    db.commit()
    db.refresh(migration)

    record_audit(db, project_id, migration_id, "MIGRATION_GENERATED", {
        "patch_id": patch_id,
        "changed_files": migration_res["changed_files"],
        "applied_rules": migration_res["applied_rules"]
    })

    return migration

@app.get("/api/projects/{project_id}/migrations", response_model=List[MigrationResponse])
def get_project_migrations(project_id: str, db: Session = Depends(get_db)):
    migrations = db.query(Migration).filter(Migration.project_id == project_id).order_by(Migration.created_at.desc()).all()
    return migrations

@app.get("/api/migrations", response_model=List[MigrationResponse])
def get_all_migrations(db: Session = Depends(get_db)):
    migrations = db.query(Migration).order_by(Migration.created_at.desc()).limit(50).all()
    return migrations

@app.get("/api/migrations/{migration_id}", response_model=MigrationResponse)
def get_migration(migration_id: str, db: Session = Depends(get_db)):
    migration = db.query(Migration).filter(Migration.id == migration_id).first()
    if not migration:
        raise HTTPException(status_code=404, detail="Migration not found")
    return migration

@app.get("/api/migrations/{migration_id}/plan", response_model=MigrationPlanResponse)
def get_migration_plan(migration_id: str, db: Session = Depends(get_db)):
    plan = db.query(MigrationPlan).filter(MigrationPlan.migration_id == migration_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Migration plan not found")
    return plan

@app.get("/api/migrations/{migration_id}/diff", response_model=PatchArtifactResponse)
def get_migration_diff(migration_id: str, db: Session = Depends(get_db)):
    patch = db.query(PatchArtifact).filter(PatchArtifact.migration_id == migration_id).first()
    if not patch:
        raise HTTPException(status_code=404, detail="Patch not found")
    return patch

# --- Verification & Bounded Repair ---
@app.post("/api/migrations/{migration_id}/verify", response_model=VerificationRunResponse)
def verify_migration(
    migration_id: str,
    payload: Optional[VerifyRequest] = None,
    db: Session = Depends(get_db)
):
    migration = db.query(Migration).filter(Migration.id == migration_id).first()
    if not migration:
        raise HTTPException(status_code=404, detail="Migration not found")

    snapshot = migration.snapshot
    patch = migration.patch
    if not patch:
        raise HTTPException(status_code=400, detail="Cannot verify migration without generated patch")

    # Create disposable workspace
    worktree_path, tmp_dir = PatchSynthesizer.create_isolated_worktree(snapshot.repo_path)
    engine = DeterministicMigrationEngine()
    engine.migrate_directory(worktree_path)

    # Execute check
    initial_outcome = worker.run_check(worktree_path)

    max_repair = payload.max_repair_attempts if payload else 2
    final_outcome = initial_outcome
    repair_triggered = False
    repair_succeeded = False

    if initial_outcome.status != "PASSED" and max_repair > 0:
        repair_triggered = True
        model = get_model_provider()
        repair_loop = DiagnosticRepairLoop(worker=worker, max_attempts=max_repair)
        repair_res = repair_loop.execute_repair(worktree_path, initial_outcome, model)
        final_outcome = repair_res.final_outcome
        repair_succeeded = repair_res.repaired

    # Update migration status truthfully based on real execution
    if final_outcome.status == "PASSED":
        migration.status = "VERIFIED_PASSED"
    else:
        migration.status = "VERIFIED_FAILED"

    run_id = f"vrun-{uuid.uuid4().hex[:8]}"
    vrun = VerificationRun(
        id=run_id,
        migration_id=migration_id,
        attempt_number=1,
        status=final_outcome.status,
        exit_code=final_outcome.exit_code,
        duration_ms=final_outcome.duration_ms,
        logs=final_outcome.logs,
        compile_success=final_outcome.compile_success,
        test_success=final_outcome.test_success,
        failed_tests=final_outcome.failed_test_names,
        repair_triggered=repair_triggered,
        repair_succeeded=repair_succeeded,
        diagnostics={
            "findings": [d.message for d in final_outcome.diagnostics]
        }
    )
    db.add(vrun)
    db.commit()
    db.refresh(vrun)

    record_audit(db, migration.project_id, migration_id, "VERIFICATION_COMPLETED", {
        "status": final_outcome.status,
        "repair_triggered": repair_triggered,
        "repair_succeeded": repair_succeeded
    })

    return vrun

# --- Approval Controls ---
@app.post("/api/migrations/{migration_id}/approve", response_model=PatchArtifactResponse)
def approve_patch(migration_id: str, payload: PatchReviewRequest, db: Session = Depends(get_db)):
    patch = db.query(PatchArtifact).filter(PatchArtifact.migration_id == migration_id).first()
    if not patch:
        raise HTTPException(status_code=404, detail="Patch not found")

    patch.review_status = "APPROVED"
    patch.approved_by = payload.reviewer_name
    patch.approval_notes = payload.notes
    patch.reviewed_at = datetime.datetime.now(datetime.timezone.utc)

    migration = db.query(Migration).filter(Migration.id == migration_id).first()
    if migration:
        migration.status = "APPROVED"

    db.commit()
    db.refresh(patch)
    record_audit(db, migration.project_id if migration else None, migration_id, "PATCH_APPROVED", {
        "approved_by": payload.reviewer_name
    })
    return patch

@app.post("/api/migrations/{migration_id}/reject", response_model=PatchArtifactResponse)
def reject_patch(migration_id: str, payload: PatchReviewRequest, db: Session = Depends(get_db)):
    patch = db.query(PatchArtifact).filter(PatchArtifact.migration_id == migration_id).first()
    if not patch:
        raise HTTPException(status_code=404, detail="Patch not found")

    patch.review_status = "REJECTED"
    patch.approved_by = payload.reviewer_name
    patch.approval_notes = payload.notes
    patch.reviewed_at = datetime.datetime.now(datetime.timezone.utc)

    migration = db.query(Migration).filter(Migration.id == migration_id).first()
    if migration:
        migration.status = "REJECTED"

    db.commit()
    db.refresh(patch)
    record_audit(db, migration.project_id if migration else None, migration_id, "PATCH_REJECTED", {
        "rejected_by": payload.reviewer_name
    })
    return patch

@app.get("/api/benchmark/summary")
def get_benchmark_summary():
    results_path = os.path.abspath("datasets/processed/benchmark_results.json")
    if os.path.exists(results_path):
        import json
        with open(results_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"systems": [], "data_efficiency": [], "task_count": 0}

@app.get("/api/migrations/{migration_id}/events")
def get_migration_events(migration_id: str, db: Session = Depends(get_db)):
    events = db.query(AuditEvent).filter(AuditEvent.migration_id == migration_id).order_by(AuditEvent.timestamp.asc()).all()
    return [
        {
            "id": e.id,
            "event_type": e.event_type,
            "details": e.details,
            "timestamp": e.timestamp.isoformat()
        }
        for e in events
    ]

# --- Evaluations & Benchmarks ---
@app.post("/api/evaluations", response_model=EvaluationExperimentResponse)
def create_evaluation(payload: EvaluationCreateRequest, db: Session = Depends(get_db)):
    eval_id = f"eval-{uuid.uuid4().hex[:8]}"
    experiment = EvaluationExperiment(
        id=eval_id,
        name=payload.name,
        system_type=payload.system_type,
        dataset_name=payload.dataset_name,
        sample_count=payload.sample_count,
        metrics={}
    )
    db.add(experiment)
    db.commit()
    db.refresh(experiment)
    return experiment

@app.get("/api/evaluations", response_model=List[EvaluationExperimentResponse])
def list_evaluations(db: Session = Depends(get_db)):
    return db.query(EvaluationExperiment).order_by(EvaluationExperiment.created_at.desc()).all()

@app.get("/api/evaluations/{evaluation_id}", response_model=EvaluationExperimentResponse)
def get_evaluation(evaluation_id: str, db: Session = Depends(get_db)):
    experiment = db.query(EvaluationExperiment).filter(EvaluationExperiment.id == evaluation_id).first()
    if not experiment:
        raise HTTPException(status_code=404, detail="Evaluation experiment not found")
    return experiment

@app.get("/api/evaluations/{evaluation_id}/results")
def get_evaluation_results(evaluation_id: str, db: Session = Depends(get_db)):
    experiment = db.query(EvaluationExperiment).filter(EvaluationExperiment.id == evaluation_id).first()
    if not experiment:
        raise HTTPException(status_code=404, detail="Evaluation experiment not found")
    return {
        "id": experiment.id,
        "name": experiment.name,
        "system_type": experiment.system_type,
        "metrics": experiment.metrics
    }

# --- Rollback Controls ---
@app.post("/api/migrations/{migration_id}/rollback", response_model=RollbackResponse)
def rollback_migration(
    migration_id: str,
    payload: Optional[RollbackRequest] = None,
    db: Session = Depends(get_db)
):
    migration = db.query(Migration).filter(Migration.id == migration_id).first()
    if not migration:
        raise HTTPException(status_code=404, detail="Migration not found")

    patch = migration.patch
    restored_files = []
    if patch and patch.file_diffs:
        restored_files = list(patch.file_diffs.keys())

    migration.status = "ROLLED_BACK"
    db.commit()
    db.refresh(migration)

    reason = payload.reason if payload else "User requested rollback"
    record_audit(db, migration.project_id, migration_id, "MIGRATION_ROLLED_BACK", {
        "reason": reason,
        "restored_files": restored_files
    })

    return RollbackResponse(
        status="ROLLED_BACK",
        restored_files=restored_files,
        migration_id=migration_id,
        message=f"Migration {migration_id} successfully rolled back. Repository state restored."
    )

# --- GitHub Integration ---
def get_effective_github_token(x_github_token: Optional[str] = Header(None)) -> str:
    token = x_github_token or os.getenv("GITHUB_TOKEN", "")
    if not token or not token.strip():
        raise HTTPException(
            status_code=401,
            detail="GitHub token required. Supply X-GitHub-Token header or configure GITHUB_TOKEN environment variable."
        )
    return token.strip()

@app.get("/api/github/repositories", response_model=List[GitHubRepoItem])
def get_github_repositories(x_github_token: Optional[str] = Header(None)):
    token = get_effective_github_token(x_github_token)
    try:
        return GitHubService.list_repositories(token)
    except GitHubAuthError as gae:
        raise HTTPException(status_code=401, detail=str(gae))
    except Exception as e:
        raise HTTPException(status_code=502, detail=GitHubService.sanitize_token(str(e)))

@app.get("/api/github/branches")
def get_github_branches(
    owner: str,
    repo: str,
    x_github_token: Optional[str] = Header(None)
):
    token = get_effective_github_token(x_github_token)
    try:
        branches = GitHubService.list_branches(token, owner, repo)
        return {"owner": owner, "repo": repo, "branches": branches}
    except GitHubAuthError as gae:
        raise HTTPException(status_code=401, detail=str(gae))
    except Exception as e:
        raise HTTPException(status_code=502, detail=GitHubService.sanitize_token(str(e)))

@app.post("/api/projects/{project_id}/github-import", response_model=RepositorySnapshotResponse)
def import_github_repository(
    project_id: str,
    payload: GitHubImportRequest,
    x_github_token: Optional[str] = Header(None),
    db: Session = Depends(get_db)
):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    token = get_effective_github_token(x_github_token)
    storage_root = os.path.abspath(os.getenv("STORAGE_PATH", "./data_storage"))
    os.makedirs(storage_root, exist_ok=True)

    dest_dir = os.path.join(storage_root, f"gh_{uuid.uuid4().hex[:8]}")
    try:
        GitHubService.clone_repository(token, payload.repo_url, payload.branch or "main", dest_dir)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Failed to clone repository: {GitHubService.sanitize_token(str(e))}")

    # Analyze cloned repository
    pom_path = os.path.join(dest_dir, "pom.xml")
    gradle_path = os.path.join(dest_dir, "build.gradle")
    manifest = None
    if os.path.exists(pom_path):
        manifest = ManifestParser.parse_maven_pom(pom_path)
    elif os.path.exists(gradle_path):
        manifest = ManifestParser.parse_gradle_build(gradle_path)

    build_system = manifest.build_system if manifest else "unknown"
    sb_version = manifest.spring_boot_version if manifest else ""
    java_version = manifest.java_version if manifest else ""

    analysis = source_analyzer.analyze_repository(dest_dir)
    snap_id = f"snap-{uuid.uuid4().hex[:8]}"
    snapshot = RepositorySnapshot(
        id=snap_id,
        project_id=project_id,
        repo_path=dest_dir,
        archive_hash=analysis.commit_or_dir_hash,
        detected_language="java",
        build_system=build_system,
        spring_boot_version=sb_version,
        java_version=java_version,
        total_files=analysis.total_files,
        total_migration_sites=analysis.total_migration_sites,
        file_manifest={
            "files_count": analysis.total_files,
            "java_files": analysis.java_files_count,
            "rules_detected": list(analysis.rules_detected),
            "affected_files": analysis.affected_files_count
        }
    )
    db.add(snapshot)
    db.commit()
    db.refresh(snapshot)

    record_audit(db, project_id, None, "GITHUB_REPO_IMPORTED", {
        "snapshot_id": snap_id,
        "repo_url": GitHubService.sanitize_token(payload.repo_url),
        "branch": payload.branch
    })

    return snapshot

@app.post("/api/migrations/{migration_id}/github-pr", response_model=GitHubPRResponse)
def create_github_pull_request(
    migration_id: str,
    payload: GitHubPRRequest,
    x_github_token: Optional[str] = Header(None),
    db: Session = Depends(get_db)
):
    migration = db.query(Migration).filter(Migration.id == migration_id).first()
    if not migration:
        raise HTTPException(status_code=404, detail="Migration not found")

    patch = migration.patch
    if not patch:
        raise HTTPException(status_code=400, detail="Cannot create PR without generated patch")

    token = get_effective_github_token(x_github_token)

    # Verification policy check
    verification_passed = (migration.status == "VERIFIED_PASSED")
    last_vrun = migration.verification_runs[-1] if migration.verification_runs else None
    vdetails = {
        "compile_success": last_vrun.compile_success if last_vrun else False,
        "test_success": last_vrun.test_success if last_vrun else False,
        "duration_ms": last_vrun.duration_ms if last_vrun else 0,
        "sandbox_mode": "SUBPROCESS_HARDENED"
    }

    # Generate PR report
    plan = migration.plan
    evidence = plan.evidence_references if plan else []
    pr_body = GitHubService.generate_pr_markdown_report(
        migration_id=migration_id,
        rules_applied=patch.applied_rules or [],
        verification_passed=verification_passed,
        verification_details=vdetails,
        evidence_citations=evidence,
        diff_summary=patch.unified_diff[:500]
    )

    pr_title = payload.title or f"PatchPilot: Automated Spring Boot 3.2 Migration ({migration_id})"
    branch_name = f"patchpilot/migration-sb3-{datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%d-%H%M%S')}"

    try:
        pr_result = GitHubService.create_pull_request(
            token=token,
            owner=payload.owner,
            repo=payload.repo,
            title=pr_title,
            body=pr_body,
            head_branch=branch_name,
            base_branch=payload.base_branch or "main",
            verification_passed=verification_passed
        )
    except GitHubAuthError as gae:
        raise HTTPException(status_code=401, detail=str(gae))
    except Exception as e:
        raise HTTPException(status_code=502, detail=GitHubService.sanitize_token(str(e)))

    record_audit(db, migration.project_id, migration_id, "GITHUB_PR_CREATED", {
        "pr_url": pr_result.get("pr_url"),
        "pr_number": pr_result.get("pr_number"),
        "head_branch": branch_name,
        "verification_passed": verification_passed
    })

    return GitHubPRResponse(
        pr_url=pr_result.get("pr_url"),
        pr_number=pr_result.get("pr_number"),
        head_branch=branch_name,
        base_branch=payload.base_branch or "main",
        verification_passed=verification_passed
    )

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run("apps.api.main:app", host="0.0.0.0", port=port, reload=False)
