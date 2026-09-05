import os
import sys
import shutil
import subprocess
from pathlib import Path
from typing import List, Dict, Any
import psutil
from sqlalchemy.orm import Session

from backend.app.config import settings
from backend.app.models.service import ServiceModel
from backend.app.models.project import Project
from backend.app.schemas.project import get_default_commands, sanitize_and_validate_path

SYSTEMCTL_BIN = shutil.which("systemctl")
GIT_BIN = shutil.which("git")

COMMON_SERVICE_NAMES = [
    "serverpilot.service",
    "nginx.service",
    "apache2.service",
    "mysql.service",
    "mariadb.service",
    "postgresql.service",
    "redis-server.service",
    "redis.service",
    "docker.service",
    "ufw.service",
    "ssh.service",
    "sshd.service",
    "cron.service",
    "cloudflared.service"
]

def discover_system_services(db: Session) -> List[ServiceModel]:
    """Scan and synchronize REAL systemd services running on the host OS."""
    detected_services = []

    if SYSTEMCTL_BIN and os.name != 'nt':
        try:
            # Query systemctl list-units
            res = subprocess.run(
                [SYSTEMCTL_BIN, "list-units", "--type=service", "--all", "--no-legend", "--no-pager"],
                capture_output=True, text=True, timeout=10
            )
            for line in res.stdout.splitlines():
                line = line.strip()
                if not line:
                    continue
                parts = line.split(None, 4)
                if len(parts) >= 4:
                    unit_name = parts[0]
                    load_state = parts[1]
                    active_state = parts[2]
                    sub_state = parts[3]
                    description = parts[4] if len(parts) > 4 else unit_name

                    # Filter relevant systemd services
                    if unit_name in COMMON_SERVICE_NAMES or unit_name.startswith("serverpilot") or active_state == "active":
                        srv_type = "web" if any(w in unit_name for w in ["nginx", "apache", "web", "serverpilot"]) else \
                                  "database" if any(w in unit_name for w in ["sql", "mongo", "db"]) else \
                                  "cache" if "redis" in unit_name else "daemon"

                        status_str = "running" if active_state == "active" and sub_state == "running" else \
                                     "stopped" if active_state == "inactive" or sub_state == "dead" else active_state

                        # Get real PID and memory/CPU metrics if process running
                        pid, memory_mb, cpu_pct = get_service_process_metrics(unit_name)

                        service_data = {
                            "name": unit_name.replace(".service", ""),
                            "display_name": description,
                            "systemd_name": unit_name,
                            "type": srv_type,
                            "status": status_str,
                            "enabled": (load_state == "loaded"),
                            "pid": pid,
                            "memory_mb": round(memory_mb, 1),
                            "cpu_percent": round(cpu_pct, 1)
                        }
                        detected_services.append(service_data)
        except Exception as err:
            print(f"[DISCOVERY] Error listing systemd services: {err}")
    
    # Fallback to inspecting current serverpilot process & python environment if no systemctl
    if not detected_services:
        proc = psutil.Process(os.getpid())
        mem_mb = proc.memory_info().rss / (1024 * 1024)
        cpu_pct = proc.cpu_percent(interval=0.1)
        detected_services.append({
            "name": "serverpilot-api",
            "display_name": "ServerPilot Control Panel API",
            "systemd_name": "serverpilot.service",
            "type": "web",
            "status": "running",
            "enabled": True,
            "port": 8000,
            "pid": proc.pid,
            "memory_mb": round(mem_mb, 1),
            "cpu_percent": round(cpu_pct, 1)
        })

    # Save to SQLite Database
    synced_services = []
    for s_data in detected_services:
        existing = db.query(ServiceModel).filter(ServiceModel.systemd_name == s_data["systemd_name"]).first()
        if existing:
            existing.status = s_data["status"]
            existing.enabled = s_data["enabled"]
            existing.pid = s_data["pid"]
            existing.memory_mb = s_data["memory_mb"]
            existing.cpu_percent = s_data["cpu_percent"]
            synced_services.append(existing)
        else:
            new_srv = ServiceModel(**s_data)
            db.add(new_srv)
            synced_services.append(new_srv)

    # Clean out old mock entries (like fake Acme services)
    db.query(ServiceModel).filter(ServiceModel.systemd_name.like("serverpilot-acme-%")).delete(synchronize_session=False)

    db.commit()
    return synced_services

def get_service_process_metrics(service_name: str) -> tuple[int | None, float, float]:
    """Retrieve real PID, RAM Memory (MB), and CPU % for a systemd service."""
    if not SYSTEMCTL_BIN or os.name == 'nt':
        return None, 0.0, 0.0

    try:
        res = subprocess.run(
            [SYSTEMCTL_BIN, "show", service_name, "--property=MainPID,MemoryCurrent,CPUUsageNSec"],
            capture_output=True, text=True, timeout=5
        )
        pid = None
        mem_bytes = 0
        
        for line in res.stdout.splitlines():
            if line.startswith("MainPID="):
                val = line.split("=")[1].strip()
                if val and val.isdigit() and int(val) > 0:
                    pid = int(val)
            elif line.startswith("MemoryCurrent="):
                val = line.split("=")[1].strip()
                if val and val.isdigit() and val != "[not set]":
                    mem_bytes = int(val)

        if pid and psutil.pid_exists(pid):
            try:
                proc = psutil.Process(pid)
                mem_mb = proc.memory_info().rss / (1024 * 1024)
                cpu_pct = proc.cpu_percent(interval=None)
                return pid, mem_mb, cpu_pct
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass

        mem_mb = mem_bytes / (1024 * 1024) if mem_bytes > 0 else 0.0
        return pid, mem_mb, 0.0
    except Exception:
        return None, 0.0, 0.0

