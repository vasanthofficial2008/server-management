import sys
from pathlib import Path
from fastapi.testclient import TestClient

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from backend.app.main import app
from backend.app.database import SessionLocal
from backend.app.models.audit import AuditLog

client = TestClient(app)

def get_auth_headers():
    res = client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
    if res.status_code == 200:
        token = res.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}
    return {}

def test_list_systemd_services():
    headers = get_auth_headers()
    response = client.get("/api/services", headers=headers)
    assert response.status_code == 200
    services = response.json()
    assert isinstance(services, list)
    assert len(services) > 0

def test_systemd_service_actions_and_audit():
    headers = get_auth_headers()
    list_res = client.get("/api/services", headers=headers)
    srv_id = list_res.json()[0]["id"]

    # Test actions
    for action in ["stop", "start", "restart", "reload", "disable", "enable"]:
        res = client.post(f"/api/services/{srv_id}/action", json={"action": action}, headers=headers)
        assert res.status_code == 200
        assert "status" in res.json()

    # Query audit logs endpoint to verify audit logging
    audit_res = client.get("/api/server/audit-logs", headers=headers)
    assert audit_res.status_code == 200
    actions = [a["action"] for a in audit_res.json()]
    assert "SERVICE_START" in actions
    assert "SERVICE_STOP" in actions
    assert "SERVICE_RESTART" in actions

def test_unregistered_service_whitelist_rejection():
    headers = get_auth_headers()
    # Non-existent service ID 999999
    res = client.post("/api/services/999999/action", json={"action": "start"}, headers=headers)
    assert res.status_code == 404
    assert "whitelist" in res.json()["detail"].lower() or "not registered" in res.json()["detail"].lower()

def test_invalid_service_action_rejection():
    headers = get_auth_headers()
    list_res = client.get("/api/services", headers=headers)
    srv_id = list_res.json()[0]["id"]

    res = client.post(f"/api/services/{srv_id}/action", json={"action": "malicious_hack_action"}, headers=headers)
    assert res.status_code == 422

def test_service_status_and_logs_endpoints():
    headers = get_auth_headers()
    list_res = client.get("/api/services", headers=headers)
    srv_id = list_res.json()[0]["id"]

    # Test status endpoint
    status_res = client.get(f"/api/services/{srv_id}/status", headers=headers)
    assert status_res.status_code == 200
    assert "status_output" in status_res.json()

    # Test logs endpoint
    logs_res = client.get(f"/api/services/{srv_id}/logs", headers=headers)
    assert logs_res.status_code == 200
    assert "logs" in logs_res.json()
