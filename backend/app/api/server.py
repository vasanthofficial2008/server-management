from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.models.user import User
from backend.app.models.audit import AuditLog
from backend.app.models.system import SystemEvent
from backend.app.schemas.system import (
    SystemStatsOut,
    ProcessInfo,
    SystemEventOut,
    AuditLogOut,
    ServerOverviewOut,
    ServerResourcesOut
)
from backend.app.services.system_service import (
    get_system_stats,
    get_top_processes,
    get_server_overview,
    get_server_resources
)
from backend.app.security.auth import get_current_user

router = APIRouter(prefix="/server", tags=["Server"])

@router.get("/overview", response_model=ServerOverviewOut)
def get_overview(current_user: User = Depends(get_current_user)):
    """Retrieve server environment specs (hostname, OS, Python version, boot info)."""
    return get_server_overview()

@router.get("/resources", response_model=ServerResourcesOut)
def get_resources(current_user: User = Depends(get_current_user)):
    """Retrieve real-time resource telemetry (CPU, RAM, Disk, Load average, Network)."""
    return get_server_resources()

@router.get("/stats", response_model=SystemStatsOut)
def get_stats(current_user: User = Depends(get_current_user)):
    return get_system_stats()

@router.get("/processes", response_model=List[ProcessInfo])
def get_processes(current_user: User = Depends(get_current_user)):
    return get_top_processes(limit=20)

@router.get("/events", response_model=List[SystemEventOut])
def get_events(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return db.query(SystemEvent).order_by(SystemEvent.id.desc()).limit(20).all()

@router.get("/audit-logs", response_model=List[AuditLogOut])
def get_audit_logs(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Retrieve audit log records for administrator inspection."""
    logs = db.query(AuditLog).order_by(AuditLog.id.desc()).limit(50).all()
    return logs
