"""
Document Permission Hooks - Filter documents based on user permissions
"""
from typing import List, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from myplatform.db.permissions import (
    check_user_access,
    get_accessible_resources,
)
from myplatform.db.user_groups import get_user_groups
from esa.utils.logger import setup_logger

logger = setup_logger()


class DocumentHooks:
    """Hooks for document permission enforcement"""
    
    @staticmethod
    def filter_accessible_documents(
        db_session: Session,
        user_id: UUID,
        document_ids: List[int],
    ) -> List[int]:
        """
        Filter document IDs to only include those the user can access.
        """
        # Get user's groups
        user_groups = get_user_groups(db_session, user_id)
        group_ids = [g.id for g in user_groups]
        
        accessible = []
        for doc_id in document_ids:
            if check_user_access(db_session, "document", doc_id, user_id, group_ids):
                accessible.append(doc_id)
        
        if len(accessible) < len(document_ids):
            logger.debug(
                f"Filtered {len(document_ids) - len(accessible)} documents for user {user_id}"
            )
        
        return accessible
    
    @staticmethod
    def filter_accessible_document_sets(
        db_session: Session,
        user_id: UUID,
        document_set_ids: List[int],
    ) -> List[int]:
        """Filter document set IDs based on permissions"""
        user_groups = get_user_groups(db_session, user_id)
        group_ids = [g.id for g in user_groups]
        
        accessible = []
        for ds_id in document_set_ids:
            if check_user_access(db_session, "document_set", ds_id, user_id, group_ids):
                accessible.append(ds_id)
        
        return accessible
    
    @staticmethod
    def filter_accessible_personas(
        db_session: Session,
        user_id: UUID,
        persona_ids: List[int],
    ) -> List[int]:
        """Filter persona/assistant IDs based on permissions"""
        user_groups = get_user_groups(db_session, user_id)
        group_ids = [g.id for g in user_groups]
        
        accessible = []
        for p_id in persona_ids:
            if check_user_access(db_session, "persona", p_id, user_id, group_ids):
                accessible.append(p_id)
        
        return accessible
    
    @staticmethod
    def can_access_connector(
        db_session: Session,
        user_id: UUID,
        connector_id: int,
    ) -> bool:
        """Check if user can access a connector"""
        user_groups = get_user_groups(db_session, user_id)
        group_ids = [g.id for g in user_groups]
        
        return check_user_access(db_session, "connector", connector_id, user_id, group_ids)


# Convenience functions
def filter_documents_for_user(
    db_session: Session,
    user_id: UUID,
    document_ids: List[int],
) -> List[int]:
    """Filter documents user can access"""
    return DocumentHooks.filter_accessible_documents(db_session, user_id, document_ids)


def filter_personas_for_user(
    db_session: Session,
    user_id: UUID,
    persona_ids: List[int],
) -> List[int]:
    """Filter personas user can access"""
    return DocumentHooks.filter_accessible_personas(db_session, user_id, persona_ids)
