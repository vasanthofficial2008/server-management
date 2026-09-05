from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Text, JSON
from backend.app.database import Base

class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    description = Column(Text, nullable=True)
    repo_url = Column(String, nullable=True)
    branch = Column(String, default="main")
    deployment_directory = Column(String, nullable=True)
    app_type = Column(String, default="Python FastAPI") # Static HTML/CSS/JavaScript, Python FastAPI, Python Flask, Python Custom
    port = Column(Integer, nullable=True)
    start_command = Column(String, nullable=True)
    stop_command = Column(String, nullable=True)
    restart_command = Column(String, nullable=True)
    build_command = Column(String, nullable=True)
    environment_vars = Column(JSON, default=dict)
    domain = Column(String, nullable=True)
    service_name = Column(String, nullable=True)
    status = Column(String, default="stopped") # active, building, stopped, error
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
