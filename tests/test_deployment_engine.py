import sys
import uuid
import pytest
from pathlib import Path
from fastapi.testclient import TestClient

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from backend.app.main import app
from backend.app.database import SessionLocal
from backend.app.services.executor import run_controlled_command, validate_command_string, validate_safe_path
from backend.app.services.deploy_engine import deploy_lock_manager

client = TestClient(app)

def get_auth_headers():
    res = client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
    if res.status_code == 200:
        token = res.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}
    return {}

def test_successful_deployment_workflow():
    headers = get_auth_headers()
    proj_name = f"DeploySuccessApp_{uuid.uuid4().hex[:6]}"

    # Create project with safe build command
    create_res = client.post("/api/projects", json={
        "name": proj_name,
        "app_type": "Static HTML/CSS/JavaScript",
        "port": 8098,
        "build_command": "echo Build OK",
        "restart_command": "python -c \"print('Restart OK')\""
    }, headers=headers)
    assert create_res.status_code == 201
    proj_id = create_res.json()["id"]

    # Trigger deployment
    dep_res = client.post("/api/deployments", json={"project_id": proj_id}, headers=headers)
    assert dep_res.status_code == 201
    data = dep_res.json()
    assert data["status"] == "success"
    assert "previous_commit" in data
    assert "new_commit" in data
    assert "started_at" in data
    assert "completed_at" in data
    assert data["completed_at"] is not None
    assert "Build OK" in data["log"]

def test_failed_deployment_workflow_no_false_success():
    headers = get_auth_headers()
    proj_name = f"DeployFailApp_{uuid.uuid4().hex[:6]}"
    failing_cmd = "python -m non_existent_module_xyz"

    # Create project with failing build command
    create_res = client.post("/api/projects", json={
        "name": proj_name,
        "app_type": "Python Custom",
        "port": 8099,
        "build_command": failing_cmd
    }, headers=headers)
    assert create_res.status_code == 201
    proj_id = create_res.json()["id"]

    # Trigger deployment
    dep_res = client.post("/api/deployments", json={"project_id": proj_id}, headers=headers)
    assert dep_res.status_code == 201
    data = dep_res.json()
    assert data["status"] == "failed"
    assert data["error_message"] is not None
    assert "Build command failed with exit code 1" in data["error_message"]
    assert "DEPLOYMENT FAILED" in data["log"]

def test_concurrency_project_locking():
    headers = get_auth_headers()
    proj_name = f"LockApp_{uuid.uuid4().hex[:6]}"

    create_res = client.post("/api/projects", json={
        "name": proj_name,
        "app_type": "Python FastAPI",
        "port": 8100
    }, headers=headers)
    assert create_res.status_code == 201
    proj_id = create_res.json()["id"]

    # Manually acquire lock
    assert deploy_lock_manager.acquire(proj_id) == True

    try:
        # Concurrent request should be blocked with 409 Conflict
        dep_res = client.post("/api/deployments", json={"project_id": proj_id}, headers=headers)
        assert dep_res.status_code == 409
        assert "already in progress" in dep_res.json()["detail"]
    finally:
        deploy_lock_manager.release(proj_id)

def test_command_injection_safety():
    # Metacharacter injection attempt should raise ValueError
    with pytest.raises(ValueError) as exc:
        validate_command_string("python main.py $(rm -rf /)")
    assert "Forbidden shell metacharacter" in str(exc.value)

    with pytest.raises(ValueError) as exc:
        validate_command_string("echo `whoami`")
    assert "Forbidden shell metacharacter" in str(exc.value)

    # Path traversal attempt should raise ValueError
    with pytest.raises(ValueError) as exc:
        validate_safe_path("../../etc/passwd")
    assert "forbidden" in str(exc.value).lower()
