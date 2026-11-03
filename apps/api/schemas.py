"""
Pydantic schemas for request validation and response serialization.
Strictly compatible with Pydantic v2.
"""
from datetime import datetime
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, ConfigDict

# Projects
class ProjectCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = ""

class ProjectResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    description: str
    created_at: datetime
    updated_at: datetime

# Repositories
class RepositoryRegisterRequest(BaseModel):
    local_path: Optional[str] = None

class RepositorySnapshotResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: str
    repo_path: str
    archive_hash: str
    detected_language: str
    build_system: str
    spring_boot_version: Optional[str] = ""
    java_version: Optional[str] = ""
    total_files: int
    total_migration_sites: int
    file_manifest: Dict[str, Any]
    created_at: datetime

# Migration Plan & Diffs
class MigrationPlanResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    migration_id: str
    goal: str
    affected_files: List[str]
    applicable_rule_ids: List[str]
    evidence_references: List[Dict[str, Any]]
    risks: List[str]
    validation_steps: List[str]
    ambiguities: List[str]
    created_at: datetime

class PatchArtifactResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    migration_id: str
    unified_diff: str
    changed_files_count: int
    file_diffs: Dict[str, str]
    applied_rules: List[str]
    review_status: str
    approved_by: Optional[str] = None
    approval_notes: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    created_at: datetime

class PatchReviewRequest(BaseModel):
    reviewer_name: str = "Developer"
    notes: Optional[str] = ""

# Verification
class VerificationRunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    migration_id: str
    attempt_number: int
    status: str
    exit_code: int
    duration_ms: int
    logs: str
    compile_success: bool
    test_success: bool
    failed_tests: List[str]
    repair_triggered: bool
    repair_succeeded: bool
    diagnostics: Dict[str, Any]
    created_at: datetime

class VerifyRequest(BaseModel):
    max_repair_attempts: int = Field(default=2, ge=0, le=5)

# Migration
class MigrationCreateRequest(BaseModel):
    snapshot_id: str
    source_version: str = "2.7.18"
    target_version: str = "3.2.0"
    patch_strategy: str = "deterministic"  # deterministic, model_qwen, hybrid

class MigrationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: str
    snapshot_id: str
    source_version: str
    target_version: str
    status: str
    patch_strategy: str
    created_at: datetime
    updated_at: datetime
    plan: Optional[MigrationPlanResponse] = None
    patch: Optional[PatchArtifactResponse] = None
    verification_runs: List[VerificationRunResponse] = []

# Evaluation & Benchmark
class EvaluationCreateRequest(BaseModel):
    name: str
    system_type: str
    dataset_name: str = "spring_boot_held_out"
    sample_count: int = 10

class EvaluationExperimentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    system_type: str
    dataset_name: str
    sample_count: int
    metrics: Dict[str, Any]
    created_at: datetime

# Rule
class RuleResponse(BaseModel):
    rule_id: str
    title: str
    category: str
    source_version_constraint: str
    target_version_constraint: str
    description: str
    affected_pattern: str
    doc_url: str
    doc_provenance: str
    expected_behavior: str
    required_validation_tests: List[str]
    known_limitations: str
    confidence: str

# GitHub & Rollback Schemas
class GitHubRepoItem(BaseModel):
    id: int
    name: str
    full_name: str
    default_branch: str
    private: bool
    clone_url: str
    description: Optional[str] = ""

class GitHubImportRequest(BaseModel):
    repo_url: str
    branch: Optional[str] = "main"

class GitHubPRRequest(BaseModel):
    owner: str
    repo: str
    base_branch: Optional[str] = "main"
    title: Optional[str] = None

class GitHubPRResponse(BaseModel):
    pr_url: Optional[str] = None
    pr_number: Optional[int] = None
    head_branch: str
    base_branch: str
    verification_passed: bool

class RollbackRequest(BaseModel):
    reason: Optional[str] = ""

class RollbackResponse(BaseModel):
    status: str
    restored_files: List[str]
    migration_id: str
    message: str
