from typing import List
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.models.user import User
from backend.app.schemas.terminal import TerminalSessionCreate, TerminalSessionOut
from backend.app.services.terminal_manager import terminal_session_manager
from backend.app.security.auth import get_current_user
from backend.app.security.audit import log_audit_event

router = APIRouter(prefix="/terminal", tags=["Terminal"])

@router.post("/session", response_model=TerminalSessionOut, status_code=status.HTTP_201_CREATED)
def create_terminal_session(
    request: Request,
    session_in: TerminalSessionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new PTY terminal session for authenticated administrator."""
    session = terminal_session_manager.create_session(
        user_id=current_user.id,
        username=current_user.username,
        cols=session_in.cols or 80,
        rows=session_in.rows or 24
    )

    log_audit_event(
        db,
        action="TERMINAL_SESSION_START",
        username=current_user.username,
        user_id=current_user.id,
        ip_address=request.client.host if request.client else "unknown",
        details=f"Created PTY terminal session #{session.session_id} under restricted OS user '{session.os_user}'"
    )

    return session.to_dict()

@router.get("/sessions", response_model=List[TerminalSessionOut])
def list_terminal_sessions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List active PTY terminal sessions for current user."""
    return terminal_session_manager.list_user_sessions(current_user.id)

@router.delete("/session/{session_id}")
def close_terminal_session(
    request: Request,
    session_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Terminate and close specified PTY terminal session."""
    closed = terminal_session_manager.close_session(session_id, username=current_user.username)
    if not closed:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Terminal session '{session_id}' not found or already closed."
        )

    log_audit_event(
        db,
        action="TERMINAL_SESSION_END",
        username=current_user.username,
        user_id=current_user.id,
        ip_address=request.client.host if request.client else "unknown",
        details=f"Closed PTY terminal session #{session_id}"
    )

    return {"message": f"Terminal session '{session_id}' terminated successfully."}
