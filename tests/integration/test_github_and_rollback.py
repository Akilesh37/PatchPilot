import pytest
from fastapi.testclient import TestClient
from apps.api.main import app
from services.github_service import GitHubService

client = TestClient(app)

def test_github_token_sanitization():
    raw_token = "ghp_123456789012345678901234567890123456"
    text_with_token = f"Cloning https://user:secret_pass@github.com/org/repo.git failed with {raw_token}"
    sanitized = GitHubService.sanitize_token(text_with_token)

    assert raw_token not in sanitized
    assert "ghp_[REDACTED]" in sanitized
    assert "[TOKEN_REDACTED]" in sanitized

def test_github_pr_markdown_generation():
    report = GitHubService.generate_pr_markdown_report(
        migration_id="mig-test1234",
        rules_applied=["RULE-JAKARTA-EE-PERSISTENCE", "RULE-CONFIG-REDIS-PREFIX"],
        verification_passed=True,
        verification_details={"compile_success": True, "test_success": True, "duration_ms": 1200},
        evidence_citations=[{
            "doc_title": "Spring Boot 3.0 Migration Guide",
            "section_title": "Jakarta EE",
            "canonical_url": "https://example.com/sb3",
            "snippet": "javax to jakarta"
        }],
        diff_summary="@@ -1,3 +1,3 @@"
    )

    assert "mig-test1234" in report
    assert "VERIFIED PASSED" in report
    assert "RULE-JAKARTA-EE-PERSISTENCE" in report
    assert "https://example.com/sb3" in report
    assert "git revert HEAD" in report

def test_github_endpoints_require_token():
    # Without token
    resp = client.get("/api/github/repositories")
    assert resp.status_code == 401
    assert "GitHub token required" in resp.json()["detail"]

def test_migration_lifecycle_and_rollback():
    # 1. Create project
    proj_resp = client.post("/api/projects", json={"name": "Rollback Test Project"})
    assert proj_resp.status_code == 201
    proj_id = proj_resp.json()["id"]

    # 2. Register repository
    repo_resp = client.post(
        f"/api/projects/{proj_id}/repositories",
        json={"local_path": "datasets/fixtures/order-service-sb2"}
    )
    assert repo_resp.status_code == 200
    snap_id = repo_resp.json()["id"]

    # 3. Create migration
    mig_resp = client.post(
        f"/api/projects/{proj_id}/migrations",
        json={"snapshot_id": snap_id, "source_version": "2.7.18", "target_version": "3.2.0"}
    )
    assert mig_resp.status_code == 201
    mig_id = mig_resp.json()["id"]
    assert mig_resp.json()["status"] == "GENERATED"

    # 4. Trigger rollback
    rb_resp = client.post(f"/api/migrations/{mig_id}/rollback", json={"reason": "User testing rollback"})
    assert rb_resp.status_code == 200
    assert rb_resp.json()["status"] == "ROLLED_BACK"
    assert rb_resp.json()["migration_id"] == mig_id
    assert len(rb_resp.json()["restored_files"]) > 0

    # 5. Check migration status
    get_mig = client.get(f"/api/migrations/{mig_id}")
    assert get_mig.status_code == 200
    assert get_mig.json()["status"] == "ROLLED_BACK"
