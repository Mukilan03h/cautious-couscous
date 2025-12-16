"""
Custom Document/Resource Permissions - ACLs for documents, personas, and connectors
"""
from datetime import datetime
from typing import List, Optional, Sequence
from uuid import UUID

from sqlalchemy import Column, DateTime, Integer, String, Boolean, Table, ForeignKey, select
from sqlalchemy.dialects.postgresql import UUID as PGUUID, ARRAY
from sqlalchemy.orm import Session

from esa.db.models import Base


class CustomDocumentACL(Base):
    """Access control for individual documents or document sets"""
    __tablename__ = "custom_document_acl"
    
    id = Column(Integer, primary_key=True)
    
    # What this ACL applies to
    resource_type = Column(String, nullable=False, index=True)  # 'document', 'document_set', 'persona', 'connector'
    resource_id = Column(Integer, nullable=False, index=True)
    
    # Who has access
    user_ids = Column(ARRAY(PGUUID(as_uuid=True)), default=[], nullable=False)
    group_ids = Column(ARRAY(Integer), default=[], nullable=False)
    
    # Access level
    is_public = Column(Boolean, default=False)  # If true, everyone can access
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by_id = Column(PGUUID(as_uuid=True), nullable=True)


# ============ ACL Functions ============

def set_resource_acl(
    db_session: Session,
    resource_type: str,
    resource_id: int,
    user_ids: List[UUID] = None,
    group_ids: List[int] = None,
    is_public: bool = False,
    created_by_id: UUID = None,
) -> CustomDocumentACL:
    """Set or update ACL for a resource"""
    # Find existing ACL
    stmt = select(CustomDocumentACL).where(
        CustomDocumentACL.resource_type == resource_type,
        CustomDocumentACL.resource_id == resource_id,
    )
    acl = db_session.scalar(stmt)
    
    if acl:
        # Update existing
        acl.user_ids = user_ids or []
        acl.group_ids = group_ids or []
        acl.is_public = is_public
    else:
        # Create new
        acl = CustomDocumentACL(
            resource_type=resource_type,
            resource_id=resource_id,
            user_ids=user_ids or [],
            group_ids=group_ids or [],
            is_public=is_public,
            created_by_id=created_by_id,
        )
        db_session.add(acl)
    
    db_session.commit()
    db_session.refresh(acl)
    return acl


def get_resource_acl(
    db_session: Session,
    resource_type: str,
    resource_id: int,
) -> CustomDocumentACL | None:
    """Get ACL for a specific resource"""
    return db_session.scalar(
        select(CustomDocumentACL).where(
            CustomDocumentACL.resource_type == resource_type,
            CustomDocumentACL.resource_id == resource_id,
        )
    )


def check_user_access(
    db_session: Session,
    resource_type: str,
    resource_id: int,
    user_id: UUID,
    user_group_ids: List[int] = None,
) -> bool:
    """Check if a user has access to a resource"""
    acl = get_resource_acl(db_session, resource_type, resource_id)
    
    if not acl:
        return True  # No ACL means public access
    
    if acl.is_public:
        return True
    
    if user_id in (acl.user_ids or []):
        return True
    
    if user_group_ids:
        if set(user_group_ids) & set(acl.group_ids or []):
            return True
    
    return False


def get_accessible_resources(
    db_session: Session,
    resource_type: str,
    user_id: UUID,
    user_group_ids: List[int] = None,
) -> List[int]:
    """Get all resource IDs of a type that user can access"""
    # Get all ACLs for this resource type
    stmt = select(CustomDocumentACL).where(
        CustomDocumentACL.resource_type == resource_type
    )
    acls = db_session.scalars(stmt).all()
    
    accessible_ids = []
    for acl in acls:
        if acl.is_public:
            accessible_ids.append(acl.resource_id)
        elif user_id in (acl.user_ids or []):
            accessible_ids.append(acl.resource_id)
        elif user_group_ids and set(user_group_ids) & set(acl.group_ids or []):
            accessible_ids.append(acl.resource_id)
    
    return accessible_ids


def add_user_to_acl(
    db_session: Session,
    resource_type: str,
    resource_id: int,
    user_id: UUID,
) -> CustomDocumentACL:
    """Add a user to resource ACL"""
    acl = get_resource_acl(db_session, resource_type, resource_id)
    
    if not acl:
        acl = CustomDocumentACL(
            resource_type=resource_type,
            resource_id=resource_id,
            user_ids=[user_id],
            group_ids=[],
        )
        db_session.add(acl)
    else:
        if user_id not in (acl.user_ids or []):
            acl.user_ids = (acl.user_ids or []) + [user_id]
    
    db_session.commit()
    db_session.refresh(acl)
    return acl


def add_group_to_acl(
    db_session: Session,
    resource_type: str,
    resource_id: int,
    group_id: int,
) -> CustomDocumentACL:
    """Add a group to resource ACL"""
    acl = get_resource_acl(db_session, resource_type, resource_id)
    
    if not acl:
        acl = CustomDocumentACL(
            resource_type=resource_type,
            resource_id=resource_id,
            user_ids=[],
            group_ids=[group_id],
        )
        db_session.add(acl)
    else:
        if group_id not in (acl.group_ids or []):
            acl.group_ids = (acl.group_ids or []) + [group_id]
    
    db_session.commit()
    db_session.refresh(acl)
    return acl


def remove_user_from_acl(
    db_session: Session,
    resource_type: str,
    resource_id: int,
    user_id: UUID,
) -> bool:
    """Remove a user from resource ACL"""
    acl = get_resource_acl(db_session, resource_type, resource_id)
    
    if acl and user_id in (acl.user_ids or []):
        acl.user_ids = [u for u in acl.user_ids if u != user_id]
        db_session.commit()
        return True
    return False


def remove_group_from_acl(
    db_session: Session,
    resource_type: str,
    resource_id: int,
    group_id: int,
) -> bool:
    """Remove a group from resource ACL"""
    acl = get_resource_acl(db_session, resource_type, resource_id)
    
    if acl and group_id in (acl.group_ids or []):
        acl.group_ids = [g for g in acl.group_ids if g != group_id]
        db_session.commit()
        return True
    return False
