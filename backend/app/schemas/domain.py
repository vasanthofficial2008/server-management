from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, field_validator

class DomainBase(BaseModel):
    domain_name: str
    subdomain: Optional[str] = None
    project_id: Optional[int] = None
    local_host: str = "127.0.0.1"
    local_port: int = 8000
    https_enabled: bool = True

    @field_validator("domain_name")
    def validate_domain_name(cls, v):
        v = v.lower().strip()
        if not v:
            raise ValueError("Domain name cannot be empty.")
        if "://" in v or "/" in v:
            raise ValueError("Domain name must be a valid hostname without protocol or path (e.g. 'example.com' or 'api.example.com').")
        return v

    @field_validator("local_port")
    def validate_port(cls, v):
        if v < 1 or v > 65535:
            raise ValueError("Local port must be between 1 and 65535.")
        return v

class DomainCreate(DomainBase):
    pass

class DomainUpdate(BaseModel):
    domain_name: Optional[str] = None
    subdomain: Optional[str] = None
    project_id: Optional[int] = None
    local_host: Optional[str] = None
    local_port: Optional[int] = None
    https_enabled: Optional[bool] = None

class DomainOut(DomainBase):
    id: int
    project_name: Optional[str] = None
    ssl_enabled: bool = True
    tunnel_status: str
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class DomainValidateRequest(BaseModel):
    domain_name: str
    project_id: Optional[int] = None
    local_host: str = "127.0.0.1"
    local_port: int = 8000

class TunnelStatusOut(BaseModel):
    tunnel_id: str
    status: str
    active_routes_count: int
    config_file_path: str
    last_reloaded: datetime
