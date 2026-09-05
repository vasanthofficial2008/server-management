import asyncio
import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from backend.app.services.system_service import get_system_stats

router = APIRouter(tags=["WebSockets"])

@router.websocket("/ws/stats")
async def websocket_stats(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            stats = get_system_stats()
            await websocket.send_json(stats)
            await asyncio.sleep(1.5)
    except WebSocketDisconnect:
        pass
    except Exception:
        pass
