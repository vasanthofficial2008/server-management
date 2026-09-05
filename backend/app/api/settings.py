from typing import List
from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.models.user import User
from backend.app.models.system import Setting
from backend.app.schemas.system import SettingOut, SettingUpdate
from backend.app.security.auth import get_current_user
from backend.app.security.audit import log_audit_event

router = APIRouter(prefix="/settings", tags=["Settings"])

@router.get("", response_model=List[SettingOut])
def list_settings(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return db.query(Setting).all()

@router.post("", response_model=SettingOut)
def update_setting(
    request: Request,
    setting_in: SettingUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    setting = db.query(Setting).filter(Setting.key == setting_in.key).first()
    if setting:
        setting.value = setting_in.value
        setting.category = setting_in.category
    else:
        setting = Setting(key=setting_in.key, value=setting_in.value, category=setting_in.category)
        db.add(setting)
        
    db.commit()
    db.refresh(setting)

    log_audit_event(
        db,
        action="SETTINGS_UPDATE",
        username=current_user.username,
        user_id=current_user.id,
        ip_address=request.client.host if request.client else "unknown",
        details=f"Updated configuration key '{setting.key}' to '{setting.value}'"
    )
    return setting
