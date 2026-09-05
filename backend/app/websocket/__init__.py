from fastapi import APIRouter

from backend.app.websocket.stats_ws import router as stats_router
from backend.app.websocket.terminal_ws import router as terminal_router
from backend.app.websocket.logs_ws import router as logs_router
from backend.app.websocket.deploy_ws import router as deploy_router

ws_router = APIRouter()
ws_router.include_router(stats_router)
ws_router.include_router(terminal_router)
ws_router.include_router(logs_router)
ws_router.include_router(deploy_router)
