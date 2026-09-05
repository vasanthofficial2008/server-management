from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, field_validator

ALLOWED_SERVICE_ACTIONS = ["start", "stop", "restart", "enable", "disable", "reload"]

class ServiceBase(BaseModel):
    name: str
    display_name: str
    systemd_name: Optional[str] = None
    project_id: Optional[int] = None
    project_name: Optional[str] = None
    type: str = "daemon"
    port: Optional[int] = None
    enabled: bool = True

class ServiceCreate(ServiceBase):
    pass

class ServiceAction(BaseModel):
    action: str  # start, stop, restart, enable, disable, reload

    @field_validator("action")
    def validate_action(cls, v):
        act = v.lower().strip()
        if act not in ALLOWED_SERVICE_ACTIONS:
            raise ValueError(f"Invalid service action '{v}'. Must be one of {ALLOWED_SERVICE_ACTIONS}")
        return act

class ServiceOut(ServiceBase):
    id: int
    status: str
    pid: Optional[int] = None
    memory_mb: float
    cpu_percent: float
    uptime_seconds: int
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
