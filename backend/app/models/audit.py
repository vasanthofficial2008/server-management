from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Text
from backend.app.database import Base

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=True)
    username = Column(String, nullable=True)
    action = Column(String, index=True, nullable=False)
    ip_address = Column(String, nullable=True)
    user_agent = Column(String, nullable=True)
    details = Column(Text, nullable=True)
    status = Column(String, default="SUCCESS") # SUCCESS, FAILURE
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
