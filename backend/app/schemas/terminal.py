from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict

class TerminalSessionCreate(BaseModel):
    cols: Optional[int] = 80
    rows: Optional[int] = 24

class TerminalSessionOut(BaseModel):
    session_id: str
    username: str
    os_user: str
    created_at: datetime
    last_activity: datetime
    expires_at: datetime
    cols: int
    rows: int
    status: str

    model_config = ConfigDict(from_attributes=True)

class TerminalResize(BaseModel):
    cols: int
    rows: int
