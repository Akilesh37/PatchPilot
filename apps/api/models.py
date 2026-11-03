"""
SQLAlchemy database models for PatchPilot.
Strictly compatible with Python 3.12+ timezone-aware UTC datetimes.
"""
import datetime
from sqlalchemy import (
    Column, String, Integer, DateTime, Text, ForeignKey, JSON, Float, Boolean
)
from sqlalchemy.orm import relationship
from apps.api.database import Base

def utc_now():
    return datetime.datetime.now(datetime.timezone.utc)

class Project(Base):
    __tablename__ = "projects"

    id = Column(String(64), primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, default="")
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    snapshots = relationship("RepositorySnapshot", back_populates="project", cascade="all, delete-orphan")
    migrations = relationship("Migration", back_populates="project", cascade="all, delete-orphan")
    audit_events = relationship("AuditEvent", back_populates="project", cascade="all, delete-orphan")

class RepositorySnapshot(Base):
    __tablename__ = "repository_snapshots"

    id = Column(String(64), primary_key=True, index=True)
    project_id = Column(String(64), ForeignKey("projects.id"), nullable=False)
    repo_path = Column(String(512), nullable=False)
    archive_hash = Column(String(64), default="")
    detected_language = Column(String(64), default="java")
    build_system = Column(String(64), default="maven")
    spring_boot_version = Column(String(64), default="")
    java_version = Column(String(64), default="")
    total_files = Column(Integer, default=0)
    total_migration_sites = Column(Integer, default=0)
    file_manifest = Column(JSON, default=dict)
    created_at = Column(DateTime, default=utc_now)

    project = relationship("Project", back_populates="snapshots")
    migrations = relationship("Migration", back_populates="snapshot")

class Migration(Base):
    __tablename__ = "migrations"

    id = Column(String(64), primary_key=True, index=True)
    project_id = Column(String(64), ForeignKey("projects.id"), nullable=False)
    snapshot_id = Column(String(64), ForeignKey("repository_snapshots.id"), nullable=False)
    source_version = Column(String(64), default="2.7.18")
    target_version = Column(String(64), default="3.2.0")
    status = Column(String(64), default="PENDING")
    patch_strategy = Column(String(64), default="deterministic")
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    project = relationship("Project", back_populates="migrations")
    snapshot = relationship("RepositorySnapshot", back_populates="migrations")
    plan = relationship("MigrationPlan", uselist=False, back_populates="migration", cascade="all, delete-orphan")
    patch = relationship("PatchArtifact", uselist=False, back_populates="migration", cascade="all, delete-orphan")
    verification_runs = relationship("VerificationRun", back_populates="migration", cascade="all, delete-orphan")

class MigrationPlan(Base):
    __tablename__ = "migration_plans"

    id = Column(String(64), primary_key=True, index=True)
    migration_id = Column(String(64), ForeignKey("migrations.id"), nullable=False, unique=True)
    goal = Column(Text, nullable=False)
    affected_files = Column(JSON, default=list)
    applicable_rule_ids = Column(JSON, default=list)
    evidence_references = Column(JSON, default=list)
    risks = Column(JSON, default=list)
    validation_steps = Column(JSON, default=list)
    ambiguities = Column(JSON, default=list)
    created_at = Column(DateTime, default=utc_now)

    migration = relationship("Migration", back_populates="plan")

class PatchArtifact(Base):
    __tablename__ = "patch_artifacts"

    id = Column(String(64), primary_key=True, index=True)
    migration_id = Column(String(64), ForeignKey("migrations.id"), nullable=False, unique=True)
    unified_diff = Column(Text, nullable=False)
    changed_files_count = Column(Integer, default=0)
    file_diffs = Column(JSON, default=dict)
    applied_rules = Column(JSON, default=list)
    review_status = Column(String(64), default="PENDING_REVIEW")
    approved_by = Column(String(128), nullable=True)
    approval_notes = Column(Text, nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=utc_now)

    migration = relationship("Migration", back_populates="patch")

class VerificationRun(Base):
    __tablename__ = "verification_runs"

    id = Column(String(64), primary_key=True, index=True)
    migration_id = Column(String(64), ForeignKey("migrations.id"), nullable=False)
    attempt_number = Column(Integer, default=1)
    status = Column(String(64), default="NOT_VERIFIED")
    exit_code = Column(Integer, default=-1)
    duration_ms = Column(Integer, default=0)
    logs = Column(Text, default="")
    compile_success = Column(Boolean, default=False)
    test_success = Column(Boolean, default=False)
    failed_tests = Column(JSON, default=list)
    repair_triggered = Column(Boolean, default=False)
    repair_succeeded = Column(Boolean, default=False)
    diagnostics = Column(JSON, default=dict)
    created_at = Column(DateTime, default=utc_now)

    migration = relationship("Migration", back_populates="verification_runs")

class EvaluationExperiment(Base):
    __tablename__ = "evaluation_experiments"

    id = Column(String(64), primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    system_type = Column(String(64), nullable=False)
    dataset_name = Column(String(128), default="spring_boot_held_out")
    sample_count = Column(Integer, default=0)
    metrics = Column(JSON, default=dict)
    created_at = Column(DateTime, default=utc_now)

class AuditEvent(Base):
    __tablename__ = "audit_events"

    id = Column(String(64), primary_key=True, index=True)
    project_id = Column(String(64), ForeignKey("projects.id"), nullable=True)
    migration_id = Column(String(64), nullable=True)
    event_type = Column(String(128), nullable=False)
    details = Column(JSON, default=dict)
    timestamp = Column(DateTime, default=utc_now)

    project = relationship("Project", back_populates="audit_events")
