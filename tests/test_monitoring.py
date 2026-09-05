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

def test_monitoring_endpoints_unauthenticated_denied():
    assert client.get("/api/server/overview").status_code == 401
    assert client.get("/api/server/resources").status_code == 401

def test_server_overview_endpoint():
    headers = get_auth_headers()
    response = client.get("/api/server/overview", headers=headers)
    assert response.status_code == 200
    data = response.json()

    assert "hostname" in data
    assert len(data["hostname"]) > 0
    assert "os_name" in data
    assert "os_release" in data
    assert "python_version" in data
    assert len(data["python_version"]) > 0
    assert "cpu_cores_logical" in data
    assert data["cpu_cores_logical"] >= 1
    assert "cpu_cores_physical" in data
    assert "uptime_seconds" in data
    assert "boot_time_iso" in data

def test_server_resources_endpoint():
    headers = get_auth_headers()
    response = client.get("/api/server/resources", headers=headers)
    assert response.status_code == 200
    data = response.json()

    assert "cpu_percent" in data
    assert isinstance(data["cpu_percent"], (int, float))

    # Memory assertions
    assert "memory" in data
    mem = data["memory"]
    assert "total_gb" in mem and mem["total_gb"] > 0
    assert "used_gb" in mem and mem["used_gb"] >= 0
    assert "free_gb" in mem and mem["free_gb"] >= 0
    assert "percent" in mem and 0 <= mem["percent"] <= 100

    # Disk assertions
    assert "disk" in data
    disk = data["disk"]
    assert "total_gb" in disk and disk["total_gb"] > 0
    assert "used_gb" in disk and disk["used_gb"] >= 0
    assert "free_gb" in disk and disk["free_gb"] >= 0
    assert "percent" in disk and 0 <= disk["percent"] <= 100

    # Load average assertions
    assert "load_avg" in data
    assert len(data["load_avg"]) == 3

    # Network assertions
    assert "network" in data
    net = data["network"]
    assert "bytes_sent_mb" in net
    assert "bytes_recv_mb" in net
    assert "packets_sent" in net
    assert "packets_recv" in net
    assert "interfaces" in net
    assert isinstance(net["interfaces"], list)
