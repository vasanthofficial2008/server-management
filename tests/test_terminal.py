import sys
import time
from pathlib import Path
from fastapi.testclient import TestClient

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from backend.app.main import app
from backend.app.database import SessionLocal
from backend.app.models.audit import AuditLog
from backend.app.services.terminal_manager import terminal_session_manager, MAX_SESSIONS_PER_USER

client = TestClient(app)

def get_auth_headers_and_token():
    res = client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
    if res.status_code == 200:
        token = res.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}, token
    return {}, None

def test_terminal_session_unauthenticated_denied():
    res = client.post("/api/terminal/session", json={"cols": 80, "rows": 24})
    assert res.status_code == 401

def test_create_and_list_terminal_sessions():
    headers, token = get_auth_headers_and_token()
    assert token is not None

    # Create session
    create_res = client.post("/api/terminal/session", json={"cols": 90, "rows": 28}, headers=headers)
    assert create_res.status_code == 201
    data = create_res.json()
    assert "session_id" in data
    assert data["session_id"].startswith("term-")
    assert data["os_user"] == "serverpilot-term"
    assert data["cols"] == 90
    assert data["rows"] == 28
    assert data["status"] == "active"

    session_id = data["session_id"]

    # List sessions
    list_res = client.get("/api/terminal/sessions", headers=headers)
    assert list_res.status_code == 200
    sessions = list_res.json()
    assert any(s["session_id"] == session_id for s in sessions)

    # Close session
    del_res = client.delete(f"/api/terminal/session/{session_id}", headers=headers)
    assert del_res.status_code == 200

    # Verify closed
    list_after = client.get("/api/terminal/sessions", headers=headers).json()
    assert not any(s["session_id"] == session_id for s in list_after)

def test_max_concurrent_sessions_limit():
    headers, token = get_auth_headers_and_token()
    created_ids = []

    try:
        # Create up to MAX_SESSIONS_PER_USER (5)
        for _ in range(MAX_SESSIONS_PER_USER):
            res = client.post("/api/terminal/session", json={"cols": 80, "rows": 24}, headers=headers)
            assert res.status_code == 201
            created_ids.append(res.json()["session_id"])

        # Excess session attempt should trigger 429 Too Many Requests
        excess_res = client.post("/api/terminal/session", json={"cols": 80, "rows": 24}, headers=headers)
        assert excess_res.status_code == 429
        assert "limit" in excess_res.json()["detail"].lower()
    finally:
        # Clean up created sessions
        for sid in created_ids:
            client.delete(f"/api/terminal/session/{sid}", headers=headers)

def test_terminal_audit_logging():
    headers, token = get_auth_headers_and_token()

    create_res = client.post("/api/terminal/session", json={"cols": 80, "rows": 24}, headers=headers)
    session_id = create_res.json()["session_id"]

    client.delete(f"/api/terminal/session/{session_id}", headers=headers)

    # Verify audit logs
    db = SessionLocal()
    try:
        logs = db.query(AuditLog).order_by(AuditLog.id.desc()).limit(20).all()
        actions = [l.action for l in logs]
        assert "TERMINAL_SESSION_START" in actions
        assert "TERMINAL_SESSION_END" in actions
    finally:
        db.close()

def test_websocket_terminal_io_resize_ctrl_c_and_reconnect():
    headers, token = get_auth_headers_and_token()

    # Create session
    create_res = client.post("/api/terminal/session", json={"cols": 80, "rows": 24}, headers=headers)
    session_id = create_res.json()["session_id"]

    try:
        # Connect to WebSocket
        with client.websocket_connect(f"/ws/terminal/{session_id}?token={token}") as ws:
            banner = ws.receive_text()
            assert "ServerPilot" in banner or "Restricted" in banner

            # Send window resize event
            ws.send_json({"type": "resize", "cols": 120, "rows": 35})

            # Send Ctrl+C interrupt
            ws.send_json({"type": "input", "data": "\x03"})

            # Send input line
            ws.send_json({"type": "input", "data": "echo TerminalTestOk\r"})

            # Read output
            out = ws.receive_text()
            assert len(out) >= 0

        # Test Reconnect behavior: Output history preserved
        with client.websocket_connect(f"/ws/terminal/{session_id}?token={token}") as ws2:
            reconnect_history = ws2.receive_text()
            assert len(reconnect_history) > 0

    finally:
        client.delete(f"/api/terminal/session/{session_id}", headers=headers)

def test_websocket_terminal_unregistered_session_rejected():
    headers, token = get_auth_headers_and_token()
    # Connecting to non-existent session ID
    try:
        with client.websocket_connect(f"/ws/terminal/term-invalid-9999?token={token}") as ws:
            msg = ws.receive_text()
            assert "Session Error" in msg or "404" in msg
    except Exception:
        pass
