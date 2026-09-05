from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict

class DeploymentCreate(BaseModel):
    project_id: int
    branch: Optional[str] = None
    commit_message: Optional[str] = "Manual trigger deployment"

class RollbackCreate(BaseModel):
    deployment_id: int
    force_arbitrary_commit: Optional[bool] = False

class DeploymentOut(BaseModel):
    id: int
    project_id: int
    project_name: str
    previous_commit: str
    new_commit: str
    branch: str
    is_rollback: bool = False
    target_rollback_commit: Optional[str] = None
    build_state: str = "passed"
    service_state: str = "active"
    started_at: datetime
    completed_at: Optional[datetime] = None
    status: str
    log: str
    error_message: Optional[str] = None
    duration_seconds: int

    model_config = ConfigDict(from_attributes=True)
