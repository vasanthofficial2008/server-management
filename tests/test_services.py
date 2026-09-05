import sys
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

def test_list_services():
    headers = get_auth_headers()
    response = client.get("/api/services", headers=headers)
    assert response.status_code == 200
    assert isinstance(response.json(), list)

def test_get_server_stats():
    headers = get_auth_headers()
    response = client.get("/api/server/stats", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert "cpu_percent" in data
    assert "memory_percent" in data
    assert "disk_percent" in data
    assert "uptime_seconds" in data
