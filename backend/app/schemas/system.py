from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, ConfigDict

class MemoryStats(BaseModel):
    total_gb: float
    used_gb: float
    free_gb: float
    percent: float

class DiskStats(BaseModel):
    total_gb: float
    used_gb: float
    free_gb: float
    percent: float

class NetworkStats(BaseModel):
    bytes_sent_mb: float
    bytes_recv_mb: float
    packets_sent: int
    packets_recv: int
    interfaces: List[str]

class ServerOverviewOut(BaseModel):
    hostname: str
    os_name: str
    os_release: str
    platform: str
    architecture: str
    python_version: str
    uptime_seconds: float
    uptime_human: str
    boot_time_iso: str
    cpu_cores_logical: int
    cpu_cores_physical: int

class ServerResourcesOut(BaseModel):
    cpu_percent: float
    memory: MemoryStats
    disk: DiskStats
    load_avg: List[float]
    network: NetworkStats

class SystemStatsOut(BaseModel):
    cpu_percent: float
    cpu_cores: int
    memory_total_gb: float
    memory_used_gb: float
    memory_free_gb: Optional[float] = 0.0
    memory_percent: float
    disk_total_gb: float
    disk_used_gb: float
    disk_free_gb: Optional[float] = 0.0
    disk_percent: float
    uptime_seconds: float
    uptime_human: str
    platform: str
    hostname: str
    python_version: Optional[str] = "3.x"
    load_avg: List[float]

class ProcessInfo(BaseModel):
    pid: int
    name: str
    cpu_percent: float
    memory_mb: float
    status: str
    username: str

class SystemEventOut(BaseModel):
    id: int
    level: str
    category: str
    message: str
    timestamp: datetime

    model_config = ConfigDict(from_attributes=True)

class AuditLogOut(BaseModel):
    id: int
    user_id: Optional[int] = None
    username: Optional[str] = None
    action: str
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    details: Optional[str] = None
    status: str
    timestamp: datetime

    model_config = ConfigDict(from_attributes=True)

class SettingOut(BaseModel):
    id: int
    key: str
    value: str
    category: str
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class SettingUpdate(BaseModel):
    key: str
    value: str
    category: str = "general"
