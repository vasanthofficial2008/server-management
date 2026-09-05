import json
import asyncio
from typing import Optional
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

from backend.app.database import SessionLocal
from backend.app.services.log_service import get_centralized_logs

router = APIRouter(tags=["WebSockets"])

@router.websocket("/ws/logs")
async def websocket_logs(websocket: WebSocket):
    """Real-time streaming WebSocket endpoint for centralized logs."""
    await websocket.accept()
    
    filter_params = {
        "category": None,
        "project_id": None,
        "service_id": None,
        "level": None,
        "search": None
    }
    
    last_ids = set()

    async def receive_filters():
        nonlocal filter_params
        while True:
            try:
                msg = await websocket.receive_text()
                if msg:
                    data = json.loads(msg)
                    if isinstance(data, dict):
                        for k in filter_params.keys():
                            if k in data:
                                filter_params[k] = data[k]
            except (WebSocketDisconnect, RuntimeError):
                break
            except Exception:
                pass

    receive_task = asyncio.create_task(receive_filters())

    try:
        while True:
            db: Session = SessionLocal()
            try:
                items, total = get_centralized_logs(
                    db=db,
                    category=filter_params["category"],
                    project_id=filter_params["project_id"],
                    service_id=filter_params["service_id"],
                    level=filter_params["level"],
                    search=filter_params["search"],
                    page=1,
                    page_size=100
                )
                
                current_ids = {e["id"] for e in items}
                if current_ids != last_ids:
                    await websocket.send_json({
                        "type": "logs_update",
                        "items": items,
                        "total": total
                    })
                    last_ids = current_ids
            finally:
                db.close()

            await asyncio.sleep(2.0)
    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        receive_task.cancel()
