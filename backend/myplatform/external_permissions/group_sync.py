"""
External group sync runner for MyPlatform.
Handles syncing user groups from external identity providers.
"""
from sqlalchemy.orm import Session

from esa.utils.logger import setup_logger

logger = setup_logger()


def sync_external_groups(db_session: Session) -> int:
    """
    Sync external groups from all configured sources.
    
    Args:
        db_session: Database session
        
    Returns:
        Number of groups synced
    """
    from myplatform.external_permissions.sync_params import source_requires_external_group_sync
    from myplatform.external_permissions.sync_params import get_source_perm_sync_config
    from esa.db.connector_credential_pair import get_all_auto_sync_cc_pairs
    
    synced_count = 0
    
    cc_pairs = get_all_auto_sync_cc_pairs(db_session)
    
    for cc_pair in cc_pairs:
        source = cc_pair.connector.source
        
        if not source_requires_external_group_sync(source):
            continue
        
        sync_config = get_source_perm_sync_config(source)
        if not sync_config or not sync_config.group_sync_config:
            continue
        
        logger.info(f"Syncing external groups for {source}")
        
        try:
            group_sync_func = sync_config.group_sync_config.group_sync_func
            tenant_id = None  # Get from context if multi-tenant
            
            for group in group_sync_func(tenant_id or "", cc_pair):
                # Save the external group to the database
                from myplatform.db.external_perm import upsert_external_user_group
                upsert_external_user_group(
                    db_session=db_session,
                    external_group=group,
                )
                synced_count += 1
        except Exception as e:
            logger.error(f"Failed to sync groups for {source}: {e}")
            continue
    
    return synced_count


def sync_groups_for_connector(
    db_session: Session,
    connector_id: int,
) -> int:
    """
    Sync external groups for a specific connector.
    
    Args:
        db_session: Database session
        connector_id: The connector ID
        
    Returns:
        Number of groups synced
    """
    from myplatform.external_permissions.sync_params import source_requires_external_group_sync
    from myplatform.external_permissions.sync_params import get_source_perm_sync_config
    from esa.db.connector import fetch_connector_by_id
    from esa.db.connector_credential_pair import get_cc_pairs_by_connector_id
    
    connector = fetch_connector_by_id(db_session, connector_id)
    if not connector:
        logger.error(f"Connector not found: {connector_id}")
        return 0
    
    source = connector.source
    
    if not source_requires_external_group_sync(source):
        logger.info(f"Source {source} does not require external group sync")
        return 0
    
    sync_config = get_source_perm_sync_config(source)
    if not sync_config or not sync_config.group_sync_config:
        return 0
    
    synced_count = 0
    cc_pairs = get_cc_pairs_by_connector_id(db_session, connector_id)
    
    for cc_pair in cc_pairs:
        logger.info(f"Syncing external groups for connector {connector_id}, cc_pair {cc_pair.id}")
        
        try:
            group_sync_func = sync_config.group_sync_config.group_sync_func
            tenant_id = None  # Get from context if multi-tenant
            
            for group in group_sync_func(tenant_id or "", cc_pair):
                from myplatform.db.external_perm import upsert_external_user_group
                upsert_external_user_group(
                    db_session=db_session,
                    external_group=group,
                )
                synced_count += 1
        except Exception as e:
            logger.error(f"Failed to sync groups for cc_pair {cc_pair.id}: {e}")
            continue
    
    return synced_count
