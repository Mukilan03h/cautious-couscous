"""
User Hooks - Handle user events for enterprise features
"""
from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from myplatform.db.user_groups import (
    get_user_groups,
    add_user_to_group,
    CustomUserGroup,
)
from myplatform.db.tenants import (
    get_user_tenants,
    add_user_to_tenant,
    check_user_in_tenant,
)
from myplatform.db.analytics import record_user_activity
from esa.utils.logger import setup_logger

logger = setup_logger()


class UserHooks:
    """Hooks for user lifecycle events"""
    
    @staticmethod
    def on_user_login(
        db_session: Session,
        user_id: UUID,
        email: str = None,
    ) -> dict:
        """
        Called when user logs in.
        Returns context with groups and tenants.
        """
        # Get user's groups
        groups = get_user_groups(db_session, user_id)
        group_ids = [g.id for g in groups]
        group_names = [g.name for g in groups]
        
        # Get user's tenants
        tenant_ids = get_user_tenants(db_session, user_id)
        
        # Record login activity
        try:
            record_user_activity(
                db_session=db_session,
                user_id=user_id,
                chat_count=0,  # Just a login
            )
        except Exception as e:
            logger.warning(f"Failed to record login activity: {e}")
        
        logger.info(f"User {user_id} logged in. Groups: {group_names}, Tenants: {tenant_ids}")
        
        return {
            "user_id": str(user_id),
            "groups": group_ids,
            "group_names": group_names,
            "tenants": tenant_ids,
            "default_tenant": tenant_ids[0] if tenant_ids else None,
        }
    
    @staticmethod
    def on_user_created(
        db_session: Session,
        user_id: UUID,
        email: str,
        default_group_id: int = None,
        default_tenant_id: int = None,
    ) -> None:
        """
        Called when a new user is created.
        Optionally assigns to default group/tenant.
        """
        if default_group_id:
            try:
                add_user_to_group(db_session, default_group_id, user_id)
                logger.info(f"Added new user {user_id} to default group {default_group_id}")
            except Exception as e:
                logger.warning(f"Failed to add user to default group: {e}")
        
        if default_tenant_id:
            try:
                add_user_to_tenant(db_session, default_tenant_id, user_id)
                logger.info(f"Added new user {user_id} to default tenant {default_tenant_id}")
            except Exception as e:
                logger.warning(f"Failed to add user to default tenant: {e}")
    
    @staticmethod
    def get_user_context(
        db_session: Session,
        user_id: UUID,
    ) -> dict:
        """Get user's enterprise context (groups, tenants, permissions)"""
        groups = get_user_groups(db_session, user_id)
        tenant_ids = get_user_tenants(db_session, user_id)
        
        # Aggregate permissions from all groups
        all_document_set_ids = set()
        all_assistant_ids = set()
        all_connector_ids = set()
        
        for group in groups:
            if group.document_set_ids:
                all_document_set_ids.update(group.document_set_ids)
            if group.assistant_ids:
                all_assistant_ids.update(group.assistant_ids)
            if group.connector_ids:
                all_connector_ids.update(group.connector_ids)
        
        return {
            "user_id": str(user_id),
            "group_ids": [g.id for g in groups],
            "tenant_ids": tenant_ids,
            "accessible_document_sets": list(all_document_set_ids),
            "accessible_assistants": list(all_assistant_ids),
            "accessible_connectors": list(all_connector_ids),
        }


# Convenience functions
def get_user_enterprise_context(db_session: Session, user_id: UUID) -> dict:
    """Get full enterprise context for a user"""
    return UserHooks.get_user_context(db_session, user_id)


def handle_user_login(db_session: Session, user_id: UUID, email: str = None) -> dict:
    """Handle user login event"""
    return UserHooks.on_user_login(db_session, user_id, email)
