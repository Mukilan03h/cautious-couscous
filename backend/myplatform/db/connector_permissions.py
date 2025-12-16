"""
Custom External Permissions Sync - Sync permissions from external connectors
"""
from datetime import datetime
from typing import Dict, List, Optional
from uuid import UUID

from sqlalchemy import Column, DateTime, Integer, String, Boolean, ForeignKey, select
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Session

from esa.db.models import Base


class CustomConnectorPermissionSync(Base):
    """Track permission sync status for connectors"""
    __tablename__ = "custom_connector_permission_sync"
    
    id = Column(Integer, primary_key=True)
    
    # Connector info
    connector_id = Column(Integer, nullable=False, index=True)
    connector_type = Column(String, nullable=False)  # slack, google_drive, sharepoint, etc.
    
    # Sync status
    last_sync_at = Column(DateTime, nullable=True)
    sync_enabled = Column(Boolean, default=True)
    sync_status = Column(String, default='pending')  # pending, syncing, success, error
    last_error = Column(String, nullable=True)
    
    # Config
    sync_config = Column(JSONB, nullable=True)  # Connector-specific config
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class CustomExternalUserMapping(Base):
    """Map external user IDs to internal users"""
    __tablename__ = "custom_external_user_mapping"
    
    id = Column(Integer, primary_key=True)
    
    # Internal user
    user_id = Column(PGUUID(as_uuid=True), nullable=False, index=True)
    
    # External identity
    connector_type = Column(String, nullable=False, index=True)
    external_user_id = Column(String, nullable=False, index=True)
    external_email = Column(String, nullable=True)
    external_name = Column(String, nullable=True)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    last_verified_at = Column(DateTime, nullable=True)


class CustomExternalResourcePermission(Base):
    """Store permissions fetched from external sources"""
    __tablename__ = "custom_external_resource_permission"
    
    id = Column(Integer, primary_key=True)
    
    # What connector/resource
    connector_id = Column(Integer, nullable=False, index=True)
    connector_type = Column(String, nullable=False)
    resource_id = Column(String, nullable=False)  # External resource ID
    resource_type = Column(String, nullable=False)  # channel, folder, repo, etc.
    resource_name = Column(String, nullable=True)
    
    # Who has access (external IDs)
    allowed_external_user_ids = Column(JSONB, default=[])
    allowed_external_group_ids = Column(JSONB, default=[])
    
    # Is it public?
    is_public = Column(Boolean, default=False)
    
    # Sync metadata
    synced_at = Column(DateTime, default=datetime.utcnow)


# ============ Sync Functions ============

def enable_connector_sync(
    db_session: Session,
    connector_id: int,
    connector_type: str,
    sync_config: Dict = None,
) -> CustomConnectorPermissionSync:
    """Enable permission sync for a connector"""
    # Check if exists
    stmt = select(CustomConnectorPermissionSync).where(
        CustomConnectorPermissionSync.connector_id == connector_id
    )
    sync = db_session.scalar(stmt)
    
    if sync:
        sync.sync_enabled = True
        sync.sync_config = sync_config
    else:
        sync = CustomConnectorPermissionSync(
            connector_id=connector_id,
            connector_type=connector_type,
            sync_config=sync_config,
        )
        db_session.add(sync)
    
    db_session.commit()
    db_session.refresh(sync)
    return sync


def get_connector_sync_status(
    db_session: Session,
    connector_id: int,
) -> CustomConnectorPermissionSync | None:
    """Get sync status for a connector"""
    return db_session.scalar(
        select(CustomConnectorPermissionSync).where(
            CustomConnectorPermissionSync.connector_id == connector_id
        )
    )


def update_sync_status(
    db_session: Session,
    connector_id: int,
    status: str,
    error: str = None,
) -> None:
    """Update sync status"""
    sync = get_connector_sync_status(db_session, connector_id)
    if sync:
        sync.sync_status = status
        sync.last_error = error
        if status == 'success':
            sync.last_sync_at = datetime.utcnow()
        db_session.commit()


def map_external_user(
    db_session: Session,
    user_id: UUID,
    connector_type: str,
    external_user_id: str,
    external_email: str = None,
    external_name: str = None,
) -> CustomExternalUserMapping:
    """Map an external user to internal user"""
    # Check if exists
    stmt = select(CustomExternalUserMapping).where(
        CustomExternalUserMapping.user_id == user_id,
        CustomExternalUserMapping.connector_type == connector_type,
    )
    mapping = db_session.scalar(stmt)
    
    if mapping:
        mapping.external_user_id = external_user_id
        mapping.external_email = external_email
        mapping.external_name = external_name
        mapping.last_verified_at = datetime.utcnow()
    else:
        mapping = CustomExternalUserMapping(
            user_id=user_id,
            connector_type=connector_type,
            external_user_id=external_user_id,
            external_email=external_email,
            external_name=external_name,
        )
        db_session.add(mapping)
    
    db_session.commit()
    db_session.refresh(mapping)
    return mapping


def store_external_permissions(
    db_session: Session,
    connector_id: int,
    connector_type: str,
    resource_id: str,
    resource_type: str,
    resource_name: str = None,
    allowed_user_ids: List[str] = None,
    allowed_group_ids: List[str] = None,
    is_public: bool = False,
) -> CustomExternalResourcePermission:
    """Store permissions fetched from external source"""
    # Check if exists
    stmt = select(CustomExternalResourcePermission).where(
        CustomExternalResourcePermission.connector_id == connector_id,
        CustomExternalResourcePermission.resource_id == resource_id,
    )
    perm = db_session.scalar(stmt)
    
    if perm:
        perm.allowed_external_user_ids = allowed_user_ids or []
        perm.allowed_external_group_ids = allowed_group_ids or []
        perm.is_public = is_public
        perm.synced_at = datetime.utcnow()
    else:
        perm = CustomExternalResourcePermission(
            connector_id=connector_id,
            connector_type=connector_type,
            resource_id=resource_id,
            resource_type=resource_type,
            resource_name=resource_name,
            allowed_external_user_ids=allowed_user_ids or [],
            allowed_external_group_ids=allowed_group_ids or [],
            is_public=is_public,
        )
        db_session.add(perm)
    
    db_session.commit()
    db_session.refresh(perm)
    return perm


def check_external_access(
    db_session: Session,
    connector_id: int,
    resource_id: str,
    user_id: UUID,
) -> bool:
    """Check if user has access based on external permissions"""
    # Get resource permissions
    perm = db_session.scalar(
        select(CustomExternalResourcePermission).where(
            CustomExternalResourcePermission.connector_id == connector_id,
            CustomExternalResourcePermission.resource_id == resource_id,
        )
    )
    
    if not perm:
        return True  # No permissions stored = allow
    
    if perm.is_public:
        return True
    
    # Get user's external mapping for this connector
    mapping = db_session.scalar(
        select(CustomExternalUserMapping).where(
            CustomExternalUserMapping.user_id == user_id,
            CustomExternalUserMapping.connector_type == perm.connector_type,
        )
    )
    
    if not mapping:
        return False  # No mapping = deny
    
    if mapping.external_user_id in (perm.allowed_external_user_ids or []):
        return True
    
    return False
