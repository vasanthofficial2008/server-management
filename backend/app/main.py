from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from backend.app.config import settings
from backend.app.database import engine, Base
from backend.app.api import api_router
from backend.app.websocket import ws_router

# Ensure models are imported so metadata is populated
import backend.app.models

# Initialize database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Production-Grade Ubuntu Server Control Panel & Deployment Engine",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API and WebSocket routers
app.include_router(api_router)
app.include_router(ws_router)

# Mount Frontend static assets
frontend_dir = Path(__file__).resolve().parent.parent.parent / "frontend"
if frontend_dir.exists():
    app.mount("/css", StaticFiles(directory=frontend_dir / "css"), name="css")
    app.mount("/js", StaticFiles(directory=frontend_dir / "js"), name="js")

    @app.get("/login.html")
    def serve_login():
        return FileResponse(frontend_dir / "login.html")

    @app.get("/{full_path:path}")
    def serve_spa(full_path: str):
        # Serve index.html for all SPA frontend routes unless it's an API route
        file_path = frontend_dir / full_path
        if file_path.exists() and file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(frontend_dir / "index.html")
