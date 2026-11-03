import os
import tempfile
import pytest
from migration_engine.analyzers.source_analyzer import SourceAnalyzer
from migration_engine.planners.plan_generator import MigrationPlanGenerator
from migration_engine.recipes.deterministic_engine import DeterministicMigrationEngine

def test_structured_migration_plan_operations():
    analyzer = SourceAnalyzer()
    planner = MigrationPlanGenerator()

    java_code = """package com.example.customer;

import javax.persistence.Entity;
import javax.persistence.Id;
import javax.servlet.http.HttpServletRequest;

@Entity
public class Customer {
    @Id
    private Long id;

    public void process(HttpServletRequest req) {
    }
}
"""
    with tempfile.TemporaryDirectory() as tmp_dir:
        fpath = os.path.join(tmp_dir, "Customer.java")
        with open(fpath, "w") as f:
            f.write(java_code)

        summary = analyzer.analyze_repository(tmp_dir)
        plan = planner.generate_plan(summary, "2.7.18", "3.2.0")

        # Check plan level metadata
        assert plan.total_operations_count >= 2
        assert len(plan.operations) == plan.total_operations_count
        assert plan.deterministic_count > 0

        # Validate structure of each operation
        for op in plan.operations:
            assert op.operation_id.startswith("op-")
            assert op.rule_id in ["RULE-JAKARTA-EE-PERSISTENCE", "RULE-JAKARTA-EE-SERVLET"]
            assert op.file_path == "Customer.java"
            assert op.line_start > 0
            assert op.original_snippet != ""
            assert op.rationale != ""
            assert op.risk_classification in ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
            assert len(op.verification_requirements) > 0
            assert "strategy" in op.rollback_action
            assert "original_content" in op.rollback_action
            assert "file_sha256" in op.rollback_action

def test_planner_idempotency_detection():
    analyzer = SourceAnalyzer()
    planner = MigrationPlanGenerator()

    # Code already using jakarta
    already_migrated_code = """package com.example.customer;

import jakarta.persistence.Entity;
import jakarta.persistence.Id;

@Entity
public class Customer {
    @Id
    private Long id;
}
"""
    with tempfile.TemporaryDirectory() as tmp_dir:
        fpath = os.path.join(tmp_dir, "Customer.java")
        with open(fpath, "w") as f:
            f.write(already_migrated_code)

        summary = analyzer.analyze_repository(tmp_dir)
        plan = planner.generate_plan(summary, "2.7.18", "3.2.0")

        # Zero migration sites detected for already migrated file
        assert plan.total_operations_count == 0
        assert len(plan.affected_files) == 0

def test_deterministic_engine_idempotency():
    engine = DeterministicMigrationEngine()
    migrated_code = """package com.example.customer;

import jakarta.persistence.Entity;
import jakarta.persistence.Id;

@Entity
public class Customer {
    @Id
    private Long id;
}
"""
    transformed, applied = engine.transform_content("Customer.java", migrated_code)
    assert transformed == migrated_code
    assert len(applied) == 0

