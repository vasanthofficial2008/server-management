import os
import re
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session

from backend.app.config import settings
from backend.app.models.audit import AuditLog
from backend.app.models.deployment import Deployment
from backend.app.models.project import Project
from backend.app.models.service import ServiceModel
from backend.app.services.executor import validate_safe_path

LOG_FILE = settings.LOGS_DIR / "serverpilot.log"

def ensure_log_file():
    if not LOG_FILE.exists():
        settings.LOGS_DIR.mkdir(parents=True, exist_ok=True)
        with open(LOG_FILE, "w", encoding="utf-8") as f:
            f.write(f"[{datetime.utcnow().isoformat()}] [INFO] ServerPilot logging engine initialized.\n")

def append_log(level: str, category: str, message: str):
    ensure_log_file()
    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] [{level.upper()}] [{category.upper()}] {message}\n"
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(log_entry)

def get_recent_logs(lines: int = 100) -> List[str]:
    ensure_log_file()
    try:
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            all_lines = f.readlines()
            return [line.strip() for line in all_lines[-lines:]]
    except Exception:
        return ["Log file unreadable or empty."]

def parse_log_level(text: str) -> str:
    upper = text.upper()
    if "ERROR" in upper or "FAIL" in upper or "❌" in upper or "CRITICAL" in upper:
        return "ERROR"
    elif "WARN" in upper or "⚠️" in upper:
        return "WARNING"
    elif "SUCCESS" in upper or "OK" in upper or "🎉" in upper or "✅" in upper:
        return "SUCCESS"
    return "INFO"

def get_centralized_logs(
    db: Session,
    category: Optional[str] = None,
    project_id: Optional[int] = None,
    service_id: Optional[int] = None,
    level: Optional[str] = None,
    search: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    page: int = 1,
    page_size: int = 50
) -> Tuple[List[Dict[str, Any]], int]:
    """Retrieve centralized logs across 4 categories with search, date filter, level filter, and pagination."""
    all_entries: List[Dict[str, Any]] = []

    target_cat = category.lower().strip() if category else None
    target_lvl = level.upper().strip() if level else None
    search_q = search.lower().strip() if search else None

    # Parse date filters if provided
    dt_start = None
    dt_end = None
    if start_date:
        try:
            dt_start = datetime.fromisoformat(start_date.replace("Z", ""))
        except Exception:
            pass
    if end_date:
        try:
            dt_end = datetime.fromisoformat(end_date.replace("Z", ""))
        except Exception:
            pass

    # 1. Audit Logs
    if not target_cat or target_cat == "audit":
        audit_query = db.query(AuditLog)
        if dt_start:
            audit_query = audit_query.filter(AuditLog.timestamp >= dt_start)
        if dt_end:
            audit_query = audit_query.filter(AuditLog.timestamp <= dt_end)
        
        audits = audit_query.order_by(AuditLog.timestamp.desc()).limit(200).all()
        for a in audits:
            lvl = "ERROR" if a.status == "FAILURE" else "INFO"
            msg = f"[{a.action}] {a.details}"
            all_entries.append({
                "id": f"audit-{a.id}",
                "timestamp": a.timestamp.isoformat(),
                "category": "audit",
                "level": lvl,
                "source": a.username or "system",
                "message": msg,
                "raw_dt": a.timestamp
            })

    # 2. Deployment Logs
    if not target_cat or target_cat == "deployment":
        dep_query = db.query(Deployment)
        if project_id:
            dep_query = dep_query.filter(Deployment.project_id == project_id)
        if dt_start:
            dep_query = dep_query.filter(Deployment.started_at >= dt_start)
        if dt_end:
            dep_query = dep_query.filter(Deployment.started_at <= dt_end)

        deps = dep_query.order_by(Deployment.id.desc()).limit(50).all()
        for d in deps:
            log_text = d.log or ""
            lines = log_text.splitlines()
            for idx, line in enumerate(lines):
                if not line.strip():
                    continue
                lvl = parse_log_level(line)
                all_entries.append({
                    "id": f"deploy-{d.id}-{idx}",
                    "timestamp": (d.started_at or datetime.utcnow()).isoformat(),
                    "category": "deployment",
                    "level": lvl,
                    "source": f"Deploy #{d.id} ({d.project_name})",
                    "message": line,
                    "raw_dt": d.started_at or datetime.utcnow()
                })

    # 3. Systemd Service Logs
    if not target_cat or target_cat == "systemd":
        from backend.app.services.systemd_manager import get_journalctl_logs
        srv_query = db.query(ServiceModel)
        if service_id:
            srv_query = srv_query.filter(ServiceModel.id == service_id)

        services = srv_query.all()
        for srv in services:
            res = get_journalctl_logs(db, srv.id, lines=50)
            logs_str = res.get("logs", "")
            for idx, line in enumerate(logs_str.splitlines()):
                if not line.strip():
                    continue
                lvl = parse_log_level(line)
                all_entries.append({
                    "id": f"systemd-{srv.id}-{idx}",
                    "timestamp": srv.updated_at.isoformat(),
                    "category": "systemd",
                    "level": lvl,
                    "source": srv.display_name,
                    "message": line,
                    "raw_dt": srv.updated_at
                })

    # 4. Application Logs
    if not target_cat or target_cat == "application":
        proj_query = db.query(Project)
        if project_id:
            proj_query = proj_query.filter(Project.id == project_id)

        projects = proj_query.all()
        for proj in projects:
            try:
                deploy_dir = validate_safe_path(proj.deployment_directory or proj.name)
                log_candidates = [deploy_dir / "app.log", deploy_dir / "server.log", deploy_dir / "console.log"]
                for candidate in log_candidates:
                    if candidate.exists() and candidate.is_file():
                        with open(candidate, "r", encoding="utf-8", errors="ignore") as f:
                            lines = f.readlines()[-50:]
                            for idx, line in enumerate(lines):
                                if not line.strip():
                                    continue
                                lvl = parse_log_level(line)
                                all_entries.append({
                                    "id": f"app-{proj.id}-{idx}",
                                    "timestamp": proj.updated_at.isoformat(),
                                    "category": "application",
                                    "level": lvl,
                                    "source": proj.name,
                                    "message": line.strip(),
                                    "raw_dt": proj.updated_at
                                })
            except Exception:
                pass

    # Filter by level
    if target_lvl:
        all_entries = [e for e in all_entries if e["level"] == target_lvl]

    # Filter by search string query
    if search_q:
        all_entries = [
            e for e in all_entries
            if search_q in e["message"].lower() or search_q in e["source"].lower()
        ]

    # Sort entries by timestamp descending
    all_entries.sort(key=lambda x: x["raw_dt"], reverse=True)

    # Remove temporary raw_dt from final dicts
    for e in all_entries:
        e.pop("raw_dt", None)

    total_count = len(all_entries)
    page_size = max(1, min(page_size, 500))
    start_idx = (page - 1) * page_size
    end_idx = start_idx + page_size
    paged_entries = all_entries[start_idx:end_idx]

    return paged_entries, total_count
