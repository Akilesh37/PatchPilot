import os
import shutil
import subprocess
import tempfile
import pytest
from migration_engine.recipes.deterministic_engine import DeterministicMigrationEngine

def test_deterministic_engine_migration_customer_service():
    fixture_dir = os.path.abspath("datasets/fixtures/customer-service-sb2")
    assert os.path.exists(fixture_dir), "customer-service-sb2 fixture must exist"

    with tempfile.TemporaryDirectory() as tmpdir:
        working_copy = os.path.join(tmpdir, "worktree")
        shutil.copytree(fixture_dir, working_copy)

        engine = DeterministicMigrationEngine()
        results = engine.migrate_directory(working_copy)

        assert results["total_files_modified"] > 0
        assert any("Customer.java" in f for f in results["changed_files"])
        assert any("CustomerController.java" in f for f in results["changed_files"])
        assert any("pom.xml" in f for f in results["changed_files"])

        # Check content in migrated Customer.java
        customer_file = os.path.join(working_copy, "src/main/java/com/example/customer/model/Customer.java")
        with open(customer_file) as f:
            content = f.read()
        assert "import jakarta.persistence." in content
        assert "import javax.persistence." not in content
        assert "import jakarta.validation." in content
        assert "import javax.validation." not in content

        # Check pom.xml
        pom_file = os.path.join(working_copy, "pom.xml")
        with open(pom_file) as f:
            pom_content = f.read()
        assert "<spring.boot.version>3.2.0</spring.boot.version>" in pom_content
        assert "jakarta.persistence-api" in pom_content

        # Run Maven test on the migrated project
        mvn_run = subprocess.run(
            ["mvn", "test", "-DskipTests=false"],
            cwd=working_copy,
            capture_output=True,
            text=True,
            timeout=60
        )
        assert mvn_run.returncode == 0, f"Migrated project failed to build: {mvn_run.stdout}\n{mvn_run.stderr}"
        assert "BUILD SUCCESS" in mvn_run.stdout

def test_deterministic_engine_migration_order_service():
    fixture_dir = os.path.abspath("datasets/fixtures/order-service-sb2")
    assert os.path.exists(fixture_dir), "order-service-sb2 fixture must exist"

    with tempfile.TemporaryDirectory() as tmpdir:
        working_copy = os.path.join(tmpdir, "worktree")
        shutil.copytree(fixture_dir, working_copy)

        engine = DeterministicMigrationEngine()
        results = engine.migrate_directory(working_copy)

        assert results["total_files_modified"] > 0
        order_service_file = os.path.join(working_copy, "src/main/java/com/example/order/OrderService.java")
        with open(order_service_file) as f:
            content = f.read()
        assert "import jakarta.annotation." in content
        assert "import javax.annotation." not in content
