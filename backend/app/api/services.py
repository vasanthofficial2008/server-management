from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.models.user import User
from backend.app.models.service import ServiceModel
from backend.app.schemas.service import ServiceOut, ServiceAction, ServiceCreate
from backend.app.services.systemd_manager import (
    execute_systemd_action,
    get_systemd_status_output,
    get_journalctl_logs
)
from backend.app.security.auth import get_current_user
from backend.app.security.audit import log_audit_event

router = APIRouter(prefix="/services", tags=["Services"])

@router.get("", response_model=List[ServiceOut])
def list_services(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return db.query(ServiceModel).order_by(ServiceModel.id.asc()).all()

@router.post("", response_model=ServiceOut)
def create_service(
    request: Request,
    service_in: ServiceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    existing = db.query(ServiceModel).filter(ServiceModel.name == service_in.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Service with this name is already registered.")

    data = service_in.model_dump()
    if not data.get("systemd_name"):
        data["systemd_name"] = f"{data['name']}.service"

    service = ServiceModel(**data)
    db.add(service)
    db.commit()
    db.refresh(service)

    log_audit_event(
        db,
        action="SERVICE_CREATE",
        username=current_user.username,
        user_id=current_user.id,
        ip_address=request.client.host if request.client else "unknown",
        details=f"Registered system service '{service.display_name}' ({service.systemd_name})"
    )
    return service

@router.post("/{service_id}/action", response_model=ServiceOut)
def perform_service_action(
    request: Request,
    service_id: int,
    action_in: ServiceAction,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    service = execute_systemd_action(
        db=db,
        service_id=service_id,
        action=action_in.action,
        username=current_user.username
    )
    return service

@router.get("/{service_id}/status")
def get_service_status(
    service_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return get_systemd_status_output(db, service_id)

@router.get("/{service_id}/logs")
def get_service_logs(
    service_id: int,
    lines: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return get_journalctl_logs(db, service_id, lines=lines)
