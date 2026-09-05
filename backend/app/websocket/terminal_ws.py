import json
from typing import Optional
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, status
from sqlalchemy.orm import Session

from backend.app.database import SessionLocal
from backend.app.services.terminal_manager import terminal_session_manager
from backend.app.security.auth import get_user_from_token

router = APIRouter(tags=["WebSockets"])

@router.websocket("/ws/terminal/{session_id}")
async def websocket_terminal_session(
    websocket: WebSocket,
    session_id: str,
    token: Optional[str] = Query(None)
):
    """Bidirectional WebSocket terminal stream for PTY session."""
    # Authenticate token
    db: Session = SessionLocal()
    try:
        user = None
        if token:
            user = get_user_from_token(db, token)
        
        if not user:
            await websocket.accept()
            await websocket.send_text("\r\n\033[1;31m[401 Unauthorized: Valid authentication token required]\033[0m\r\n")
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return

        session = terminal_session_manager.get_session(session_id)
        if not session or session.status != "active":
            await websocket.accept()
            await websocket.send_text(f"\r\n\033[1;31m[404 Session Error: Terminal session '{session_id}' not found or expired]\033[0m\r\n")
            await websocket.close(code=4004)
            return

        await websocket.accept()

        import asyncio
        session.loop = asyncio.get_running_loop()
        session.active_websockets.add(websocket)

        # Send existing output history scrollback buffer upon connection
        history = session.get_output_history()
        if history:
            await websocket.send_text(history)

        while True:
            raw_msg = await websocket.receive_text()
            if not raw_msg:
                continue

            try:
                msg_json = json.loads(raw_msg)
                if isinstance(msg_json, dict):
                    msg_type = msg_json.get("type")
                    if msg_type == "input":
                        input_data = msg_json.get("data", "")
                        session.write_input(input_data, db=db)
                    elif msg_type == "resize":
                        cols = int(msg_json.get("cols", 80))
                        rows = int(msg_json.get("rows", 24))
                        session.set_window_size(cols, rows)
                    elif msg_type == "ping":
                        session.last_activity = session.created_at  # Keepalive ping
                    continue
            except (json.JSONDecodeError, TypeError, ValueError):
                pass

            # Fallback to direct raw input text
            session.write_input(raw_msg, db=db)

    except WebSocketDisconnect:
        pass
    except Exception as err:
        try:
            await websocket.send_text(f"\r\n\033[1;31m[Terminal Error: {str(err)}]\033[0m\r\n")
        except Exception:
            pass
    finally:
        if 'session' in locals() and session:
            session.active_websockets.discard(websocket)
        db.close()
