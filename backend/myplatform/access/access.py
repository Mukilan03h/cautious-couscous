"""
Group-aware access control for MyPlatform.
Extends base ACL with user group and external group support.
Ported from ee/esa/access/access.py
"""
from sqlalchemy.orm import Session

from myplatform.db.external_perm import fetch_external_groups_for_user
from myplatform.db.external_perm import fetch_public_external_group_ids
from myplatform.db.user_groups import fetch_user_groups_for_documents
from myplatform.db.user_groups import fetch_user_groups_for_user
from myplatform.external_permissions.sync_params import get_source_perm_sync_config
from esa.access.access import (
    _get_access_for_documents as get_access_for_documents_without_groups,
)
from esa.access.access import _get_acl_for_user as get_acl_for_user_without_groups
from esa.access.models import DocumentAccess
from esa.access.utils import prefix_external_group
from esa.access.utils import prefix_user_group
from esa.db.document import get_document_sources
from esa.db.document import get_documents_by_ids
from esa.db.models import User
from esa.utils.logger import setup_logger


logger = setup_logger()


def _get_access_for_document(
    document_id: str,
    db_session: Session,
) -> DocumentAccess:
    """
    Get access control for a single document.
    
    Args:
        document_id: The document ID
        db_session: Database session
        
    Returns:
        DocumentAccess object with full ACL information
    """
    id_to_access = _get_access_for_documents([document_id], db_session)
    if len(id_to_access) == 0:
        return DocumentAccess.build(
            user_emails=[],
            user_groups=[],
            external_user_emails=[],
            external_user_group_ids=[],
            is_public=False,
        )

    return next(iter(id_to_access.values()))


def _get_access_for_documents(
    document_ids: list[str],
    db_session: Session,
) -> dict[str, DocumentAccess]:
    """
    Get access control for multiple documents with group support.
    
    This extends the base ACL with:
    - User group memberships
    - External group memberships (from connectors)
    - Public external group handling
    
    Args:
        document_ids: List of document IDs
        db_session: Database session
        
    Returns:
        Dict mapping document IDs to DocumentAccess objects
    """
    # Get base access without groups
    non_ee_access_dict = get_access_for_documents_without_groups(
        document_ids=document_ids,
        db_session=db_session,
    )
    
    # Get user group info for documents
    user_group_info: dict[str, list[str]] = {}
    try:
        for document_id, group_names in fetch_user_groups_for_documents(
            db_session=db_session,
            document_ids=document_ids,
        ):
            user_group_info[document_id] = group_names
    except Exception as e:
        logger.warning(f"Could not fetch user groups for documents: {e}")
    
    # Get document objects
    documents = get_documents_by_ids(
        db_session=db_session,
        document_ids=document_ids,
    )
    doc_id_map = {doc.id: doc for doc in documents}

    # Get all sources in one batch
    doc_id_to_source_map = get_document_sources(
        db_session=db_session,
        document_ids=document_ids,
    )

    # Get all public external group IDs
    all_public_ext_u_group_ids = set(fetch_public_external_group_ids(db_session))

    access_map = {}
    for document_id, non_ee_access in non_ee_access_dict.items():
        document = doc_id_map.get(document_id)
        if not document:
            logger.warning(f"Document {document_id} not found in doc_id_map")
            continue
            
        source = doc_id_to_source_map.get(document_id)
        if source is None:
            logger.error(f"Document {document_id} has no source")
            continue

        # Check if this source uses censoring-only (post-query filtering)
        perm_sync_config = get_source_perm_sync_config(source)
        is_only_censored = (
            perm_sync_config
            and perm_sync_config.censoring_config is not None
            and perm_sync_config.doc_sync_config is None
        )

        # Get external user emails
        ext_u_emails = (
            set(document.external_user_emails)
            if hasattr(document, 'external_user_emails') and document.external_user_emails
            else set()
        )

        # Get external user groups
        ext_u_groups = (
            set(document.external_user_group_ids)
            if hasattr(document, 'external_user_group_ids') and document.external_user_group_ids
            else set()
        )

        # Determine if document should be treated as public
        # - Explicitly marked public in ESA
        # - Base access says public
        # - Using post-query censoring (public during search, filtered after)
        # - Any external group is in the public external groups list
        is_public_anywhere = (
            (hasattr(document, 'is_public') and document.is_public)
            or non_ee_access.is_public
            or is_only_censored
            or any(u_group in all_public_ext_u_group_ids for u_group in ext_u_groups)
        )

        # Build final access with all groups
        access_map[document_id] = DocumentAccess.build(
            user_emails=list(non_ee_access.user_emails),
            user_groups=user_group_info.get(document_id, []),
            is_public=is_public_anywhere,
            external_user_emails=list(ext_u_emails),
            external_user_group_ids=list(ext_u_groups),
        )
    return access_map


def _get_acl_for_user(user: User | None, db_session: Session) -> set[str]:
    """
    Get all ACL entries that a user has access to.
    
    This is used to filter search results - a user can access a document
    if at least one entry in the document's ACL matches one entry in this set.
    
    Args:
        user: The user (or None for public access)
        db_session: Database session
        
    Returns:
        Set of ACL entry strings the user has access to
        
    NOTE: This is imported in esa.access.access by `fetch_versioned_implementation`
    DO NOT REMOVE.
    """
    # Get user's internal groups
    db_user_groups = []
    if user:
        try:
            db_user_groups = fetch_user_groups_for_user(db_session, user.id)
        except Exception as e:
            logger.warning(f"Could not fetch user groups for user {user.id}: {e}")
    
    prefixed_user_groups = [
        prefix_user_group(db_user_group.name) for db_user_group in db_user_groups
    ]

    # Get user's external groups (from connectors)
    db_external_groups = []
    if user:
        try:
            db_external_groups = fetch_external_groups_for_user(db_session, user.id)
        except Exception as e:
            logger.warning(f"Could not fetch external groups for user {user.id}: {e}")
    
    prefixed_external_groups = [
        prefix_external_group(db_external_group.external_user_group_id)
        for db_external_group in db_external_groups
    ]

    # Combine all ACL entries
    user_acl = set(prefixed_user_groups + prefixed_external_groups)
    user_acl.update(get_acl_for_user_without_groups(user, db_session))

    return user_acl
