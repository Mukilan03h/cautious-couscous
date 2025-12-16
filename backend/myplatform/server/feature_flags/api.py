"""
Custom Feature Flags API
"""
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from esa.auth.users import current_admin_user, current_user
from esa.db.engine import get_session
from esa.db.models import User
from myplatform.db.feature_flags import (
    create_feature_flag,
    get_feature_flag,
    get_all_feature_flags,
    update_feature_flag,
    is_feature_enabled,
    delete_feature_flag,
)


router = APIRouter(prefix="/api/admin/feature-flags", tags=["feature-flags"])
user_router = APIRouter(prefix="/api/features", tags=["features"])


class FlagCreate(BaseModel):
    name: str
    description: Optional[str] = None
    enabled_by_default: bool = False


class FlagUpdate(BaseModel):
    enabled_for_all: Optional[bool] = None
    enabled_tenant_ids: Optional[List[int]] = None
    enabled_user_ids: Optional[List[str]] = None
    enabled_group_ids: Optional[List[int]] = None
    disabled_tenant_ids: Optional[List[int]] = None
    disabled_user_ids: Optional[List[str]] = None


class FlagResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    enabled_by_default: bool
    enabled_for_all: bool
    enabled_tenant_ids: List[int]
    enabled_user_ids: List[str]
    enabled_group_ids: List[int]


@router.get("/", response_model=List[FlagResponse])
def list_flags(
    db: Session = Depends(get_session),
    _user: User = Depends(current_admin_user),
):
    """List all feature flags"""
    flags = get_all_feature_flags(db)
    return [
        FlagResponse(
            id=f.id,
            name=f.name,
            description=f.description,
            enabled_by_default=f.enabled_by_default,
            enabled_for_all=f.enabled_for_all,
            enabled_tenant_ids=f.enabled_tenant_ids or [],
            enabled_user_ids=[str(u) for u in (f.enabled_user_ids or [])],
            enabled_group_ids=f.enabled_group_ids or [],
        )
        for f in flags
    ]


@router.post("/", response_model=FlagResponse)
def create_flag(
    flag: FlagCreate,
    db: Session = Depends(get_session),
    _user: User = Depends(current_admin_user),
):
    """Create a new feature flag"""
    f = create_feature_flag(db, flag.name, flag.description, flag.enabled_by_default)
    return FlagResponse(
        id=f.id,
        name=f.name,
        description=f.description,
        enabled_by_default=f.enabled_by_default,
        enabled_for_all=f.enabled_for_all,
        enabled_tenant_ids=f.enabled_tenant_ids or [],
        enabled_user_ids=[str(u) for u in (f.enabled_user_ids or [])],
        enabled_group_ids=f.enabled_group_ids or [],
    )


@router.patch("/{name}", response_model=FlagResponse)
def update_flag(
    name: str,
    update: FlagUpdate,
    db: Session = Depends(get_session),
    _user: User = Depends(current_admin_user),
):
    """Update a feature flag"""
    user_uuids = [UUID(u) for u in update.enabled_user_ids] if update.enabled_user_ids else None
    disabled_uuids = [UUID(u) for u in update.disabled_user_ids] if update.disabled_user_ids else None
    
    f = update_feature_flag(
        db,
        name=name,
        enabled_for_all=update.enabled_for_all,
        enabled_tenant_ids=update.enabled_tenant_ids,
        enabled_user_ids=user_uuids,
        enabled_group_ids=update.enabled_group_ids,
        disabled_tenant_ids=update.disabled_tenant_ids,
        disabled_user_ids=disabled_uuids,
    )
    if not f:
        raise HTTPException(status_code=404, detail="Flag not found")
    
    return FlagResponse(
        id=f.id,
        name=f.name,
        description=f.description,
        enabled_by_default=f.enabled_by_default,
        enabled_for_all=f.enabled_for_all,
        enabled_tenant_ids=f.enabled_tenant_ids or [],
        enabled_user_ids=[str(u) for u in (f.enabled_user_ids or [])],
        enabled_group_ids=f.enabled_group_ids or [],
    )


@router.delete("/{name}")
def delete_flag(
    name: str,
    db: Session = Depends(get_session),
    _user: User = Depends(current_admin_user),
):
    """Delete a feature flag"""
    if delete_feature_flag(db, name):
        return {"deleted": True, "name": name}
    raise HTTPException(status_code=404, detail="Flag not found")


# ============ User Endpoints ============

@user_router.get("/check/{flag_name}")
def check_feature(
    flag_name: str,
    tenant_id: Optional[int] = None,
    db: Session = Depends(get_session),
    user: User = Depends(current_user),
):
    """Check if a feature is enabled for current user"""
    # Get user's groups
    group_ids = []
    if hasattr(user, 'custom_groups'):
        group_ids = [g.id for g in user.custom_groups]
    
    enabled = is_feature_enabled(
        db,
        flag_name=flag_name,
        user_id=user.id,
        tenant_id=tenant_id,
        group_ids=group_ids,
    )
    return {"feature": flag_name, "enabled": enabled}


@user_router.get("/my-features")
def get_my_features(
    tenant_id: Optional[int] = None,
    db: Session = Depends(get_session),
    user: User = Depends(current_user),
):
    """Get all enabled features for current user"""
    group_ids = []
    if hasattr(user, 'custom_groups'):
        group_ids = [g.id for g in user.custom_groups]
    
    all_flags = get_all_feature_flags(db)
    enabled_features = []
    
    for flag in all_flags:
        if is_feature_enabled(db, flag.name, user.id, tenant_id, group_ids):
            enabled_features.append(flag.name)
    
    return {"enabled_features": enabled_features}
