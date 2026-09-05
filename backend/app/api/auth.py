from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from jose import jwt

from backend.app.config import settings
from backend.app.database import get_db
from backend.app.models.user import User
from backend.app.schemas.auth import LoginRequest, Token, UserOut
from backend.app.security.auth import verify_password, create_user_session, revoke_session, get_current_user
from backend.app.security.audit import log_audit_event
from backend.app.security.rate_limiter import login_limiter

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/login", response_model=Token)
def login(request: Request, credentials: LoginRequest, db: Session = Depends(get_db)):
    try:
        # Enforce rate limiter
        login_limiter.check(request)
        
        ip_addr = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("user-agent", "unknown")

        user = db.query(User).filter(User.username == credentials.username).first()
        if not user or not verify_password(credentials.password, user.hashed_password):
            login_limiter.record_failure(request)
            try:
                log_audit_event(
                    db,
                    action="LOGIN_FAILURE",
                    username=credentials.username,
                    ip_address=ip_addr,
                    user_agent=user_agent,
                    details=f"Invalid login attempt for username '{credentials.username}'",
                    status="FAILURE"
                )
            except Exception:
                pass
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
            
        if not user.is_active:
            login_limiter.record_failure(request)
            try:
                log_audit_event(
                    db,
                    action="LOGIN_FAILURE",
                    username=user.username,
                    user_id=user.id,
                    ip_address=ip_addr,
                    user_agent=user_agent,
                    details="Login attempt on inactive user account",
                    status="FAILURE"
                )
            except Exception:
                pass
            raise HTTPException(status_code=400, detail="Inactive user account")

        # Reset failure rate limiter on successful authentication
        login_limiter.reset(request)

        # Create session record in database
        access_token = create_user_session(db, user, ip_address=ip_addr, user_agent=user_agent)

        # Audit log login success
        try:
            log_audit_event(
                db,
                action="LOGIN_SUCCESS",
                username=user.username,
                user_id=user.id,
                ip_address=ip_addr,
                user_agent=user_agent,
                details=f"Administrator user '{user.username}' logged in successfully",
                status="SUCCESS"
            )
        except Exception:
            pass

        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user": user
        }
    except HTTPException:
        raise
    except Exception as exc:
        import logging
        logging.getLogger("serverpilot").error(f"Login endpoint failure: {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Authentication error: {str(exc)}"
        )

@router.post("/logout")
def logout(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    ip_addr = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("user-agent", "unknown")
    
    # Extract JTI from bearer token
    auth_header = request.headers.get("authorization", "")
    if auth_header.startswith("Bearer "):
        token_str = auth_header.split(" ")[1]
        try:
            payload = jwt.decode(token_str, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
            jti = payload.get("jti")
            if jti:
                revoke_session(db, jti)
        except Exception:
            pass

    log_audit_event(
        db,
        action="LOGOUT",
        username=current_user.username,
        user_id=current_user.id,
        ip_address=ip_addr,
        user_agent=user_agent,
        details=f"User '{current_user.username}' logged out",
        status="SUCCESS"
    )

    return {"message": "Successfully logged out"}

@router.get("/me", response_model=UserOut)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user
