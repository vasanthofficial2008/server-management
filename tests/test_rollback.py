import sys
import uuid
from pathlib import Path
from fastapi.testclient import TestClient

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from backend.app.main import app
from backend.app.database import SessionLocal
from backend.app.models.audit import AuditLog
from backend.app.services.deploy_engine import deploy_lock_manager

client = TestClient(app)

def get_auth_headers():
    res = client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
    if res.status_code == 200:
        token = res.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}
    return {}

def test_rollback_unauthenticated_denied():
    res = client.post("/api/deployments/rollback", json={"deployment_id": 1})
    assert res.status_code == 401

def test_successful_rollback_workflow():
    headers = get_auth_headers()
    proj_name = f"RollbackApp_{uuid.uuid4().hex[:6]}"

    # Create project
    create_res = client.post("/api/projects", json={
        "name": proj_name,
        "app_type": "Python FastAPI",
        "port": 8105,
        "build_command": "echo Build OK",
        "restart_command": "python -c \"print('Restart OK')\""
    }, headers=headers)
    assert create_res.status_code == 201
    proj_id = create_res.json()["id"]

    # Trigger initial successful deployment
    dep_res = client.post("/api/deployments", json={"project_id": proj_id}, headers=headers)
    assert dep_res.status_code == 201
    dep_data = dep_res.json()
    assert dep_data["status"] == "success"
    dep_id = dep_data["id"]

    # Trigger rollback targeting successful deployment
    rollback_res = client.post("/api/deployments/rollback", json={"deployment_id": dep_id}, headers=headers)
    assert rollback_res.status_code == 201
    rollback_data = rollback_res.json()

    assert rollback_data["status"] == "success"
    assert rollback_data["is_rollback"] == True
    assert rollback_data["target_rollback_commit"] is not None
    assert "Restored to commit #" in rollback_data["log"]

    # Audit log check
    db = SessionLocal()
    try:
        logs = db.query(AuditLog).order_by(AuditLog.id.desc()).limit(20).all()
        actions = [l.action for l in logs]
        assert "DEPLOYMENT_ROLLBACK_SUCCESS" in actions
    finally:
        db.close()

def test_rollback_concurrency_locking():
    headers = get_auth_headers()
    proj_name = f"RollbackLockApp_{uuid.uuid4().hex[:6]}"

    create_res = client.post("/api/projects", json={
        "name": proj_name,
        "app_type": "Python FastAPI",
        "port": 8106
    }, headers=headers)
    assert create_res.status_code == 201
    proj_id = create_res.json()["id"]

    dep_res = client.post("/api/deployments", json={"project_id": proj_id}, headers=headers)
    dep_id = dep_res.json()["id"]

    # Manually acquire deployment lock
    assert deploy_lock_manager.acquire(proj_id) == True

    try:
        # Concurrent rollback attempt should trigger HTTP 409 Conflict
        res = client.post("/api/deployments/rollback", json={"deployment_id": dep_id}, headers=headers)
        assert res.status_code == 409
        assert "already in progress" in res.json()["detail"]
    finally:
        deploy_lock_manager.release(proj_id)

def test_rollback_untrusted_failed_deployment_rejection():
    headers = get_auth_headers()
    proj_name = f"RollbackRejectApp_{uuid.uuid4().hex[:6]}"

    # Create project with failing build command
    create_res = client.post("/api/projects", json={
        "name": proj_name,
        "app_type": "Python Custom",
        "port": 8107,
        "build_command": "python -m non_existent_module_xyz"
    }, headers=headers)
    assert create_res.status_code == 201
    proj_id = create_res.json()["id"]

    # Trigger deployment that fails
    dep_res = client.post("/api/deployments", json={"project_id": proj_id}, headers=headers)
    dep_data = dep_res.json()
    assert dep_data["status"] == "failed"
    failed_dep_id = dep_data["id"]

    # Attempt rollback to failed release without force flag should be rejected with 400 Bad Request
    res = client.post("/api/deployments/rollback", json={"deployment_id": failed_dep_id}, headers=headers)
    assert res.status_code == 400
    assert "rejected" in res.json()["detail"].lower()
