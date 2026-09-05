from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, ConfigDict, field_validator
from backend.app.config import settings

ALLOWED_APP_TYPES = [
    "Static HTML/CSS/JavaScript",
    "Python FastAPI",
    "Python Flask",
    "Python Custom"
]

def sanitize_and_validate_path(path_str: Optional[str], project_name: str = "app") -> str:
    """Sanitize and validate deployment directory to prevent path traversal outside sandbox."""
    if not path_str or not str(path_str).strip():
        safe_folder = "".join(c if c.isalnum() else "_" for c in project_name.lower())
        return str((settings.DEPLOYMENTS_DIR / safe_folder).resolve())

    path_str = str(path_str).strip()

    # Disallow explicit traversal sequences
    if ".." in path_str:
        raise ValueError("Directory path cannot contain relative traversal '..' characters.")

    target_path = Path(path_str)
    if not target_path.is_absolute():
        target_path = (settings.DEPLOYMENTS_DIR / path_str).resolve()
    else:
        target_path = target_path.resolve()

    # Ensure path resides within allowed workspace or deployments dir
    allowed_base = settings.DEPLOYMENTS_DIR.resolve()
    try:
        target_path.relative_to(allowed_base)
    except ValueError:
        safe_basename = target_path.name or "app"
        target_path = (allowed_base / safe_basename).resolve()

    return str(target_path)

def get_default_commands(app_type: str, port: Optional[int] = 8000) -> Dict[str, str]:
    port = port or 8000
    if app_type == "Static HTML/CSS/JavaScript":
        return {
            "build_command": "echo 'Static assets ready'",
            "start_command": f"python3 -m http.server {port}",
            "stop_command": "pkill -f http.server",
            "restart_command": f"pkill -f http.server && python3 -m http.server {port}"
        }
    elif app_type == "Python FastAPI":
        return {
            "build_command": "pip install -r requirements.txt",
            "start_command": f"uvicorn main:app --host 0.0.0.0 --port {port}",
            "stop_command": f"pkill -f 'uvicorn.*{port}'",
            "restart_command": f"pkill -f 'uvicorn.*{port}' && uvicorn main:app --host 0.0.0.0 --port {port}"
        }
    elif app_type == "Python Flask":
        return {
            "build_command": "pip install -r requirements.txt",
            "start_command": f"flask run --host=0.0.0.0 --port={port}",
            "stop_command": f"pkill -f 'flask.*{port}'",
            "restart_command": f"pkill -f 'flask.*{port}' && flask run --host=0.0.0.0 --port={port}"
        }
    else:
        return {
            "build_command": "pip install -r requirements.txt",
            "start_command": f"python3 main.py --port {port}",
            "stop_command": f"pkill -f 'python3 main.py'",
            "restart_command": f"pkill -f 'python3 main.py' && python3 main.py --port {port}"
        }

class ProjectBase(BaseModel):
    name: str
    description: Optional[str] = None
    repo_url: Optional[str] = None
    branch: str = "main"
    deployment_directory: Optional[str] = None
    app_type: str = "Python FastAPI"
    port: Optional[int] = 8000
    start_command: Optional[str] = None
    stop_command: Optional[str] = None
    restart_command: Optional[str] = None
    build_command: Optional[str] = None
    environment_vars: Dict[str, Any] = {}
    domain: Optional[str] = None
    service_name: Optional[str] = None

    @field_validator("app_type")
    def validate_app_type(cls, v):
        if v not in ALLOWED_APP_TYPES:
            raise ValueError(f"Invalid app_type '{v}'. Must be one of {ALLOWED_APP_TYPES}")
        return v

    @field_validator("port")
    def validate_port(cls, v):
        if v is not None and (v < 1 or v > 65535):
            raise ValueError("Port must be between 1 and 65535.")
        return v

class ProjectCreate(ProjectBase):
    @field_validator("deployment_directory")
    def validate_deploy_dir(cls, v, info):
        proj_name = info.data.get("name", "app")
        return sanitize_and_validate_path(v, proj_name)

class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    repo_url: Optional[str] = None
    branch: Optional[str] = None
    deployment_directory: Optional[str] = None
    app_type: Optional[str] = None
    port: Optional[int] = None
    start_command: Optional[str] = None
    stop_command: Optional[str] = None
    restart_command: Optional[str] = None
    build_command: Optional[str] = None
    environment_vars: Optional[Dict[str, Any]] = None
    domain: Optional[str] = None
    service_name: Optional[str] = None
    status: Optional[str] = None

    @field_validator("app_type")
    def validate_app_type(cls, v):
        if v is not None and v not in ALLOWED_APP_TYPES:
            raise ValueError(f"Invalid app_type '{v}'. Must be one of {ALLOWED_APP_TYPES}")
        return v

    @field_validator("deployment_directory")
    def validate_deploy_dir(cls, v, info):
        if v is not None:
            proj_name = info.data.get("name", "app")
            return sanitize_and_validate_path(v, proj_name)
        return v

class ProjectOut(ProjectBase):
    id: int
    deployment_directory: Optional[str] = None
    status: str
    created_at: datetime
    updated_at: datetime
    last_deployment: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(from_attributes=True)
