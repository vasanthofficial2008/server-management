import os
import uuid
import hashlib
import hmac
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from backend.app.config import settings
from backend.app.database import get_db
from backend.app.models.user import User
from backend.app.models.session import SessionModel

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Salted PBKDF2 SHA256 password verification."""
    parts = hashed_password.split("$")
    if len(parts) == 3 and parts[0] == "pbkdf2_sha256":
        salt = parts[1].encode('utf-8')
        iterations = 100000
        key = hashlib.pbkdf2_hmac('sha256', plain_password.encode('utf-8'), salt, iterations)
        return hmac.compare_digest(key.hex(), parts[2])
    return plain_password == hashed_password

def get_password_hash(password: str) -> str:
    """Generate salted PBKDF2 SHA256 password hash."""
    salt = os.urandom(16).hex()
    iterations = 100000
    key = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt.encode('utf-8'), iterations)
    return f"pbkdf2_sha256${salt}${key.hex()}"

def create_access_token_data(data: dict, expires_delta: Optional[timedelta] = None) -> tuple[str, str, datetime]:
    jti = str(uuid.uuid4())
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire, "jti": jti})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt, jti, expire

def create_user_session(db: Session, user: User, ip_address: str = None, user_agent: str = None) -> str:
    token, jti, expire = create_access_token_data(data={"sub": user.username})
    session_rec = SessionModel(
        user_id=user.id,
        token_jti=jti,
        ip_address=ip_address,
        user_agent=user_agent,
        expires_at=expire,
        is_revoked=False
    )
    db.add(session_rec)
    db.commit()
    return token

def revoke_session(db: Session, token_jti: str) -> bool:
    session_rec = db.query(SessionModel).filter(SessionModel.token_jti == token_jti).first()
    if session_rec:
        session_rec.is_revoked = True
        db.commit()
        return True
    return False

def get_current_user(
    request: Request,
    token: Optional[str] = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token required",
            headers={"WWW-Authenticate": "Bearer"}
        )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        username: str = payload.get("sub")
        jti: str = payload.get("jti")
        if username is None or jti is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token claims")
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not validate token credentials")

    # Check session status in database
    session_rec = db.query(SessionModel).filter(SessionModel.token_jti == jti).first()
    if not session_rec or session_rec.is_revoked or session_rec.expires_at < datetime.utcnow():
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session expired or revoked")

    user = db.query(User).filter(User.username == username).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Inactive or non-existent user account")
        
    return user

def get_user_from_token(db: Session, token: str) -> Optional[User]:
    """Retrieve active authenticated User from token string (useful for WebSockets)."""
    if not token:
        return None
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        username: str = payload.get("sub")
        jti: str = payload.get("jti")
        if not username or not jti:
            return None
    except JWTError:
        return None

    session_rec = db.query(SessionModel).filter(SessionModel.token_jti == jti).first()
    if not session_rec or session_rec.is_revoked or session_rec.expires_at < datetime.utcnow():
        return None

    user = db.query(User).filter(User.username == username).first()
    if not user or not user.is_active:
        return None

    return user
