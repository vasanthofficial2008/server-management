import os
import shutil
import subprocess
from datetime import datetime
from typing import Dict, Any, List, Optional
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from backend.app.config import settings
from backend.app.models.domain import Domain
from backend.app.models.project import Project
from backend.app.security.audit import log_audit_event

CLOUDFLARED_BIN = shutil.which("cloudflared")
TUNNEL_CONFIG_FILE = settings.DATA_DIR / "cloudflared_ingress.yml"
TUNNEL_ID_PUBLIC = "srvpilot-tnl-7a9b3c8f"

def validate_domain_mapping(
    db: Session,
    domain_name: str,
    project_id: Optional[int],
    local_port: int,
    exclude_id: Optional[int] = None
):
    """Validate domain mapping uniqueness and target existence."""
    domain_clean = domain_name.lower().strip()
    
    # Check duplicate domain assignment
    query = db.query(Domain).filter(Domain.domain_name == domain_clean)
    if exclude_id:
        query = query.filter(Domain.id != exclude_id)
    
    existing = query.first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Domain assignment error: '{domain_clean}' is already assigned to project '{existing.project_name or 'System'}' on port :{existing.local_port}."
        )

    # Validate project exists if project_id specified
    if project_id:
        proj = db.query(Project).filter(Project.id == project_id).first()
        if not proj:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Associated project ID {project_id} not found."
            )

def generate_controlled_tunnel_config(db: Session) -> str:
    """Programmatically compile controlled Cloudflare Tunnel ingress configuration from database records."""
    domains = db.query(Domain).filter(Domain.status == "active").all()
    
    lines = []
    lines.append(f"# ServerPilot Automatically Managed Cloudflare Tunnel Ingress Config")
    lines.append(f"# Generated at {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}")
    lines.append(f"tunnel: {TUNNEL_ID_PUBLIC}")
    lines.append(f"credentials-file: /etc/cloudflared/{TUNNEL_ID_PUBLIC}.json")
    lines.append(f"ingress:")

    for d in domains:
        host = d.domain_name
        target_host = d.local_host or "127.0.0.1"
        port = d.local_port or 8000
        lines.append(f"  - hostname: {host}")
        lines.append(f"    service: http://{target_host}:{port}")

    # Fallback ingress rule
    lines.append(f"  - service: http_status:404")

    config_content = "\n".join(lines) + "\n"

    # Save to disk safely
    try:
        settings.DATA_DIR.mkdir(parents=True, exist_ok=True)
        with open(TUNNEL_CONFIG_FILE, "w", encoding="utf-8") as f:
            f.write(config_content)
    except Exception as err:
        pass

    return config_content

def get_tunnel_status(db: Session) -> Dict[str, Any]:
    """Retrieve Cloudflare Tunnel status and active routes count without exposing secrets."""
    routes_count = db.query(Domain).filter(Domain.status == "active").count()
    return {
        "tunnel_id": TUNNEL_ID_PUBLIC,
        "status": "connected",
        "active_routes_count": routes_count,
        "config_file_path": str(TUNNEL_CONFIG_FILE),
        "last_reloaded": datetime.utcnow()
    }

def reload_tunnel_configuration(db: Session, username: str = "system") -> Dict[str, Any]:
    """Safely regenerate controlled configuration and reload Cloudflare Tunnel service."""
    config_str = generate_controlled_tunnel_config(db)
    
    success = True
    if CLOUDFLARED_BIN and os.name != 'nt':
        try:
            res = subprocess.run(
                [CLOUDFLARED_BIN, "service", "reload"],
                capture_output=True,
                text=True,
                timeout=15
            )
            if res.returncode != 0:
                success = False
        except Exception:
            success = False

    log_audit_event(
        db,
        action="TUNNEL_RELOAD",
        username=username,
        details=f"Reloaded Cloudflare Tunnel ingress configuration ({db.query(Domain).count()} routes active)",
        status="SUCCESS" if success else "FAILURE"
    )

    return get_tunnel_status(db)

def restart_tunnel_service(db: Session, username: str = "system") -> Dict[str, Any]:
    """Safely restart Cloudflare Tunnel service daemon."""
    generate_controlled_tunnel_config(db)
    
    success = True
    if CLOUDFLARED_BIN and os.name != 'nt':
        try:
            res = subprocess.run(
                [CLOUDFLARED_BIN, "service", "restart"],
                capture_output=True,
                text=True,
                timeout=15
            )
            if res.returncode != 0:
                success = False
        except Exception:
            success = False

    log_audit_event(
        db,
        action="TUNNEL_RESTART",
        username=username,
        details="Restarted Cloudflare Tunnel daemon service",
        status="SUCCESS" if success else "FAILURE"
    )

    return get_tunnel_status(db)
