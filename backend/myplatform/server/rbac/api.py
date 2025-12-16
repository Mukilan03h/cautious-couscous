"""
Custom RBAC (Role-Based Access Control) API

Provides endpoints for managing user groups and permissions.
"""
import json
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from esa.auth.users import current_admin_user, current_user
from esa.db.engine import get_session
from esa.db.models import User
from myplatform.db.user_groups import CustomUserGroup, CustomUserGroupAuditLog


router = APIRouter(prefix="/api/admin/groups", tags=["rbac"])


# ============ Pydantic Models ============

class GroupCreate(BaseModel):
    name: str
    description: Optional[str] = None
    document_set_ids: List[int] = []
    assistant_ids: List[int] = []
    connector_ids: List[int] = []


class GroupUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    document_set_ids: Optional[List[int]] = None
    assistant_ids: Optional[List[int]] = None
    connector_ids: Optional[List[int]] = None
    is_active: Optional[bool] = None


class GroupResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    document_set_ids: List[int]
    assistant_ids: List[int]
    connector_ids: List[int]
    is_active: bool
    user_count: int
    created_at: datetime
    
    class Config:
        from_attributes = True


class UserGroupAssignment(BaseModel):
    user_ids: List[str]  # UUID strings


# ============ Group CRUD Endpoints ============

@router.get("/", response_model=List[GroupResponse])
def list_groups(
    include_inactive: bool = False,
    db: Session = Depends(get_session),
    _user: User = Depends(current_admin_user)
):
    """List all user groups"""
    query = select(CustomUserGroup)
    if not include_inactive:
        query = query.where(CustomUserGroup.is_active == True)
    
    groups = db.execute(query).scalars().all()
    
    return [
        GroupResponse(
            id=g.id,
            name=g.name,
            description=g.description,
            document_set_ids=g.document_set_ids or [],
            assistant_ids=g.assistant_ids or [],
            connector_ids=g.connector_ids or [],
            is_active=g.is_active,
            user_count=len(g.users),
            created_at=g.created_at
        )
        for g in groups
    ]


@router.post("/", response_model=GroupResponse)
def create_group(
    group: GroupCreate,
    db: Session = Depends(get_session),
    user: User = Depends(current_admin_user)
):
    """Create a new user group"""
    # Check if group name already exists
    existing = db.execute(
        select(CustomUserGroup).where(CustomUserGroup.name == group.name)
    ).scalar_one_or_none()
    
    if existing:
        raise HTTPException(status_code=400, detail="Group name already exists")
    
    new_group = CustomUserGroup(
        name=group.name,
        description=group.description,
        document_set_ids=group.document_set_ids,
        assistant_ids=group.assistant_ids,
        connector_ids=group.connector_ids,
        created_by_id=user.id
    )
    db.add(new_group)
    
    # Audit log
    audit = CustomUserGroupAuditLog(
        group_id=new_group.id,
        action="created",
        actor_id=user.id,
        details=json.dumps({"name": group.name})
    )
    db.add(audit)
    db.commit()
    db.refresh(new_group)
    
    return GroupResponse(
        id=new_group.id,
        name=new_group.name,
        description=new_group.description,
        document_set_ids=new_group.document_set_ids or [],
        assistant_ids=new_group.assistant_ids or [],
        connector_ids=new_group.connector_ids or [],
        is_active=new_group.is_active,
        user_count=0,
        created_at=new_group.created_at
    )


@router.get("/{group_id}", response_model=GroupResponse)
def get_group(
    group_id: int,
    db: Session = Depends(get_session),
    _user: User = Depends(current_admin_user)
):
    """Get a specific group by ID"""
    group = db.get(CustomUserGroup, group_id)
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    
    return GroupResponse(
        id=group.id,
        name=group.name,
        description=group.description,
        document_set_ids=group.document_set_ids or [],
        assistant_ids=group.assistant_ids or [],
        connector_ids=group.connector_ids or [],
        is_active=group.is_active,
        user_count=len(group.users),
        created_at=group.created_at
    )


