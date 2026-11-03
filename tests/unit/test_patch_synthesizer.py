import os
import tempfile
import pytest
from migration_engine.patching.patch_synthesizer import PatchSynthesizer, PatchValidationError

def test_path_safety_validation():
    repo_dir = "/tmp/repo"
    # Valid relative paths
    assert PatchSynthesizer.validate_relative_path(repo_dir, "src/main/App.java") == "/tmp/repo/src/main/App.java"
    assert PatchSynthesizer.validate_relative_path(repo_dir, "pom.xml") == "/tmp/repo/pom.xml"

    # Traversal attempts must raise PatchValidationError
    with pytest.raises(PatchValidationError):
        PatchSynthesizer.validate_relative_path(repo_dir, "../etc/passwd")

    with pytest.raises(PatchValidationError):
        PatchSynthesizer.validate_relative_path(repo_dir, "/etc/passwd")

    with pytest.raises(PatchValidationError):
        PatchSynthesizer.validate_relative_path(repo_dir, ".git/config")

def test_unified_diff_generation():
    orig = "import javax.persistence.Entity;\npublic class Item {}\n"
    mod = "import jakarta.persistence.Entity;\npublic class Item {}\n"
    diff = PatchSynthesizer.generate_unified_diff("Item.java", orig, mod)

    assert "--- a/Item.java" in diff
    assert "+++ b/Item.java" in diff
    assert "-import javax.persistence.Entity;" in diff
    assert "+import jakarta.persistence.Entity;" in diff

def test_atomic_patch_application_and_rollback():
    with tempfile.TemporaryDirectory() as tmp_dir:
        test_file = os.path.join(tmp_dir, "App.java")
        with open(test_file, "w") as f:
            f.write("original code")

        # 1. Successful atomic patch
        success, changed, checkpoint = PatchSynthesizer.apply_patch_atomic(
            tmp_dir,
            {"App.java": "updated code"}
        )
        assert success
        assert "App.java" in changed

        with open(test_file, "r") as f:
            assert f.read() == "updated code"

        # 2. Rollback to checkpoint
        checkpoint.restore()
        with open(test_file, "r") as f:
            assert f.read() == "original code"
