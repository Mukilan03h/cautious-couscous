"""
Custom Permissions API - ACLs for documents, personas, connectors
"""
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from esa.auth.users import current_admin_user, current_user
from esa.db.engine import get_session
from esa.db.models import User
from myplatform.db.permissions import (
    set_resource_acl,
    get_resource_acl,
    check_user_access,
    get_accessible_resources,
    add_user_to_acl,
    add_group_to_acl,
    remove_user_from_acl,
    remove_group_from_acl,
    CustomDocumentACL,
)


router = APIRouter(prefix="/api/admin/permissions", tags=["permissions"])
user_router = APIRouter(prefix="/api/access", tags=["access"])


# ============ Pydantic Models ============

class ACLSet(BaseModel):
    resource_type: str  # document, document_set, persona, connector
    resource_id: int
    user_ids: List[str] = []  # UUID strings
    group_ids: List[int] = []
    is_public: bool = False


class ACLResponse(BaseModel):
    id: int
    resource_type: str
    resource_id: int
    user_ids: List[str]
    group_ids: List[int]
    is_public: bool


class AccessCheck(BaseModel):
    resource_type: str
    resource_id: int


class AccessResult(BaseModel):
    has_access: bool
    resource_type: str
    resource_id: int


# ============ Admin Endpoints ============

@router.get("/{resource_type}/{resource_id}", response_model=Optional[ACLResponse])
def get_acl(
    resource_type: str,
    resource_id: int,
    db: Session = Depends(get_session),
    _user: User = Depends(current_admin_user),
):
    """Get ACL for a resource"""
    acl = get_resource_acl(db, resource_type, resource_id)
    if not acl:
        return None
    return ACLResponse(
        id=acl.id,
        resource_type=acl.resource_type,
        resource_id=acl.resource_id,
        user_ids=[str(u) for u in (acl.user_ids or [])],
        group_ids=acl.group_ids or [],
        is_public=acl.is_public,
    )


@router.put("/", response_model=ACLResponse)
def set_acl(
    acl_data: ACLSet,
    db: Session = Depends(get_session),
    user: User = Depends(current_admin_user),
):
    """Set ACL for a resource"""
    user_uuids = [UUID(u) for u in acl_data.user_ids]
    
    acl = set_resource_acl(
        db,
        resource_type=acl_data.resource_type,
        resource_id=acl_data.resource_id,
        user_ids=user_uuids,
        group_ids=acl_data.group_ids,
        is_public=acl_data.is_public,
        created_by_id=user.id,
    )
    return ACLResponse(
        id=acl.id,
        resource_type=acl.resource_type,
        resource_id=acl.resource_id,
        user_ids=[str(u) for u in (acl.user_ids or [])],
        group_ids=acl.group_ids or [],
        is_public=acl.is_public,
    )


@router.post("/{resource_type}/{resource_id}/users/{user_id}")
def add_user(
    resource_type: str,
    resource_id: int,
    user_id: str,
    db: Session = Depends(get_session),
    _admin: User = Depends(current_admin_user),
):
    """Add a user to resource ACL"""
    acl = add_user_to_acl(db, resource_type, resource_id, UUID(user_id))
    return {"added": True, "user_id": user_id}


@router.delete("/{resource_type}/{resource_id}/users/{user_id}")
def remove_user(
    resource_type: str,
    resource_id: int,
    user_id: str,
    db: Session = Depends(get_session),
    _admin: User = Depends(current_admin_user),
):
    """Remove a user from resource ACL"""
    removed = remove_user_from_acl(db, resource_type, resource_id, UUID(user_id))
    return {"removed": removed, "user_id": user_id}


@router.post("/{resource_type}/{resource_id}/groups/{group_id}")
def add_group(
    resource_type: str,
    resource_id: int,
    group_id: int,
    db: Session = Depends(get_session),
    _admin: User = Depends(current_admin_user),
):
    """Add a group to resource ACL"""
    acl = add_group_to_acl(db, resource_type, resource_id, group_id)
    return {"added": True, "group_id": group_id}


@router.delete("/{resource_type}/{resource_id}/groups/{group_id}")
def remove_group(
    resource_type: str,
    resource_id: int,
    group_id: int,
    db: Session = Depends(get_session),
    _admin: User = Depends(current_admin_user),
):
    """Remove a group from resource ACL"""
    removed = remove_group_from_acl(db, resource_type, resource_id, group_id)
    return {"removed": removed, "group_id": group_id}


# ============ User Endpoints ============

@user_router.post("/check", response_model=AccessResult)
def check_access(
    check: AccessCheck,
    db: Session = Depends(get_session),
    user: User = Depends(current_user),
):
    """Check if current user has access to a resource"""
    # Get user's groups
    group_ids = []
    if hasattr(user, 'custom_groups'):
        group_ids = [g.id for g in user.custom_groups]
    
    has_access = check_user_access(
        db,
        check.resource_type,
        check.resource_id,
        user.id,
        group_ids,
    )
    return AccessResult(
        has_access=has_access,
        resource_type=check.resource_type,
        resource_id=check.resource_id,
    )


@user_router.get("/accessible/{resource_type}")
def list_accessible(
    resource_type: str,
    db: Session = Depends(get_session),
    user: User = Depends(current_user),
):
    """List all resources of a type that user can access"""
    group_ids = []
    if hasattr(user, 'custom_groups'):
        group_ids = [g.id for g in user.custom_groups]
    
    resource_ids = get_accessible_resources(db, resource_type, user.id, group_ids)
    return {
        "resource_type": resource_type,
        "accessible_ids": resource_ids,
    }
