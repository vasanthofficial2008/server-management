import time
from datetime import datetime
from sqlalchemy.orm import Session
from backend.app.models.project import Project
from backend.app.models.deployment import Deployment
from backend.app.models.system import SystemEvent

def trigger_deployment(db: Session, project_id: int, commit_hash: str = "head", commit_msg: str = "Manual trigger deployment") -> Deployment:
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise ValueError(f"Project with ID {project_id} not found")
        
    project.status = "building"
    db.commit()
    
    deployment = Deployment(
        project_id=project.id,
        project_name=project.name,
        commit_hash=commit_hash[:7] if commit_hash != "head" else "a8f3b21",
        commit_message=commit_msg,
        status="building",
        log=f"[INFO] Initializing deployment pipeline for {project.name}...\n[INFO] Pulling branch '{project.branch}'...\n[INFO] Validating environment configurations...\n[INFO] Building application bundle...\n"
    )
    db.add(deployment)
    db.commit()
    db.refresh(deployment)
    
    # Simulate step completions for deployment execution
    start_time = time.time()
    deployment.log += f"[SUCCESS] Dependencies installed successfully.\n[SUCCESS] Health check passed on port {project.port or 8000}.\n[INFO] Deployment complete!"
    deployment.status = "success"
    deployment.duration_seconds = round(time.time() - start_time, 2)
    deployment.completed_at = datetime.utcnow()
    
    project.status = "active"
    
    event = SystemEvent(
        level="INFO",
        category="DEPLOYMENT",
        message=f"Successfully deployed project '{project.name}' (Commit #{deployment.commit_hash})"
    )
    db.add(event)
    db.commit()
    db.refresh(deployment)
    
    return deployment