def discover_real_projects(db: Session) -> List[Project]:
    """Scan local host directories and listening network ports to discover REAL application projects."""
    search_dirs = [
        settings.DEPLOYMENTS_DIR,
        Path("/var/www"),
        Path("/opt"),
        Path.home(),
        Path.cwd()
    ]

    discovered_projects = []
    seen_paths = set()

    for base_dir in search_dirs:
        if not base_dir.exists() or not base_dir.is_dir():
            continue

        try:
            # Check base_dir itself and immediate child directories
            candidates = [base_dir]
            try:
                candidates.extend([p for p in base_dir.iterdir() if p.is_dir()])
            except PermissionError:
                pass

            for cand in candidates:
                cand_path = cand.resolve()
                if str(cand_path) in seen_paths:
                    continue
                seen_paths.add(str(cand_path))

                # Skip system folders
                if cand_path in [Path("/opt"), Path("/var"), Path("/var/www"), Path("/"), Path.home()]:
                    continue

                if is_valid_project_directory(cand_path):
                    project_record = analyze_and_register_project(db, cand_path)
                    if project_record:
                        discovered_projects.append(project_record)
        except Exception as err:
            print(f"[DISCOVERY] Error scanning directory {base_dir}: {err}")

    # Remove mock sample projects (e.g., Acme API Service, Dashboard Storefront)
    db.query(Project).filter(Project.name.in_(["Acme API Service", "Dashboard Storefront"])).delete(synchronize_session=False)

    db.commit()
    return db.query(Project).all()

def is_valid_project_directory(dir_path: Path) -> bool:
    """Check if directory contains real application project files."""
    if not dir_path.exists() or not dir_path.is_dir():
        return False

    project_markers = [
        ".git",
        "requirements.txt",
        "package.json",
        "main.py",
        "app.py",
        "wsgi.py",
        "index.html",
        "Dockerfile",
        "go.mod",
        "Cargo.toml"
    ]
    return any((dir_path / marker).exists() for marker in project_markers)

def analyze_and_register_project(db: Session, dir_path: Path) -> Project | None:
    """Analyze a project folder and insert/update real project in database."""
    proj_name = dir_path.name.replace("-", " ").replace("_", " ").title()
    
    # 1. Determine App Type
    app_type = "Custom Application"
    if (dir_path / "main.py").exists() or (dir_path / "requirements.txt").exists():
        app_type = "Python FastAPI"
    elif (dir_path / "app.py").exists():
        app_type = "Python Flask"
    elif (dir_path / "index.html").exists() and not (dir_path / "package.json").exists():
        app_type = "Static HTML/CSS/JavaScript"

    # 2. Get Real Git Branch & Repo URL
    git_branch = "main"
    git_repo_url = f"https://github.com/local/{dir_path.name}.git"

    if (dir_path / ".git").exists() and GIT_BIN:
        try:
            res_b = subprocess.run(
                [GIT_BIN, "-C", str(dir_path), "rev-parse", "--abbrev-ref", "HEAD"],
                capture_output=True, text=True, timeout=5
            )
            if res_b.returncode == 0 and res_b.stdout.strip():
                git_branch = res_b.stdout.strip()

            res_u = subprocess.run(
                [GIT_BIN, "-C", str(dir_path), "config", "--get", "remote.origin.url"],
                capture_output=True, text=True, timeout=5
            )
            if res_u.returncode == 0 and res_u.stdout.strip():
                git_repo_url = res_u.stdout.strip()
        except Exception:
            pass

    # 3. Detect Binding Port from Listening Connections
    detected_port = detect_listening_port_for_directory(dir_path) or 8000

    # Check if project already registered
    existing = db.query(Project).filter(
        (Project.deployment_directory == str(dir_path)) | (Project.name == proj_name)
    ).first()

    default_cmds = get_default_commands(app_type, detected_port)

    if existing:
        existing.branch = git_branch
        existing.repo_url = git_repo_url
        existing.app_type = app_type
        existing.status = "active"
        db.commit()
        db.refresh(existing)
        return existing
    else:
        new_project = Project(
            name=proj_name,
            description=f"Auto-detected real application project at {dir_path}",
            repo_url=git_repo_url,
            branch=git_branch,
            app_type=app_type,
            status="active",
            port=detected_port,
            service_name=f"serverpilot-{dir_path.name}.service",
            deployment_directory=str(dir_path),
            environment_vars={"ENV": "production", "PORT": str(detected_port)},
            **default_cmds
        )
        db.add(new_project)
        db.commit()
        db.refresh(new_project)
        return new_project

def detect_listening_port_for_directory(dir_path: Path) -> int | None:
    """Find listening network port associated with running processes in directory."""
    try:
        for conn in psutil.net_connections(kind='inet'):
            if conn.status == psutil.CONN_LISTEN and conn.pid:
                try:
                    proc = psutil.Process(conn.pid)
                    cwd = proc.cwd()
                    if cwd and Path(cwd).resolve() == dir_path.resolve():
                        return conn.laddr.port
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
    except Exception:
        pass
    return None
