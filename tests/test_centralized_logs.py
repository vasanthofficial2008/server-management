import sys
from pathlib import Path
from fastapi.testclient import TestClient

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from backend.app.main import app
from backend.app.database import SessionLocal
from backend.app.models.audit import AuditLog
from backend.app.security.audit import log_audit_event

client = TestClient(app)

def get_auth_headers():
    res = client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
    if res.status_code == 200:
        token = res.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}
    return {}

def test_centralized_logs_unauthenticated_denied():
    res = client.get("/api/logs")
    assert res.status_code == 401

def test_list_centralized_logs_paginated():
    headers = get_auth_headers()
    
    # Create audit log to ensure entries exist
    db = SessionLocal()
    try:
        log_audit_event(db, action="TEST_LOG_EVENT", username="admin", details="Centralized test log verification message")
    finally:
        db.close()

    res = client.get("/api/logs?page=1&page_size=10", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert "items" in data
    assert "total" in data
    assert "page" in data
    assert "page_size" in data
    assert "total_pages" in data
    assert data["page"] == 1
    assert data["page_size"] == 10
    assert isinstance(data["items"], list)

def test_centralized_logs_category_filtering():
    headers = get_auth_headers()

    # Filter audit logs
    audit_res = client.get("/api/logs?category=audit", headers=headers)
    assert audit_res.status_code == 200
    items = audit_res.json()["items"]
    assert all(item["category"] == "audit" for item in items)

    # Filter systemd logs
    sys_res = client.get("/api/logs?category=systemd", headers=headers)
    assert sys_res.status_code == 200
    sys_items = sys_res.json()["items"]
    assert all(item["category"] == "systemd" for item in sys_items)

def test_centralized_logs_search_and_level_filtering():
    headers = get_auth_headers()

    # Search query filter
    res = client.get("/api/logs?search=Centralized", headers=headers)
    assert res.status_code == 200
    items = res.json()["items"]
    assert len(items) > 0
    assert any("Centralized" in item["message"] for item in items)

    # Level filter
    lvl_res = client.get("/api/logs?level=INFO", headers=headers)
    assert lvl_res.status_code == 200
    lvl_items = lvl_res.json()["items"]
    assert all(item["level"] == "INFO" for item in lvl_items)

def test_download_logs_endpoint():
    headers = get_auth_headers()

    download_res = client.get("/api/logs/download?category=audit", headers=headers)
    assert download_res.status_code == 200
    assert "attachment" in download_res.headers.get("Content-Disposition", "")
    assert "ServerPilot Centralized Log Export" in download_res.text

def test_path_traversal_safety_rejection():
    headers = get_auth_headers()
    
    # Attempting path traversal as parameters should be ignored/rejected safely
    res = client.get("/api/logs?search=../../etc/passwd", headers=headers)
    assert res.status_code == 200
    assert "/etc/passwd" not in res.text
