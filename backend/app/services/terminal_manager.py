import os
import sys
import time
import uuid
import signal
import threading
import subprocess
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Set
from fastapi import HTTPException, status, WebSocket
from sqlalchemy.orm import Session

from backend.app.config import settings
from backend.app.security.audit import log_audit_event

# Optional PTY modules on POSIX systems
try:
    import pty
    import fcntl
    import termios
    import struct
    HAS_PTY = True
except ImportError:
    HAS_PTY = False

MAX_SESSIONS_PER_USER = 5
MAX_GLOBAL_SESSIONS = 20
SESSION_TTL_SECONDS = 3600  # 1 hour maximum duration
IDLE_TIMEOUT_SECONDS = 900  # 15 minutes idle timeout
MAX_BUFFER_CHARS = 100000   # 100KB output scrollback buffer

class PTYSession:
    def __init__(self, user_id: int, username: str, cols: int = 80, rows: int = 24):
        self.session_id = f"term-{uuid.uuid4().hex[:10]}"
        self.user_id = user_id
        self.username = username
        self.cols = cols
        self.rows = rows
        self.created_at = datetime.utcnow()
        self.last_activity = datetime.utcnow()
        self.expires_at = self.created_at + timedelta(seconds=SESSION_TTL_SECONDS)
        self.status = "active"
        self.os_user = "serverpilot-term"
        
        self.master_fd: Optional[int] = None
        self.slave_fd: Optional[int] = None
        self.process: Optional[subprocess.Popen] = None
        
        self.output_buffer: List[str] = []
        self.command_line_buffer: str = ""
        self.active_websockets: Set[WebSocket] = set()
        self.loop: Optional[Any] = None
        self._lock = threading.Lock()
        self._running = False
        self._reader_thread: Optional[threading.Thread] = None

        self._spawn_terminal()

    def _spawn_terminal(self):
        """Spawn a PTY terminal process under a restricted non-root OS user without secret leakage."""
        # Clean environment secrets
        clean_env = os.environ.copy()
        for secret_key in ["SECRET_KEY", "DATABASE_URL", "ADMIN_PASSWORD", "PASSWORD", "JWT_SECRET"]:
            clean_env.pop(secret_key, None)
        
        clean_env["TERM"] = "xterm-256color"
        clean_env["COLORTERM"] = "truecolor"
        clean_env["PAGER"] = "cat"

        # Determine restricted shell launch command
        # DO NOT run as root under any circumstance!
        if os.name != 'nt' and HAS_PTY:
            # Check if running as root or if restricted user exists
            is_root = (os.geteuid() == 0)
            if is_root:
                # Force switch to restricted non-root user 'serverpilot-term' or 'nobody'
                shell_cmd = ["runuser", "-u", "serverpilot-term", "--", "/bin/bash", "--noprofile", "--norc"]
            else:
                shell_cmd = ["/bin/bash", "--noprofile", "--norc"]

            master_fd, slave_fd = pty.openpty()
            self.master_fd = master_fd
            self.slave_fd = slave_fd

            # Set initial PTY window size
            self.set_window_size(self.cols, self.rows)

            self.process = subprocess.Popen(
                shell_cmd,
                stdin=slave_fd,
                stdout=slave_fd,
                stderr=slave_fd,
                cwd=str(settings.DEPLOYMENTS_DIR),
                env=clean_env,
                preexec_fn=os.setsid,
                close_fds=True
            )
            # Close slave fd in parent process
            os.close(slave_fd)
            self.slave_fd = None
        else:
            # Fallback for Windows or non-PTY test execution
            shell_cmd = ["powershell.exe", "-NoProfile"] if os.name == 'nt' else ["/bin/bash", "--noprofile", "--norc"]
            self.process = subprocess.Popen(
                shell_cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=False,
                bufsize=0,
                env=clean_env
            )

        self._running = True
        self._reader_thread = threading.Thread(target=self._read_output_loop, daemon=True)
        self._reader_thread.start()

        # Add initial terminal banner
        banner = (
            f"\r\n\033[1;36m=== ServerPilot Restricted Web Terminal (Session #{self.session_id}) ===\033[0m\r\n"
            f"\033[1;33m⚠️ WARNING: Operating under restricted OS user '{self.os_user}'. Root access disabled.\033[0m\r\n"
            f"\033[90mSession started at {self.created_at.strftime('%Y-%m-%d %H:%M:%S UTC')}. Type 'exit' to terminate.\033[0m\r\n\r\n"
        )
        self._append_output(banner)

    def set_window_size(self, cols: int, rows: int):
        """Update PTY window size using termios TIOCSWINSZ ioctl on POSIX systems."""
        self.cols = max(10, min(cols, 300))
        self.rows = max(5, min(rows, 100))
        if os.name != 'nt' and HAS_PTY and self.master_fd is not None:
            try:
                fcntl.ioctl(
                    self.master_fd,
                    termios.TIOCSWINSZ,
                    struct.pack("HHHH", self.rows, self.cols, 0, 0)
                )
            except Exception:
                pass

    def _append_output(self, text: str):
        with self._lock:
            self.output_buffer.append(text)
            # Limit total buffer length
            total_len = sum(len(chunk) for chunk in self.output_buffer)
            while total_len > MAX_BUFFER_CHARS and self.output_buffer:
                popped = self.output_buffer.pop(0)
                total_len -= len(popped)

    def get_output_history(self) -> str:
        with self._lock:
            return "".join(self.output_buffer)

    def _read_output_loop(self):
        """Background thread continuously reading PTY output and forwarding to WebSockets."""
        while self._running:
            try:
                if self.master_fd is not None:
                    # POSIX PTY read
                    data_bytes = os.read(self.master_fd, 4096)
                    if not data_bytes:
                        break
                    text = data_bytes.decode('utf-8', errors='replace')
                elif self.process and self.process.stdout:
                    # Fallback pipe read
                    data_bytes = self.process.stdout.read(1024)
                    if not data_bytes:
                        break
                    text = data_bytes.decode('utf-8', errors='replace')
                else:
                    break

                self._append_output(text)

                # Broadcast to active WebSockets
                self._broadcast_text(text)
            except (OSError, ValueError):
                break
            except Exception:
                break

        self.status = "closed"
        self._broadcast_text("\r\n\033[1;31m[Terminal session closed]\033[0m\r\n")

    def _broadcast_text(self, text: str):
        dead_sockets = set()
        with self._lock:
            sockets = list(self.active_websockets)
            loop = self.loop

        if not sockets:
            return

        for ws in sockets:
            try:
                if loop and loop.is_running():
                    import asyncio
                    asyncio.run_coroutine_threadsafe(ws.send_text(text), loop)
            except Exception:
                dead_sockets.add(ws)

        if dead_sockets:
            with self._lock:
                self.active_websockets -= dead_sockets

    def write_input(self, data: str, db: Optional[Session] = None):
        """Write user keystrokes/data to PTY process and record command audits."""
        self.last_activity = datetime.utcnow()
        if not self._running or self.status != "active":
            return

        # Audit command buffering
        for char in data:
            if char in ['\r', '\n']:
                cmd = self.command_line_buffer.strip()
                if cmd and db:
                    try:
                        log_audit_event(
                            db,
                            action="TERMINAL_COMMAND",
                            username=self.username,
                            details=f"Terminal session #{self.session_id} command: '{cmd}'"
                        )
                    except Exception:
                        pass
                self.command_line_buffer = ""
            elif char == '\x03':  # Ctrl+C
                self.command_line_buffer = ""
                # Send SIGINT signal to process group on POSIX
                if self.process and os.name != 'nt':
                    try:
                        os.killpg(os.getpgid(self.process.pid), signal.SIGINT)
                    except Exception:
                        pass
            elif char in ['\b', '\x7f']:  # Backspace
                self.command_line_buffer = self.command_line_buffer[:-1]
            elif ord(char) >= 32 and ord(char) <= 126:
                self.command_line_buffer += char

        # Write to master fd / process stdin
        try:
            if self.master_fd is not None:
                os.write(self.master_fd, data.encode('utf-8'))
            elif self.process and self.process.stdin:
                self.process.stdin.write(data.encode('utf-8'))
                self.process.stdin.flush()
        except Exception:
            pass

    def is_expired(self) -> bool:
        now = datetime.utcnow()
        if now > self.expires_at:
            return True
        if (now - self.last_activity).total_seconds() > IDLE_TIMEOUT_SECONDS:
            return True
        return False

    def close(self):
        self._running = False
        self.status = "closed"

        if self.process:
            try:
                if os.name != 'nt':
                    os.killpg(os.getpgid(self.process.pid), signal.SIGTERM)
                else:
                    self.process.terminate()
            except Exception:
                pass
            try:
                self.process.wait(timeout=2)
            except Exception:
                try:
                    if os.name != 'nt':
                        os.killpg(os.getpgid(self.process.pid), signal.SIGKILL)
                    else:
                        self.process.kill()
                except Exception:
                    pass

        if self.master_fd is not None:
            try:
                os.close(self.master_fd)
            except Exception:
                pass
            self.master_fd = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "username": self.username,
            "os_user": self.os_user,
            "created_at": self.created_at,
            "last_activity": self.last_activity,
            "expires_at": self.expires_at,
            "cols": self.cols,
            "rows": self.rows,
            "status": self.status
        }


