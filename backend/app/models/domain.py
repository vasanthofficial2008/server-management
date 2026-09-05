from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from backend.app.database import Base

class Domain(Base):
    __tablename__ = "domains"

    id = Column(Integer, primary_key=True, index=True)
    domain_name = Column(String, unique=True, index=True, nullable=False)
    subdomain = Column(String, nullable=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True)
    project_name = Column(String, nullable=True)
    local_host = Column(String, default="127.0.0.1")
    local_port = Column(Integer, nullable=False, default=8000)
    https_enabled = Column(Boolean, default=True)
    ssl_enabled = Column(Boolean, default=True)
    tunnel_status = Column(String, default="connected")  # connected, disconnected, active, degraded
    status = Column(String, default="active")            # active, pending, error
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
