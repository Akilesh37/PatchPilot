import hashlib
import os
import shutil
import tempfile
import pytest
from migration_engine.analyzers.source_analyzer import SourceAnalyzer
from migration_engine.planners.plan_generator import MigrationPlanGenerator
from migration_engine.patching.patch_synthesizer import PatchSynthesizer
from migration_engine.recipes.deterministic_engine import DeterministicMigrationEngine
from retrieval.search.retrieval_service import DocumentationRetrievalService
from services.verification_worker.worker import VerificationWorker
from services.verification_worker.repair_loop import DiagnosticRepairLoop
from ml.inference.model_provider import MockCodeModelProvider

def compute_dir_checksum(dir_path: str) -> str:
    hasher = hashlib.sha256()
    for root, _, files in sorted(os.walk(dir_path)):
        for f in sorted(files):
            if f.startswith(".") or "target" in root:
                continue
            fpath = os.path.join(root, f)
            with open(fpath, "rb") as fp:
                hasher.update(fp.read())
    return hasher.hexdigest()

def test_full_pipeline_e2e_customer_service():
    original_fixture = os.path.abspath("datasets/fixtures/customer-service-sb2")
    assert os.path.exists(original_fixture)

    # Record initial checksum of original repository
    initial_checksum = compute_dir_checksum(original_fixture)

    # 1. Analyze original repository
    analyzer = SourceAnalyzer()
    analysis = analyzer.analyze_repository(original_fixture)
    assert analysis.total_files > 0
    assert analysis.total_migration_sites > 0
    assert "RULE-JAKARTA-EE-PERSISTENCE" in analysis.rules_detected
    assert "RULE-JAKARTA-EE-SERVLET" in analysis.rules_detected

    # 2. Retrieve version-aware documentation citations & generate plan
    retriever = DocumentationRetrievalService()
    planner = MigrationPlanGenerator(retrieval_service=retriever)
    plan = planner.generate_plan(analysis, source_version="2.7.18", target_version="3.2.0")
    assert len(plan.applicable_rule_ids) > 0
    assert len(plan.evidence_references) > 0

    # 3. Create disposable isolated worktree (preserving original)
    worktree_path, tmp_dir = PatchSynthesizer.create_isolated_worktree(original_fixture)
    assert os.path.exists(worktree_path)

    # 4. Synthesize and apply patch
    engine = DeterministicMigrationEngine()
    migration_res = engine.migrate_directory(worktree_path)
    assert migration_res["total_files_modified"] > 0
    assert len(migration_res["diffs"]) > 0

    # 5. Run Verification in isolated sandbox
    worker = VerificationWorker(timeout_seconds=60)
    outcome = worker.run_check(worktree_path)
    assert outcome.status == "PASSED", f"Verification failed with logs:\n{outcome.logs}"
    assert outcome.compile_success is True
    assert outcome.test_success is True

    # 6. Verify original repository was NOT modified
    after_checksum = compute_dir_checksum(original_fixture)
    assert initial_checksum == after_checksum, "Original fixture was modified! Isolation violated."

def test_full_pipeline_e2e_order_service():
    original_fixture = os.path.abspath("datasets/fixtures/order-service-sb2")
    assert os.path.exists(original_fixture)
    initial_checksum = compute_dir_checksum(original_fixture)

    analyzer = SourceAnalyzer()
    analysis = analyzer.analyze_repository(original_fixture)
    assert "RULE-JAKARTA-EE-ANNOTATION" in analysis.rules_detected

    worktree_path, tmp_dir = PatchSynthesizer.create_isolated_worktree(original_fixture)
    engine = DeterministicMigrationEngine()
    res = engine.migrate_directory(worktree_path)
    assert res["total_files_modified"] > 0

    # Check that PostConstruct was migrated to jakarta.annotation
    migrated_order = os.path.join(worktree_path, "src/main/java/com/example/order/OrderService.java")
    with open(migrated_order) as f:
        content = f.read()
    assert "import jakarta.annotation.PostConstruct;" in content

    # Clean check
    after_checksum = compute_dir_checksum(original_fixture)
    assert initial_checksum == after_checksum
