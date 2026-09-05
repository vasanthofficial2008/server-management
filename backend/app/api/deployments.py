from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.models.user import User
from backend.app.models.deployment import Deployment
from backend.app.schemas.deployment import DeploymentCreate, RollbackCreate, DeploymentOut
from backend.app.services.deploy_engine import run_deployment_workflow, run_rollback_workflow
from backend.app.security.auth import get_current_user

router = APIRouter(prefix="/deployments", tags=["Deployments"])

@router.get("", response_model=List[DeploymentOut])
def list_deployments(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return db.query(Deployment).order_by(Deployment.id.desc()).all()

@router.post("", response_model=DeploymentOut, status_code=status.HTTP_201_CREATED)
def create_deployment(
    request: Request,
    deploy_in: DeploymentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    deployment = run_deployment_workflow(db, project_id=deploy_in.project_id, username=current_user.username)
    return deployment

@router.post("/rollback", response_model=DeploymentOut, status_code=status.HTTP_201_CREATED)
def rollback_deployment(
    request: Request,
    rollback_in: RollbackCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Trigger deployment rollback to a known-good release commit."""
    target_dep = db.query(Deployment).filter(Deployment.id == rollback_in.deployment_id).first()
    if not target_dep:
        raise HTTPException(status_code=404, detail=f"Target deployment #{rollback_in.deployment_id} not found.")

    rollback_dep = run_rollback_workflow(
        db=db,
        project_id=target_dep.project_id,
        target_deployment_id=target_dep.id,
        username=current_user.username,
        force_arbitrary_commit=rollback_in.force_arbitrary_commit or False
    )
    return rollback_dep

@router.get("/{deployment_id}", response_model=DeploymentOut)
def get_deployment(
    deployment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    deployment = db.query(Deployment).filter(Deployment.id == deployment_id).first()
    if not deployment:
        raise HTTPException(status_code=404, detail="Deployment record not found.")
    return deployment
