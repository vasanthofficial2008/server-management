import time
from collections import defaultdict
from fastapi import HTTPException, status, Request

class LoginRateLimiter:
    def __init__(self, max_attempts: int = 5, window_seconds: int = 60):
        self.max_attempts = max_attempts
        self.window_seconds = window_seconds
        self.attempts = defaultdict(list)

    def check(self, request: Request):
        client_ip = self._get_client_ip(request)
        now = time.time()
        
        # Clean up old timestamps outside window
        timestamps = [ts for ts in self.attempts[client_ip] if now - ts < self.window_seconds]
        self.attempts[client_ip] = timestamps
        
        if len(timestamps) >= self.max_attempts:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many failed login attempts. Please wait 60 seconds before trying again."
            )

    def record_failure(self, request: Request):
        client_ip = self._get_client_ip(request)
        self.attempts[client_ip].append(time.time())

    def reset(self, request: Request = None):
        if request:
            client_ip = self._get_client_ip(request)
            if client_ip in self.attempts:
                del self.attempts[client_ip]
        else:
            self.attempts.clear()

    def _get_client_ip(self, request: Request) -> str:
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "unknown"

login_limiter = LoginRateLimiter(max_attempts=5, window_seconds=60)
