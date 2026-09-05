import sys
from pathlib import Path
from fastapi.testclient import TestClient

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from backend.app.main import app

client = TestClient(app)

def test_login_invalid_credentials():
    response = client.post("/api/auth/login", json={"username": "nonexistent", "password": "wrongpassword"})
    assert response.status_code == 401

def test_get_me_unauthenticated():
    response = client.get("/api/auth/me")
    assert response.status_code == 401
