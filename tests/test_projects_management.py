import sys
import uuid
from pathlib import Path
from fastapi.testclient import TestClient

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from backend.app.main import app
from backend.app.schemas.project import ALLOWED_APP_TYPES

client = TestClient(app)

def get_auth_headers():
    res = client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
    if res.status_code == 200:
        token = res.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}
    return {}

def test_create_project_all_app_types():
    headers = get_auth_headers()

    for app_type in ALLOWED_APP_TYPES:
        name = f"TestApp_{uuid.uuid4().hex[:6]}"
        res = client.post("/api/projects", json={
            "name": name,
            "app_type": app_type,
            "branch": "main",
            "port": 8090
        }, headers=headers)

        assert res.status_code == 201, f"Failed for app_type {app_type}: {res.text}"
        data = res.json()
        assert data["name"] == name
        assert data["app_type"] == app_type
        assert data["start_command"] is not None
        assert data["build_command"] is not None
        assert "deployment_directory" in data

def test_path_traversal_rejection():
    headers = get_auth_headers()
    name = f"TraversalApp_{uuid.uuid4().hex[:6]}"

    # Attempt directory traversal attack
    res = client.post("/api/projects", json={
        "name": name,
        "app_type": "Python FastAPI",
        "deployment_directory": "../../etc/passwd"
    }, headers=headers)

    # Should reject with HTTP 422 validation error
    assert res.status_code == 422

def test_invalid_app_type_rejection():
    headers = get_auth_headers()
    name = f"BadTypeApp_{uuid.uuid4().hex[:6]}"

    res = client.post("/api/projects", json={
        "name": name,
        "app_type": "Invalid Unsupported Framework"
    }, headers=headers)

    assert res.status_code == 422

def test_project_actions_and_logs():
    headers = get_auth_headers()
    name = f"ActionApp_{uuid.uuid4().hex[:6]}"

    create_res = client.post("/api/projects", json={
        "name": name,
        "app_type": "Python Flask",
        "port": 8095
    }, headers=headers)
    assert create_res.status_code == 201
    proj_id = create_res.json()["id"]

    # Test Restart Action
    restart_res = client.post(f"/api/projects/{proj_id}/restart", headers=headers)
    assert restart_res.status_code == 200
    assert restart_res.json()["status"] == "active"

    # Test Stop Action
    stop_res = client.post(f"/api/projects/{proj_id}/stop", headers=headers)
    assert stop_res.status_code == 200
    assert stop_res.json()["status"] == "stopped"

    # Test Deploy Action
    deploy_res = client.post(f"/api/projects/{proj_id}/deploy", headers=headers)
    assert deploy_res.status_code == 200
    assert "deployment_id" in deploy_res.json()

    # Test Logs Action
    logs_res = client.get(f"/api/projects/{proj_id}/logs", headers=headers)
    assert logs_res.status_code == 200
    assert "logs" in logs_res.json()
