import os
import tempfile
import pytest
from migration_engine.patching.patch_synthesizer import PatchSynthesizer, PatchValidationError
from services.verification_worker.repair_loop import DiagnosticRepairLoop
from services.verification_worker.worker import VerificationOutcome, DiagnosticFinding
from ml.inference.model_provider import MockCodeModelProvider

def test_checkpoint_atomic_rollback_on_failure():
    with tempfile.TemporaryDirectory() as tmp_dir:
        f1 = os.path.join(tmp_dir, "ServiceA.java")
        f2 = os.path.join(tmp_dir, "ServiceB.java")

        with open(f1, "w") as f:
            f.write("original content A")
        with open(f2, "w") as f:
            f.write("original content B")

        # 1. Create checkpoint
        checkpoint = PatchSynthesizer.create_checkpoint(tmp_dir, ["ServiceA.java", "ServiceB.java"])
        assert checkpoint.file_snapshots["ServiceA.java"] == "original content A"

        # 2. Modify files
        with open(f1, "w") as f:
            f.write("corrupted content A")
        with open(f2, "w") as f:
            f.write("corrupted content B")

        # 3. Restore checkpoint
        restored = checkpoint.restore()
        assert len(restored) == 2

        with open(f1, "r") as f:
            assert f.read() == "original content A"
        with open(f2, "r") as f:
            assert f.read() == "original content B"

def test_atomic_patch_conflict_marker_rejection():
    with tempfile.TemporaryDirectory() as tmp_dir:
        f1 = os.path.join(tmp_dir, "ServiceA.java")
        with open(f1, "w") as f:
            f.write("original content A")

        conflict_content = """<<<<<<< HEAD
some code
=======
other code
>>>>>>> branch"""

        with pytest.raises(PatchValidationError) as exc:
            PatchSynthesizer.apply_patch_atomic(tmp_dir, {"ServiceA.java": conflict_content})

        assert "Merge conflict marker detected" in str(exc.value)
        # Original content must remain intact
        with open(f1, "r") as f:
            assert f.read() == "original content A"

def test_failure_classification():
    compile_fail = VerificationOutcome(
        status="FAILED",
        exit_code=1,
        duration_ms=100,
        compile_success=False,
        test_success=False,
        logs="error",
        diagnostics=[DiagnosticFinding("compilation", message="cannot find symbol")]
    )
    assert DiagnosticRepairLoop.classify_failure(compile_fail) == "COMPILATION_ERROR"

    test_fail = VerificationOutcome(
        status="FAILED",
        exit_code=1,
        duration_ms=100,
        compile_success=True,
        test_success=False,
        logs="error",
        diagnostics=[DiagnosticFinding("test_failure", message="AssertionFailedError")]
    )
    assert DiagnosticRepairLoop.classify_failure(test_fail) == "TEST_FAILURE"

