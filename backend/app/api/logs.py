import math
from typing import Optional
from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.models.user import User
from backend.app.schemas.log import PaginatedLogsResponse, LogEntry
from backend.app.services.log_service import get_centralized_logs
from backend.app.security.auth import get_current_user

router = APIRouter(prefix="/logs", tags=["Logs"])

@router.get("", response_model=PaginatedLogsResponse)
def list_centralized_logs(
    category: Optional[str] = Query(None, description="deployment, application, systemd, audit"),
    project_id: Optional[int] = Query(None),
    service_id: Optional[int] = Query(None),
    level: Optional[str] = Query(None, description="INFO, WARNING, ERROR, SUCCESS"),
    search: Optional[str] = Query(None, description="Text search query"),
    start_date: Optional[str] = Query(None, description="ISO start date filter"),
    end_date: Optional[str] = Query(None, description="ISO end date filter"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Retrieve paginated centralized logs with search, category, level, and date filters."""
    items, total = get_centralized_logs(
        db=db,
        category=category,
        project_id=project_id,
        service_id=service_id,
        level=level,
        search=search,
        start_date=start_date,
        end_date=end_date,
        page=page,
        page_size=page_size
    )

    total_pages = math.ceil(total / page_size) if total > 0 else 1

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages
    }

@router.get("/download")
def download_centralized_logs(
    category: Optional[str] = Query(None),
    project_id: Optional[int] = Query(None),
    service_id: Optional[int] = Query(None),
    level: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Download matching centralized logs as a plain text file."""
    items, total = get_centralized_logs(
        db=db,
        category=category,
        project_id=project_id,
        service_id=service_id,
        level=level,
        search=search,
        start_date=start_date,
        end_date=end_date,
        page=1,
        page_size=1000
    )

    lines = []
    lines.append(f"# ServerPilot Centralized Log Export ({len(items)} entries)")
    lines.append(f"# Generated: {category or 'all categories'} | User: {current_user.username}")
    lines.append("-" * 80)
    for entry in items:
        lines.append(f"[{entry['timestamp']}] [{entry['level']}] [{entry['category'].upper()}] [{entry['source']}] {entry['message']}")

    content = "\n".join(lines)
    filename = f"serverpilot_logs_{(category or 'all')}.log"

    return Response(
        content=content,
        media_type="text/plain",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )
