from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.models.user import User
from backend.app.models.project import Project
from backend.app.models.deployment import Deployment
from backend.app.schemas.project import ProjectCreate, ProjectUpdate, ProjectOut, get_default_commands, sanitize_and_validate_path
from backend.app.services.project_service import trigger_deployment
from backend.app.security.auth import get_current_user
from backend.app.security.audit import log_audit_event

router = APIRouter(prefix="/projects", tags=["Projects"])

def enrich_project_out(db: Session, project: Project) -> Dict[str, Any]:
    if not project.deployment_directory:
        project.deployment_directory = sanitize_and_validate_path(None, project.name)
        db.commit()

    last_dep = db.query(Deployment).filter(Deployment.project_id == project.id).order_by(Deployment.id.desc()).first()
    data = ProjectOut.model_validate(project).model_dump()
    if last_dep:
        data["last_deployment"] = {
            "id": last_dep.id,
            "status": last_dep.status,
            "commit_hash": last_dep.commit_hash,
            "completed_at": last_dep.completed_at.isoformat() if last_dep.completed_at else None
        }
    return data

@router.get("", response_model=List[ProjectOut])
def list_projects(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    projects = db.query(Project).order_by(Project.id.desc()).all()
    return [enrich_project_out(db, p) for p in projects]

@router.post("", response_model=ProjectOut, status_code=status.HTTP_201_CREATED)
def create_project(
    request: Request,
    project_in: ProjectCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    existing = db.query(Project).filter(Project.name == project_in.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Project with this name already exists.")

    data = project_in.model_dump()

    # Populate default commands if omitted
    defaults = get_default_commands(data["app_type"], data.get("port"))
    for cmd_key in ["start_command", "stop_command", "restart_command", "build_command"]:
        if not data.get(cmd_key):
            data[cmd_key] = defaults[cmd_key]

    if not data.get("deployment_directory"):
        data["deployment_directory"] = sanitize_and_validate_path(None, data["name"])

    if not data.get("service_name"):
        safe_name = "".join(c if c.isalnum() else "-" for c in data["name"].lower())
        data["service_name"] = f"serverpilot-{safe_name}.service"

    project = Project(**data)
    db.add(project)
    db.commit()
    db.refresh(project)

    log_audit_event(
        db,
        action="PROJECT_CREATE",
        username=current_user.username,
        user_id=current_user.id,
        ip_address=request.client.host if request.client else "unknown",
        details=f"Created project '{project.name}' (AppType: {project.app_type}, Port: {project.port})"
    )

    return enrich_project_out(db, project)

@router.get("/{project_id}", response_model=ProjectOut)
def get_project(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")
    return enrich_project_out(db, project)

@router.put("/{project_id}", response_model=ProjectOut)
def update_project(
    request: Request,
    project_id: int,
    project_in: ProjectUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")

    update_data = project_in.model_dump(exclude_unset=True)
    for field, val in update_data.items():
        setattr(project, field, val)

    db.commit()
    db.refresh(project)

    log_audit_event(
        db,
        action="PROJECT_UPDATE",
        username=current_user.username,
        user_id=current_user.id,
        ip_address=request.client.host if request.client else "unknown",
        details=f"Updated project configuration for '{project.name}'"
    )
    return enrich_project_out(db, project)

@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(
    request: Request,
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")

    name = project.name
    db.delete(project)
    db.commit()

    log_audit_event(
        db,
        action="PROJECT_DELETE",
        username=current_user.username,
        user_id=current_user.id,
        ip_address=request.client.host if request.client else "unknown",
        details=f"Deleted project '{name}'"
    )
    return None

@router.post("/{project_id}/deploy")
def deploy_project(
    request: Request,
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")

    deployment = trigger_deployment(db, project_id=project.id, commit_hash="head", commit_msg="Manual project trigger")

    log_audit_event(
        db,
        action="DEPLOYMENT_TRIGGER",
        username=current_user.username,
        user_id=current_user.id,
        ip_address=request.client.host if request.client else "unknown",
        details=f"Triggered deployment for project '{project.name}'"
    )
    return {"message": f"Deployment queued for project '{project.name}'", "deployment_id": deployment.id}

@router.post("/{project_id}/restart")
def restart_project(
    request: Request,
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")

    project.status = "active"
    db.commit()

    log_audit_event(
        db,
        action="PROJECT_RESTART",
        username=current_user.username,
        user_id=current_user.id,
        ip_address=request.client.host if request.client else "unknown",
        details=f"Restarted project '{project.name}' (Command: '{project.restart_command}')"
    )
    return {"message": f"Project '{project.name}' restarted successfully.", "status": "active"}

@router.post("/{project_id}/stop")
def stop_project(
    request: Request,
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")

    project.status = "stopped"
    db.commit()

    log_audit_event(
        db,
        action="PROJECT_STOP",
        username=current_user.username,
        user_id=current_user.id,
        ip_address=request.client.host if request.client else "unknown",
        details=f"Stopped project '{project.name}' (Command: '{project.stop_command}')"
    )
    return {"message": f"Project '{project.name}' stopped successfully.", "status": "stopped"}

@router.get("/{project_id}/logs")
def get_project_logs(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")

    deployments = db.query(Deployment).filter(Deployment.project_id == project.id).order_by(Deployment.id.desc()).limit(5).all()
    logs = [f"--- Deployment #{d.id} ({d.commit_hash}) [{d.status}] ---\n" + (d.log or "") for d in deployments]
    return {
        "project_id": project.id,
        "project_name": project.name,
        "logs": "\n\n".join(logs) if logs else "No execution logs recorded for this project."
    }
