import sys
import uuid
from pathlib import Path
from fastapi.testclient import TestClient

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from backend.app.main import app
from backend.app.database import SessionLocal
from backend.app.models.audit import AuditLog
from backend.app.models.user import User
from backend.app.security.auth import get_password_hash
from backend.app.security.rate_limiter import login_limiter
from scripts.create_admin import create_admin

client = TestClient(app)

def setup_function():
    login_limiter.reset()

def teardown_function():
    login_limiter.reset()

def test_admin_creation_script_and_login():
    login_limiter.reset()
    unique_user = f"secadmin_{uuid.uuid4().hex[:6]}"
    unique_email = f"{unique_user}@example.com"
    password = "SuperSecretPassword123!"

    # Test admin creation script
    create_admin(username=unique_user, email=unique_email, password=password)

    db = SessionLocal()
    user = db.query(User).filter(User.username == unique_user).first()
    assert user is not None
    assert user.email == unique_email
    db.close()

    # Test login success
    login_res = client.post("/api/auth/login", json={"username": unique_user, "password": password})
    assert login_res.status_code == 200
    data = login_res.json()
    assert "access_token" in data
    token = data["access_token"]

    # Test protected endpoint with token
    headers = {"Authorization": f"Bearer {token}"}
    me_res = client.get("/api/auth/me", headers=headers)
    assert me_res.status_code == 200
    assert me_res.json()["username"] == unique_user

    # Test logout session revocation
    logout_res = client.post("/api/auth/logout", headers=headers)
    assert logout_res.status_code == 200

    # Test token is revoked after logout
    post_logout_me = client.get("/api/auth/me", headers=headers)
    assert post_logout_me.status_code == 401

def test_protected_endpoints_deny_unauthenticated():
    login_limiter.reset()
    assert client.get("/api/projects").status_code == 401
    assert client.get("/api/services").status_code == 401
    assert client.get("/api/deployments").status_code == 401
    assert client.get("/api/domains").status_code == 401
    assert client.get("/api/settings").status_code == 401
    assert client.get("/api/server/stats").status_code == 401

def test_login_failed_audit_and_rate_limit():
    login_limiter.reset()
    ip_headers = {"X-Forwarded-For": "192.168.88.88"}
    for _ in range(5):
        client.post("/api/auth/login", json={"username": "invalid_user", "password": "wrongpassword"}, headers=ip_headers)

    # 6th attempt should return 429 Too Many Requests
    rate_res = client.post("/api/auth/login", json={"username": "invalid_user", "password": "wrongpassword"}, headers=ip_headers)
    assert rate_res.status_code == 429
    login_limiter.reset()

def test_audit_logs_recorded():
    login_limiter.reset()
    # Login as admin to get token
    login_res = client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
    assert login_res.status_code == 200
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Perform actions
    proj_name = f"AuditProj {uuid.uuid4().hex[:4]}"
    p_res = client.post("/api/projects", json={"name": proj_name, "framework": "Python/FastAPI", "port": 7070}, headers=headers)
    assert p_res.status_code == 201
    proj_id = p_res.json()["id"]

    d_res = client.post("/api/deployments", json={"project_id": proj_id, "commit_message": "Audit test deploy"}, headers=headers)
    assert d_res.status_code == 201

    dom_res = client.post("/api/domains", json={"domain_name": f"{uuid.uuid4().hex[:4]}.audit.local", "target_port": 7070}, headers=headers)
    assert dom_res.status_code == 201

    st_res = client.post("/api/settings", json={"key": "audit_test_key", "value": "test_val", "category": "test"}, headers=headers)
    assert st_res.status_code == 200

    # Query audit logs endpoint
    audit_res = client.get("/api/server/audit-logs", headers=headers)
    assert audit_res.status_code == 200
    actions = [a["action"] for a in audit_res.json()]
    assert "PROJECT_CREATE" in actions
    assert ("DEPLOYMENT_SUCCESS" in actions or "DEPLOYMENT_FAILURE" in actions or "DEPLOYMENT_TRIGGER" in actions)
    assert "DOMAIN_CREATE" in actions
    assert "SETTINGS_UPDATE" in actions
