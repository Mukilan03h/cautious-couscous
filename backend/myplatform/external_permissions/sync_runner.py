"""
Permission sync runner for MyPlatform.
Orchestrates the execution of permission sync operations.
"""
from sqlalchemy.orm import Session

from esa.utils.logger import setup_logger

logger = setup_logger()


def run_permission_sync(
    db_session: Session,
    connector_id: int,
    credential_id: int,
) -> None:
    """
    Run permission sync for a specific connector-credential pair.
    
    Args:
        db_session: Database session
        connector_id: The connector ID
        credential_id: The credential ID
    """
    from myplatform.external_permissions.sync_params import get_source_perm_sync_config
    from myplatform.external_permissions.sync_params import source_requires_doc_sync
    from esa.db.connector_credential_pair import get_connector_credential_pair_from_id
    
    # Get the CC pair
    cc_pair = get_connector_credential_pair_from_id(
        db_session=db_session,
        cc_pair_id=connector_id,  # Assuming connector_id is cc_pair_id
    )
    
    if not cc_pair:
        logger.error(f"CC pair not found: connector_id={connector_id}")
        return
    
    source = cc_pair.connector.source
    
    if not source_requires_doc_sync(source):
        logger.info(f"Source {source} does not require doc sync")
        return
    
    sync_config = get_source_perm_sync_config(source)
    if not sync_config or not sync_config.doc_sync_config:
        logger.info(f"No sync config found for source {source}")
        return
    
    logger.info(f"Running permission sync for {source} cc_pair={cc_pair.id}")
    
    # Execute the sync function
    doc_sync_func = sync_config.doc_sync_config.doc_sync_func
    
    # Create fetch functions
    def fetch_all_docs(sort_order=None):
        from esa.db.document import get_documents_for_cc_pair
        return get_documents_for_cc_pair(
            db_session=db_session,
            cc_pair_id=cc_pair.id,
        )
    
    def fetch_all_doc_ids():
        from esa.db.document import get_document_ids_for_cc_pair
        return get_document_ids_for_cc_pair(
            db_session=db_session,
            cc_pair_id=cc_pair.id,
        )
    
    # Run the sync
    for doc_access in doc_sync_func(cc_pair, fetch_all_docs, fetch_all_doc_ids, None):
        # Update document access in the database
        from myplatform.db.permissions import update_document_external_access
        update_document_external_access(
            db_session=db_session,
            doc_id=doc_access.doc_id,
            external_access=doc_access.external_access,
        )
    
    logger.info(f"Permission sync completed for {source} cc_pair={cc_pair.id}")


def sync_cc_pair_permissions(
    db_session: Session,
    cc_pair_id: int,
) -> None:
    """
    Sync permissions for a specific connector-credential pair.
    
    Args:
        db_session: Database session
        cc_pair_id: The connector-credential pair ID
    """
    from esa.db.connector_credential_pair import get_connector_credential_pair_from_id
    
    cc_pair = get_connector_credential_pair_from_id(
        db_session=db_session,
        cc_pair_id=cc_pair_id,
    )
    
    if not cc_pair:
        logger.error(f"CC pair not found: {cc_pair_id}")
        return
    
    run_permission_sync(
        db_session=db_session,
        connector_id=cc_pair.connector_id,
        credential_id=cc_pair.credential_id,
    )
