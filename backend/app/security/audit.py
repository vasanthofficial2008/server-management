from typing import Optional
from sqlalchemy.orm import Session
from backend.app.models.audit import AuditLog
from backend.app.services.log_service import append_log

def log_audit_event(
    db: Session,
    action: str,
    username: Optional[str] = None,
    user_id: Optional[int] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    details: Optional[str] = None,
    status: str = "SUCCESS"
) -> AuditLog:
    """Create an audit log record in database and append to server file log."""
    audit_entry = AuditLog(
        user_id=user_id,
        username=username or "anonymous",
        action=action,
        ip_address=ip_address or "unknown",
        user_agent=user_agent or "unknown",
        details=details or "",
        status=status
    )
    db.add(audit_entry)
    db.commit()
    db.refresh(audit_entry)
    
    log_level = "INFO" if status == "SUCCESS" else "WARNING"
    log_msg = f"[AUDIT:{action}] User='{username or 'anon'}' IP='{ip_address}' Status='{status}' - {details or ''}"
    append_log(log_level, "AUDIT", log_msg)
    
    return audit_entry
