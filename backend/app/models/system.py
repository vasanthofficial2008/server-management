from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Text
from backend.app.database import Base

class SystemEvent(Base):
    __tablename__ = "system_events"

    id = Column(Integer, primary_key=True, index=True)
    level = Column(String, default="INFO") # INFO, WARNING, ERROR, CRITICAL
    category = Column(String, default="SYSTEM") # SYSTEM, DEPLOYMENT, SECURITY, SERVICE
    message = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)

class Setting(Base):
    __tablename__ = "settings"

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String, unique=True, index=True, nullable=False)
    value = Column(Text, nullable=False)
    category = Column(String, default="general")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
