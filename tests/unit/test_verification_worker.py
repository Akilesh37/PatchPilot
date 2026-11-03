import os
import shutil
import tempfile
import pytest
from services.verification_worker.worker import VerificationWorker, CommandSecurityError
from services.verification_worker.repair_loop import DiagnosticRepairLoop
from ml.inference.model_provider import MockCodeModelProvider

def test_command_security_policy():
    worker = VerificationWorker()

    # Allowed commands
    worker.validate_command(["mvn", "test", "-DskipTests=false"])
    worker.validate_command(["mvn", "test-compile"])

    # Disallowed commands
    with pytest.raises(CommandSecurityError):
        worker.validate_command(["rm", "-rf", "/"])

    # Shell injection attempts
    with pytest.raises(CommandSecurityError):
        worker.validate_command(["mvn", "test; rm -rf /"])

    with pytest.raises(CommandSecurityError):
        worker.validate_command(["mvn", "test | cat /etc/passwd"])

def test_verification_on_sb3_fixture():
    fixture_dir = os.path.abspath("datasets/fixtures/customer-service-sb3")
    assert os.path.exists(fixture_dir)

    worker = VerificationWorker(timeout_seconds=60)
    outcome = worker.run_check(fixture_dir)

    assert outcome.status == "PASSED"
    assert outcome.compile_success is True
    assert outcome.test_success is True
    assert outcome.exit_code == 0

def test_diagnostic_repair_loop_fixes_error():
    fixture_dir = os.path.abspath("datasets/fixtures/customer-service-sb3")

    with tempfile.TemporaryDirectory() as tmpdir:
        working_copy = os.path.join(tmpdir, "workspace")
        shutil.copytree(fixture_dir, working_copy)

        # Introduce an intentional compilation error: inject a javax import into Customer.java
        customer_file = os.path.join(working_copy, "src/main/java/com/example/customer/model/Customer.java")
        with open(customer_file, "r") as f:
            code = f.read()

        broken_code = code.replace("import jakarta.persistence.", "import javax.persistence.")
        with open(customer_file, "w") as f:
            f.write(broken_code)

        worker = VerificationWorker(timeout_seconds=60)
        initial_outcome = worker.run_check(working_copy)

        # Initial check must fail
        assert initial_outcome.status == "FAILED"
        assert initial_outcome.compile_success is False
        assert len(initial_outcome.diagnostics) > 0

        # Now run bounded diagnostic repair loop
        model = MockCodeModelProvider()
        loop = DiagnosticRepairLoop(worker=worker, max_attempts=2)
        repair_result = loop.execute_repair(working_copy, initial_outcome, model)

        assert repair_result.repaired is True
        assert repair_result.total_attempts >= 1
        assert repair_result.final_outcome.status == "PASSED"
