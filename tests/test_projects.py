import sys
import uuid
from pathlib import Path
from fastapi.testclient import TestClient

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from backend.app.main import app

client = TestClient(app)

def get_auth_headers():
    res = client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
    if res.status_code == 200:
        token = res.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}
    return {}

def test_list_projects():
    headers = get_auth_headers()
    response = client.get("/api/projects", headers=headers)
    assert response.status_code == 200
    assert isinstance(response.json(), list)

def test_create_and_delete_project():
    headers = get_auth_headers()
    unique_name = f"Test Project {uuid.uuid4().hex[:6]}"
    create_res = client.post("/api/projects", json={
        "name": unique_name,
        "description": "Automated test project",
        "repo_url": "https://github.com/test/repo.git",
        "branch": "main",
        "framework": "Python/FastAPI",
        "port": 9090
    }, headers=headers)
    assert create_res.status_code == 201
    proj = create_res.json()
    assert proj["name"] == unique_name
    proj_id = proj["id"]

    # Delete project
    del_res = client.delete(f"/api/projects/{proj_id}", headers=headers)
    assert del_res.status_code == 204