@router.patch("/{group_id}", response_model=GroupResponse)
def update_group(
    group_id: int,
    update: GroupUpdate,
    db: Session = Depends(get_session),
    user: User = Depends(current_admin_user)
):
    """Update a group's settings"""
    group = db.get(CustomUserGroup, group_id)
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    
    changes = {}
    if update.name is not None:
        changes["name"] = {"old": group.name, "new": update.name}
        group.name = update.name
    if update.description is not None:
        group.description = update.description
    if update.document_set_ids is not None:
        group.document_set_ids = update.document_set_ids
    if update.assistant_ids is not None:
        group.assistant_ids = update.assistant_ids
    if update.connector_ids is not None:
        group.connector_ids = update.connector_ids
    if update.is_active is not None:
        group.is_active = update.is_active
    
    # Audit log
    audit = CustomUserGroupAuditLog(
        group_id=group.id,
        action="updated",
        actor_id=user.id,
        details=json.dumps(changes)
    )
    db.add(audit)
    db.commit()
    db.refresh(group)
    
    return GroupResponse(
        id=group.id,
        name=group.name,
        description=group.description,
        document_set_ids=group.document_set_ids or [],
        assistant_ids=group.assistant_ids or [],
        connector_ids=group.connector_ids or [],
        is_active=group.is_active,
        user_count=len(group.users),
        created_at=group.created_at
    )


@router.delete("/{group_id}")
def delete_group(
    group_id: int,
    db: Session = Depends(get_session),
    user: User = Depends(current_admin_user)
):
    """Soft delete a group (mark as inactive)"""
    group = db.get(CustomUserGroup, group_id)
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    
    group.is_active = False
    
    audit = CustomUserGroupAuditLog(
        group_id=group.id,
        action="deleted",
        actor_id=user.id
    )
    db.add(audit)
    db.commit()
    
    return {"status": "deleted", "group_id": group_id}


# ============ User Assignment Endpoints ============

@router.post("/{group_id}/users")
def add_users_to_group(
    group_id: int,
    assignment: UserGroupAssignment,
    db: Session = Depends(get_session),
    actor: User = Depends(current_admin_user)
):
    """Add users to a group"""
    group = db.get(CustomUserGroup, group_id)
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    
    added = []
    for user_id_str in assignment.user_ids:
        user = db.execute(
            select(User).where(User.id == user_id_str)
        ).scalar_one_or_none()
        
        if user and user not in group.users:
            group.users.append(user)
            added.append(user_id_str)
    
    if added:
        audit = CustomUserGroupAuditLog(
            group_id=group.id,
            action="users_added",
            actor_id=actor.id,
            details=json.dumps({"user_ids": added})
        )
        db.add(audit)
    
    db.commit()
    return {"added_users": added, "group_id": group_id}


@router.delete("/{group_id}/users/{user_id}")
def remove_user_from_group(
    group_id: int,
    user_id: str,
    db: Session = Depends(get_session),
    actor: User = Depends(current_admin_user)
):
    """Remove a user from a group"""
    group = db.get(CustomUserGroup, group_id)
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    
    user = db.execute(
        select(User).where(User.id == user_id)
    ).scalar_one_or_none()
    
    if user and user in group.users:
        group.users.remove(user)
        
        audit = CustomUserGroupAuditLog(
            group_id=group.id,
            action="user_removed",
            actor_id=actor.id,
            details=json.dumps({"user_id": user_id})
        )
        db.add(audit)
        db.commit()
        return {"removed": True, "user_id": user_id}
    
    return {"removed": False, "user_id": user_id}


@router.get("/{group_id}/users")
def get_group_users(
    group_id: int,
    db: Session = Depends(get_session),
    _user: User = Depends(current_admin_user)
):
    """Get all users in a group"""
    group = db.get(CustomUserGroup, group_id)
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    
    return {
        "group_id": group_id,
        "group_name": group.name,
        "users": [
            {"id": str(u.id), "email": u.email}
            for u in group.users
        ]
    }


# ============ Permission Check Endpoints ============

@router.get("/my-permissions")
def get_my_permissions(
    db: Session = Depends(get_session),
    user: User = Depends(current_user)
):
    """Get current user's permissions based on their groups"""
    # Get all groups user belongs to
    groups = db.execute(
        select(CustomUserGroup)
        .where(CustomUserGroup.users.contains(user))
        .where(CustomUserGroup.is_active == True)
    ).scalars().all()
    
    # Aggregate permissions
    document_set_ids = set()
    assistant_ids = set()
    connector_ids = set()
    
    for group in groups:
        document_set_ids.update(group.document_set_ids or [])
        assistant_ids.update(group.assistant_ids or [])
        connector_ids.update(group.connector_ids or [])
    
    return {
        "user_id": str(user.id),
        "groups": [{"id": g.id, "name": g.name} for g in groups],
        "accessible_document_sets": list(document_set_ids),
        "accessible_assistants": list(assistant_ids),
        "accessible_connectors": list(connector_ids)
    }
