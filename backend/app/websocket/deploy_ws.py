import asyncio
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from backend.app.services.deploy_engine import deploy_log_streams

router = APIRouter(tags=["WebSockets"])

@router.websocket("/ws/deployments/{deployment_id}")
async def websocket_deployment_logs(websocket: WebSocket, deployment_id: int):
    await websocket.accept()
    last_idx = 0
    try:
        while True:
            stream = deploy_log_streams.get(deployment_id, [])
            if len(stream) > last_idx:
                new_logs = stream[last_idx:]
                last_idx = len(stream)
                for log_line in new_logs:
                    await websocket.send_text(log_line)
            await asyncio.sleep(0.5)
    except WebSocketDisconnect:
        pass
    except Exception:
        pass
