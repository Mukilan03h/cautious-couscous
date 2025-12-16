"""
Custom Feature Flags - Toggle features per tenant/user
"""
from datetime import datetime
from typing import Optional, List
from uuid import UUID

from sqlalchemy import Column, DateTime, Integer, String, Boolean, select
from sqlalchemy.dialects.postgresql import UUID as PGUUID, JSONB, ARRAY
from sqlalchemy.orm import Session

from esa.db.models import Base


class CustomFeatureFlag(Base):
    """Feature flags for toggling features"""
    __tablename__ = "custom_feature_flag"
    
    id = Column(Integer, primary_key=True)
    
    # Flag info
    name = Column(String, nullable=False, unique=True, index=True)
    description = Column(String, nullable=True)
    
    # Default state
    enabled_by_default = Column(Boolean, default=False)
    
    # Who gets this feature
    enabled_for_all = Column(Boolean, default=False)
    enabled_tenant_ids = Column(ARRAY(Integer), default=[])
    enabled_user_ids = Column(ARRAY(PGUUID(as_uuid=True)), default=[])
    enabled_group_ids = Column(ARRAY(Integer), default=[])
    
    # Override: explicitly disabled for these
    disabled_tenant_ids = Column(ARRAY(Integer), default=[])
    disabled_user_ids = Column(ARRAY(PGUUID(as_uuid=True)), default=[])
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ============ Feature Flag Functions ============

def create_feature_flag(
    db_session: Session,
    name: str,
    description: str = None,
    enabled_by_default: bool = False,
) -> CustomFeatureFlag:
    """Create a new feature flag"""
    flag = CustomFeatureFlag(
        name=name,
        description=description,
        enabled_by_default=enabled_by_default,
    )
    db_session.add(flag)
    db_session.commit()
    db_session.refresh(flag)
    return flag


def get_feature_flag(db_session: Session, name: str) -> CustomFeatureFlag | None:
    """Get a feature flag by name"""
    return db_session.scalar(
        select(CustomFeatureFlag).where(CustomFeatureFlag.name == name)
    )


def get_all_feature_flags(db_session: Session) -> List[CustomFeatureFlag]:
    """Get all feature flags"""
    return list(db_session.scalars(select(CustomFeatureFlag)).all())


def update_feature_flag(
    db_session: Session,
    name: str,
    enabled_for_all: bool = None,
    enabled_tenant_ids: List[int] = None,
    enabled_user_ids: List[UUID] = None,
    enabled_group_ids: List[int] = None,
    disabled_tenant_ids: List[int] = None,
    disabled_user_ids: List[UUID] = None,
) -> CustomFeatureFlag | None:
    """Update a feature flag"""
    flag = get_feature_flag(db_session, name)
    if not flag:
        return None
    
    if enabled_for_all is not None:
        flag.enabled_for_all = enabled_for_all
    if enabled_tenant_ids is not None:
        flag.enabled_tenant_ids = enabled_tenant_ids
    if enabled_user_ids is not None:
        flag.enabled_user_ids = enabled_user_ids
    if enabled_group_ids is not None:
        flag.enabled_group_ids = enabled_group_ids
    if disabled_tenant_ids is not None:
        flag.disabled_tenant_ids = disabled_tenant_ids
    if disabled_user_ids is not None:
        flag.disabled_user_ids = disabled_user_ids
    
    db_session.commit()
    db_session.refresh(flag)
    return flag


def is_feature_enabled(
    db_session: Session,
    flag_name: str,
    user_id: UUID = None,
    tenant_id: int = None,
    group_ids: List[int] = None,
) -> bool:
    """Check if a feature is enabled for user/tenant"""
    flag = get_feature_flag(db_session, flag_name)
    
    if not flag:
        return False  # Unknown flag = disabled
    
    # Check explicit disables first
    if user_id and user_id in (flag.disabled_user_ids or []):
        return False
    if tenant_id and tenant_id in (flag.disabled_tenant_ids or []):
        return False
    
    # Check if enabled for all
    if flag.enabled_for_all:
        return True
    
    # Check specific enables
    if user_id and user_id in (flag.enabled_user_ids or []):
        return True
    if tenant_id and tenant_id in (flag.enabled_tenant_ids or []):
        return True
    if group_ids:
        if set(group_ids) & set(flag.enabled_group_ids or []):
            return True
    
    # Fall back to default
    return flag.enabled_by_default


def delete_feature_flag(db_session: Session, name: str) -> bool:
    """Delete a feature flag"""
    flag = get_feature_flag(db_session, name)
    if flag:
        db_session.delete(flag)
        db_session.commit()
        return True
    return False
