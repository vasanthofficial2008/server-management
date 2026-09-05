from fastapi import APIRouter

from backend.app.api.health import router as health_router
from backend.app.api.auth import router as auth_router
from backend.app.api.projects import router as projects_router
from backend.app.api.services import router as services_router
from backend.app.api.deployments import router as deployments_router
from backend.app.api.domains import router as domains_router
from backend.app.api.server import router as server_router
from backend.app.api.settings import router as settings_router
from backend.app.api.terminal import router as terminal_router
from backend.app.api.logs import router as logs_router

api_router = APIRouter(prefix="/api")
api_router.include_router(health_router)
api_router.include_router(auth_router)
api_router.include_router(projects_router)
api_router.include_router(services_router)
api_router.include_router(deployments_router)
api_router.include_router(domains_router)
api_router.include_router(server_router)
api_router.include_router(settings_router)
api_router.include_router(terminal_router)
api_router.include_router(logs_router)
