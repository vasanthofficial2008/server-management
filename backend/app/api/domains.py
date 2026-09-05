from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.models.user import User
from backend.app.models.domain import Domain
from backend.app.models.project import Project
from backend.app.schemas.domain import (
    DomainCreate,
    DomainUpdate,
    DomainOut,
    DomainValidateRequest,
    TunnelStatusOut
)
from backend.app.services.tunnel_manager import (
    validate_domain_mapping,
    generate_controlled_tunnel_config,
    get_tunnel_status,
    reload_tunnel_configuration,
    restart_tunnel_service
)
from backend.app.security.auth import get_current_user
from backend.app.security.audit import log_audit_event

router = APIRouter(prefix="/domains", tags=["Domains"])

@router.get("", response_model=List[DomainOut])
def list_domains(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all registered domain routing assignments."""
    return db.query(Domain).order_by(Domain.id.desc()).all()

@router.post("", response_model=DomainOut, status_code=status.HTTP_201_CREATED)
def create_domain(
    request: Request,
    domain_in: DomainCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new validated domain mapping behind the tunnel."""
    validate_domain_mapping(
        db=db,
        domain_name=domain_in.domain_name,
        project_id=domain_in.project_id,
        local_port=domain_in.local_port
    )

    project_name = None
    if domain_in.project_id:
        proj = db.query(Project).filter(Project.id == domain_in.project_id).first()
        if proj:
            project_name = proj.name

    domain = Domain(
        domain_name=domain_in.domain_name.lower().strip(),
        subdomain=domain_in.subdomain.strip() if domain_in.subdomain else None,
        project_id=domain_in.project_id,
        project_name=project_name,
        local_host=domain_in.local_host or "127.0.0.1",
        local_port=domain_in.local_port,
        https_enabled=domain_in.https_enabled,
        ssl_enabled=domain_in.https_enabled,
        tunnel_status="connected",
        status="active"
    )
    db.add(domain)
    db.commit()
    db.refresh(domain)

    # Regenerate controlled Cloudflare Tunnel config
    generate_controlled_tunnel_config(db)

    log_audit_event(
        db,
        action="DOMAIN_CREATE",
        username=current_user.username,
        user_id=current_user.id,
        ip_address=request.client.host if request.client else "unknown",
        details=f"Added domain route '{domain.domain_name}' → {domain.local_host}:{domain.local_port} (Project: {project_name or 'System'})"
    )

    return domain

@router.post("/validate")
def validate_domain_config(
    payload: DomainValidateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Validate domain mapping configuration without persisting."""
    validate_domain_mapping(
        db=db,
        domain_name=payload.domain_name,
        project_id=payload.project_id,
        local_port=payload.local_port
    )
    return {
        "valid": True,
        "mapping": f"{payload.domain_name} → {payload.local_host}:{payload.local_port}",
        "message": "Domain mapping configuration is valid and free of duplicate assignments."
    }

@router.get("/tunnel/status", response_model=TunnelStatusOut)
def fetch_tunnel_status(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Fetch Cloudflare Tunnel connection status and active routes count."""
    return get_tunnel_status(db)

@router.post("/tunnel/reload", response_model=TunnelStatusOut)
def reload_tunnel(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Safely regenerate controlled configuration and reload Cloudflare Tunnel."""
    return reload_tunnel_configuration(db, username=current_user.username)

@router.post("/tunnel/restart", response_model=TunnelStatusOut)
def restart_tunnel(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Safely restart Cloudflare Tunnel service daemon."""
    return restart_tunnel_service(db, username=current_user.username)

@router.get("/{domain_id}", response_model=DomainOut)
def get_domain(
    domain_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    domain = db.query(Domain).filter(Domain.id == domain_id).first()
    if not domain:
        raise HTTPException(status_code=404, detail="Domain mapping not found.")
    return domain

@router.put("/{domain_id}", response_model=DomainOut)
def update_domain(
    request: Request,
    domain_id: int,
    domain_in: DomainUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    domain = db.query(Domain).filter(Domain.id == domain_id).first()
    if not domain:
        raise HTTPException(status_code=404, detail="Domain mapping not found.")

    new_domain = domain_in.domain_name.lower().strip() if domain_in.domain_name else domain.domain_name
    new_port = domain_in.local_port if domain_in.local_port is not None else domain.local_port
    new_project_id = domain_in.project_id if domain_in.project_id is not None else domain.project_id

    validate_domain_mapping(
        db=db,
        domain_name=new_domain,
        project_id=new_project_id,
        local_port=new_port,
        exclude_id=domain.id
    )

    domain.domain_name = new_domain
    if domain_in.subdomain is not None:
        domain.subdomain = domain_in.subdomain.strip() if domain_in.subdomain else None
    if domain_in.local_host is not None:
        domain.local_host = domain_in.local_host
    domain.local_port = new_port
    if domain_in.https_enabled is not None:
        domain.https_enabled = domain_in.https_enabled
        domain.ssl_enabled = domain_in.https_enabled
    if domain_in.project_id is not None:
        domain.project_id = domain_in.project_id
        if domain_in.project_id:
            proj = db.query(Project).filter(Project.id == domain_in.project_id).first()
            domain.project_name = proj.name if proj else None

    db.commit()
    db.refresh(domain)

    generate_controlled_tunnel_config(db)

    log_audit_event(
        db,
        action="DOMAIN_UPDATE",
        username=current_user.username,
        user_id=current_user.id,
        ip_address=request.client.host if request.client else "unknown",
        details=f"Updated domain route '{domain.domain_name}' → {domain.local_host}:{domain.local_port}"
    )

    return domain

@router.delete("/{domain_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_domain(
    request: Request,
    domain_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    domain = db.query(Domain).filter(Domain.id == domain_id).first()
    if not domain:
        raise HTTPException(status_code=404, detail="Domain mapping not found.")
        
    name = domain.domain_name
    db.delete(domain)
    db.commit()

    generate_controlled_tunnel_config(db)

    log_audit_event(
        db,
        action="DOMAIN_DELETE",
        username=current_user.username,
        user_id=current_user.id,
        ip_address=request.client.host if request.client else "unknown",
        details=f"Removed domain route '{name}'"
    )
    return None