class TerminalSessionManager:
    """Manager holding active PTY terminal sessions."""
    def __init__(self):
        self._sessions: Dict[str, PTYSession] = {}
        self._lock = threading.Lock()

    def create_session(self, user_id: int, username: str, cols: int = 80, rows: int = 24) -> PTYSession:
        self._cleanup_expired_sessions()
        with self._lock:
            # Check user session count
            user_sessions = [s for s in self._sessions.values() if s.user_id == user_id and s.status == "active"]
            if len(user_sessions) >= MAX_SESSIONS_PER_USER:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Maximum limit of {MAX_SESSIONS_PER_USER} concurrent terminal sessions reached for user."
                )

            if len(self._sessions) >= MAX_GLOBAL_SESSIONS:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Global maximum limit of terminal sessions reached. Please close an existing session."
                )

            session = PTYSession(user_id=user_id, username=username, cols=cols, rows=rows)
            self._sessions[session.session_id] = session
            return session

    def get_session(self, session_id: str) -> Optional[PTYSession]:
        self._cleanup_expired_sessions()
        with self._lock:
            session = self._sessions.get(session_id)
            if session and session.is_expired():
                session.close()
                del self._sessions[session_id]
                return None
            return session

    def list_user_sessions(self, user_id: int) -> List[Dict[str, Any]]:
        self._cleanup_expired_sessions()
        with self._lock:
            return [s.to_dict() for s in self._sessions.values() if s.user_id == user_id and s.status == "active"]

    def close_session(self, session_id: str, username: str = "system") -> bool:
        with self._lock:
            session = self._sessions.get(session_id)
            if session:
                session.close()
                del self._sessions[session_id]
                return True
            return False

    def _cleanup_expired_sessions(self):
        with self._lock:
            expired_ids = [sid for sid, s in self._sessions.items() if s.is_expired() or s.status == "closed"]
            for sid in expired_ids:
                s = self._sessions.pop(sid, None)
                if s:
                    s.close()

terminal_session_manager = TerminalSessionManager()
