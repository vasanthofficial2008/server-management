import sys
import uuid
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

def test_domains_unauthenticated_denied():
    res = client.get("/api/domains")
    assert res.status_code == 401

def test_create_and_validate_domain_mapping():
    headers = get_auth_headers()
    dom_name = f"app-{uuid.uuid4().hex[:6]}.example.com"

    # Validate mapping endpoint
    val_res = client.post("/api/domains/validate", json={
        "domain_name": dom_name,
        "local_host": "127.0.0.1",
        "local_port": 3000
    }, headers=headers)
    assert val_res.status_code == 200
    assert val_res.json()["valid"] == True

    # Create domain mapping
    create_res = client.post("/api/domains", json={
        "domain_name": dom_name,
        "subdomain": "app",
        "local_host": "127.0.0.1",
        "local_port": 3000,
        "https_enabled": True
    }, headers=headers)
    assert create_res.status_code == 201
    data = create_res.json()
    assert data["domain_name"] == dom_name
    assert data["local_port"] == 3000
    assert data["tunnel_status"] == "connected"

    dom_id = data["id"]

    # Delete created domain
    del_res = client.delete(f"/api/domains/{dom_id}", headers=headers)
    assert del_res.status_code == 204

def test_duplicate_domain_assignment_rejection():
    headers = get_auth_headers()
    dup_name = f"dup-{uuid.uuid4().hex[:6]}.example.com"

    # Create first domain binding
    res1 = client.post("/api/domains", json={
        "domain_name": dup_name,
        "local_port": 8000
    }, headers=headers)
    assert res1.status_code == 201
    dom_id = res1.json()["id"]

    try:
        # Second attempt with identical domain name should trigger 400 Bad Request
        res2 = client.post("/api/domains", json={
            "domain_name": dup_name,
            "local_port": 8001
        }, headers=headers)
        assert res2.status_code == 400
        assert "already assigned" in res2.json()["detail"].lower()
    finally:
        client.delete(f"/api/domains/{dom_id}", headers=headers)

def test_cloudflare_tunnel_status_reload_restart_and_audit():
    headers = get_auth_headers()

    # Get tunnel status
    status_res = client.get("/api/domains/tunnel/status", headers=headers)
    assert status_res.status_code == 200
    status_data = status_res.json()
    assert "tunnel_id" in status_data
    assert "active_routes_count" in status_data
    # Ensure sensitive tokens are NOT exposed
    assert "api_token" not in status_data
    assert "secret" not in status_data

    # Reload tunnel
    reload_res = client.post("/api/domains/tunnel/reload", headers=headers)
    assert reload_res.status_code == 200

    # Restart tunnel
    restart_res = client.post("/api/domains/tunnel/restart", headers=headers)
    assert restart_res.status_code == 200

    # Verify audit logs for domain and tunnel events
    db = SessionLocal()
    try:
        logs = db.query(AuditLog).order_by(AuditLog.id.desc()).limit(20).all()
        actions = [l.action for l in logs]
        assert "TUNNEL_RELOAD" in actions
        assert "TUNNEL_RESTART" in actions
    finally:
        db.close()
