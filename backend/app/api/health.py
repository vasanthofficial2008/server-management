from datetime import datetime
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from backend.app.config import settings
from backend.app.database import get_db

router = APIRouter(tags=["Health"])

@router.get("/health")
def get_health_status(db: Session = Depends(get_db)):
    """Health check endpoint returning application status, database connectivity, and runtime metrics."""
    db_status = "connected"
    try:
        db.execute(text("SELECT 1"))
    except Exception as e:
        db_status = f"error: {str(e)}"
        
    return {
        "status": "healthy" if db_status == "connected" else "degraded",
        "application": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.ENV,
        "database": db_status,
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }
