import os
import pytest
from fastapi.testclient import TestClient
from apps.api.main import app
from apps.api.database import init_db

init_db()
client = TestClient(app)

def test_root_endpoint():
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "PatchPilot API"
    assert data["status"] == "online"
    assert "/docs" in data["documentation"]

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "PatchPilot"

def test_get_rules_registry():
    response = client.get("/api/rules")
    assert response.status_code == 200
    rules = response.json()
    assert len(rules) >= 5
    assert any(r["rule_id"] == "RULE-JAKARTA-EE-PERSISTENCE" for r in rules)

def test_project_lifecycle_and_migration():
    # 1. Create project
    p_res = client.post("/api/projects", json={"name": "Customer Service Migration", "description": "Spring Boot 2 to 3"})
    assert p_res.status_code == 201
    proj_id = p_res.json()["id"]

    # 2. Register fixture repository
    fixture_path = os.path.abspath("datasets/fixtures/customer-service-sb2")
    r_res = client.post(f"/api/projects/{proj_id}/repositories", json={"local_path": fixture_path})
    assert r_res.status_code == 200
    snap = r_res.json()
    assert snap["build_system"] == "maven"
    assert snap["spring_boot_version"] == "2.7.18"
    snap_id = snap["id"]

    # 3. Analyze repository
    a_res = client.post(f"/api/projects/{proj_id}/analyze")
    assert a_res.status_code == 200
    analysis = a_res.json()
    assert analysis["total_migration_sites"] > 0
    assert "RULE-JAKARTA-EE-PERSISTENCE" in analysis["rules_detected"]

    # 4. Create Migration (Generate Plan & Diff)
    m_res = client.post(f"/api/projects/{proj_id}/migrations", json={
        "snapshot_id": snap_id,
        "source_version": "2.7.18",
        "target_version": "3.2.0",
        "patch_strategy": "deterministic"
    })
    assert m_res.status_code == 201
    mig = m_res.json()
    mig_id = mig["id"]
    assert mig["status"] == "GENERATED"
    assert mig["plan"] is not None
    assert mig["patch"] is not None
    assert mig["patch"]["changed_files_count"] > 0
    assert "jakarta.persistence" in mig["patch"]["unified_diff"]

    # 5. Fetch Plan & Diff directly
    plan_res = client.get(f"/api/migrations/{mig_id}/plan")
    assert plan_res.status_code == 200
    diff_res = client.get(f"/api/migrations/{mig_id}/diff")
    assert diff_res.status_code == 200

    # 6. Verify Migration
    v_res = client.post(f"/api/migrations/{mig_id}/verify", json={"max_repair_attempts": 2})
    assert v_res.status_code == 200
    vrun = v_res.json()
    assert vrun["status"] == "PASSED"
    assert vrun["compile_success"] is True
    assert vrun["test_success"] is True

    # Check updated migration status
    mig_updated = client.get(f"/api/migrations/{mig_id}").json()
    assert mig_updated["status"] == "VERIFIED_PASSED"

    # 7. Approve Patch
    app_res = client.post(f"/api/migrations/{mig_id}/approve", json={"reviewer_name": "SeniorDev", "notes": "Approved for release"})
    assert app_res.status_code == 200
    assert app_res.json()["review_status"] == "APPROVED"

    # 8. Check audit events
    events_res = client.get(f"/api/migrations/{mig_id}/events")
    assert events_res.status_code == 200
    events = events_res.json()
    assert len(events) >= 3
