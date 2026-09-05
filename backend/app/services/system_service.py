import psutil
import time
import os
import sys
import platform
import socket
from datetime import datetime
from typing import Dict, Any, List

BOOT_TIME = psutil.boot_time()

def get_server_overview() -> Dict[str, Any]:
    """Retrieve system software environment and hardware specifications."""
    try:
        hostname = socket.gethostname()
    except Exception:
        hostname = platform.node() or "unknown-host"

    uptime_seconds = round(time.time() - BOOT_TIME)
    days = uptime_seconds // 86400
    hours = (uptime_seconds % 86400) // 3600
    minutes = (uptime_seconds % 3600) // 60
    uptime_parts = []
    if days > 0:
        uptime_parts.append(f"{days}d")
    if hours > 0:
        uptime_parts.append(f"{hours}h")
    uptime_parts.append(f"{minutes}m")
    uptime_human = " ".join(uptime_parts) if uptime_parts else "0m"

    boot_time_iso = datetime.fromtimestamp(BOOT_TIME).isoformat()

    try:
        cpu_logical = psutil.cpu_count(logical=True) or 1
        cpu_physical = psutil.cpu_count(logical=False) or cpu_logical
    except Exception:
        cpu_logical = 1
        cpu_physical = 1

    return {
        "hostname": hostname,
        "os_name": platform.system(),
        "os_release": platform.release(),
        "platform": f"{platform.system()} {platform.release()}",
        "architecture": " ".join(platform.architecture()),
        "python_version": sys.version.split()[0],
        "uptime_seconds": uptime_seconds,
        "uptime_human": uptime_human,
        "boot_time_iso": boot_time_iso,
        "cpu_cores_logical": cpu_logical,
        "cpu_cores_physical": cpu_physical
    }

def get_server_resources() -> Dict[str, Any]:
    """Retrieve real-time resource consumption (CPU, RAM, Disk, Load, Network)."""
    # CPU
    try:
        cpu_percent = psutil.cpu_percent(interval=None)
    except Exception:
        cpu_percent = 0.0

    # RAM Total / Used / Free
    try:
        mem = psutil.virtual_memory()
        memory = {
            "total_gb": round(mem.total / (1024 ** 3), 2),
            "used_gb": round(mem.used / (1024 ** 3), 2),
            "free_gb": round(mem.available / (1024 ** 3), 2),
            "percent": mem.percent
        }
    except Exception:
        memory = {"total_gb": 0.0, "used_gb": 0.0, "free_gb": 0.0, "percent": 0.0}

    # Disk Total / Used / Free
    try:
        disk_path = "/" if platform.system() != "Windows" else "C:\\"
        d = psutil.disk_usage(disk_path)
        disk = {
            "total_gb": round(d.total / (1024 ** 3), 2),
            "used_gb": round(d.used / (1024 ** 3), 2),
            "free_gb": round(d.free / (1024 ** 3), 2),
            "percent": d.percent
        }
    except Exception:
        disk = {"total_gb": 0.0, "used_gb": 0.0, "free_gb": 0.0, "percent": 0.0}

    # Load Averages
    try:
        load_avg = list(os.getloadavg())
    except (AttributeError, OSError):
        cpu_cores = psutil.cpu_count() or 1
        load_val = round((cpu_percent / 100.0) * cpu_cores, 2)
        load_avg = [load_val, load_val, load_val]

    # Network Stats
    try:
        net_io = psutil.net_io_counters()
        net_addrs = psutil.net_if_addrs()
        interface_names = [iface for iface in net_addrs.keys() if iface != "lo"]
        network = {
            "bytes_sent_mb": round(net_io.bytes_sent / (1024 * 1024), 2),
            "bytes_recv_mb": round(net_io.bytes_recv / (1024 * 1024), 2),
            "packets_sent": net_io.packets_sent,
            "packets_recv": net_io.packets_recv,
            "interfaces": interface_names[:5]
        }
    except Exception:
        network = {
            "bytes_sent_mb": 0.0,
            "bytes_recv_mb": 0.0,
            "packets_sent": 0,
            "packets_recv": 0,
            "interfaces": []
        }

    return {
        "cpu_percent": cpu_percent,
        "memory": memory,
        "disk": disk,
        "load_avg": load_avg,
        "network": network
    }

def get_system_stats() -> Dict[str, Any]:
    """Legacy backward-compatible composite system stats dict."""
    overview = get_server_overview()
    resources = get_server_resources()

    return {
        "cpu_percent": resources["cpu_percent"],
        "cpu_cores": overview["cpu_cores_logical"],
        "memory_total_gb": resources["memory"]["total_gb"],
        "memory_used_gb": resources["memory"]["used_gb"],
        "memory_free_gb": resources["memory"]["free_gb"],
        "memory_percent": resources["memory"]["percent"],
        "disk_total_gb": resources["disk"]["total_gb"],
        "disk_used_gb": resources["disk"]["used_gb"],
        "disk_free_gb": resources["disk"]["free_gb"],
        "disk_percent": resources["disk"]["percent"],
        "uptime_seconds": overview["uptime_seconds"],
        "uptime_human": overview["uptime_human"],
        "platform": overview["platform"],
        "hostname": overview["hostname"],
        "python_version": overview["python_version"],
        "load_avg": resources["load_avg"],
        "network": resources["network"]
    }

def get_top_processes(limit: int = 15) -> List[Dict[str, Any]]:
    """Retrieve top active system processes with graceful permission handling."""
    processes = []
    for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_info', 'status', 'username']):
        try:
            info = proc.info
            mem_mb = round((info['memory_info'].rss if info['memory_info'] else 0) / (1024 * 1024), 1)
            processes.append({
                "pid": info['pid'],
                "name": info['name'] or "unknown",
                "cpu_percent": info['cpu_percent'] or 0.0,
                "memory_mb": mem_mb,
                "status": info['status'] or "running",
                "username": info['username'] or "system"
            })
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess, PermissionError):
            continue
            
    processes.sort(key=lambda p: p['memory_mb'], reverse=True)
    return processes[:limit]
