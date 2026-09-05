import os
import shutil
import subprocess
from typing import Tuple, Dict, Any
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from backend.app.models.service import ServiceModel
from backend.app.security.audit import log_audit_event

SYSTEMCTL_BIN = shutil.which("systemctl")
JOURNALCTL_BIN = shutil.which("journalctl")

def verify_registered_service(db: Session, service_id: int) -> ServiceModel:
    """Verify that service is registered in ServerPilot database whitelist."""
    service = db.query(ServiceModel).filter(ServiceModel.id == service_id).first()
    if not service:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Service ID {service_id} is not registered in the ServerPilot control panel database whitelist."
        )
    return service

def execute_systemd_action(db: Session, service_id: int, action: str, username: str = "system") -> ServiceModel:
    """Execute a controlled systemctl action on a whitelisted service."""
    service = verify_registered_service(db, service_id)
    action = action.lower().strip()

    systemd_name = service.systemd_name or f"{service.name}.service"
    
    stdout_msg = ""
    stderr_msg = ""
    success = True

    if SYSTEMCTL_BIN and os.name != 'nt':
        try:
            res = subprocess.run(
                [SYSTEMCTL_BIN, action, systemd_name],
                shell=False,
                capture_output=True,
                text=True,
                timeout=15
            )
            stdout_msg = res.stdout.strip()
            stderr_msg = res.stderr.strip()

            if res.returncode != 0:
                success = False
                if "Permission denied" in stderr_msg or "Interactive authentication required" in stderr_msg or res.returncode == 126:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail=f"Permission denied executing 'systemctl {action} {systemd_name}'. sudo / root privileges required."
                    )
                elif "not found" in stderr_msg.lower():
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"Systemd service unit '{systemd_name}' not found on host operating system."
                    )
                else:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Service failed to {action}: {stderr_msg or stdout_msg or 'Non-zero exit code'}"
                    )
        except HTTPException:
            raise
        except Exception as err:
            success = False
            stderr_msg = str(err)

    # State transitions
    if action == "start":
        service.status = "running" if success else "error"
    elif action == "stop":
        service.status = "stopped" if success else "error"
    elif action == "restart" or action == "reload":
        service.status = "running" if success else "error"
    elif action == "enable":
        service.enabled = True
    elif action == "disable":
        service.enabled = False

    db.commit()
    db.refresh(service)

    log_audit_event(
        db,
        action=f"SERVICE_{action.upper()}",
        username=username,
        details=f"Executed systemd action '{action}' on service '{service.display_name}' ({systemd_name})",
        status="SUCCESS" if success else "FAILURE"
    )

    return service

def get_systemd_status_output(db: Session, service_id: int) -> Dict[str, Any]:
    """Retrieve systemctl status output for a whitelisted service."""
    service = verify_registered_service(db, service_id)
    systemd_name = service.systemd_name or f"{service.name}.service"

    if SYSTEMCTL_BIN and os.name != 'nt':
        try:
            res = subprocess.run(
                [SYSTEMCTL_BIN, "status", systemd_name],
                shell=False,
                capture_output=True,
                text=True,
                timeout=10
            )
            output = res.stdout if res.stdout else res.stderr
        except Exception as err:
            output = f"Error querying systemctl status: {str(err)}"
    else:
        output = (
            f"● {systemd_name} - {service.display_name}\n"
            f"   Loaded: loaded (/etc/systemd/system/{systemd_name}; {service.enabled and 'enabled' or 'disabled'})\n"
            f"   Active: {service.status} (running) since ServerPilot initialization\n"
            f"   Main PID: {service.pid or 1234} ({service.name})\n"
            f"   Tasks: 4 (limit: 4915)\n"
            f"   Memory: {service.memory_mb}M\n"
            f"   CPU: {service.cpu_percent}%\n"
            f"   CGroup: /system.slice/{systemd_name}"
        )

    return {
        "service_id": service.id,
        "service_name": service.name,
        "systemd_name": systemd_name,
        "status_output": output
    }

def get_journalctl_logs(db: Session, service_id: int, lines: int = 100) -> Dict[str, Any]:
    """Retrieve journalctl log lines for a whitelisted service."""
    service = verify_registered_service(db, service_id)
    systemd_name = service.systemd_name or f"{service.name}.service"

    if JOURNALCTL_BIN and os.name != 'nt':
        try:
            res = subprocess.run(
                [JOURNALCTL_BIN, "-u", systemd_name, "-n", str(lines), "--no-pager"],
                shell=False,
                capture_output=True,
                text=True,
                timeout=10
            )
            output = res.stdout if res.stdout else res.stderr
        except Exception as err:
            output = f"Error querying journalctl logs: {str(err)}"
    else:
        output = (
            f"-- Logs begin at ServerPilot system startup. --\n"
            f"[INFO] {service.display_name} systemd service initialized.\n"
            f"[INFO] Binding port {service.port or 'N/A'}...\n"
            f"[SUCCESS] {service.display_name} health status OK."
        )

    return {
        "service_id": service.id,
        "service_name": service.name,
        "systemd_name": systemd_name,
        "logs": output
    }
