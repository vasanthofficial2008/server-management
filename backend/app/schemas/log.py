from datetime import datetime
from typing import Optional, List, Any
from pydantic import BaseModel, ConfigDict

class LogEntry(BaseModel):
    id: str
    timestamp: str
    category: str  # deployment, application, systemd, audit
    level: str     # INFO, WARNING, ERROR, SUCCESS
    source: str
    message: str

    model_config = ConfigDict(from_attributes=True)

class PaginatedLogsResponse(BaseModel):
    items: List[LogEntry]
    total: int
    page: int
    page_size: int
    total_pages: int
