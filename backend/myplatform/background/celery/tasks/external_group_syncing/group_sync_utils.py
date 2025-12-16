"""
Group sync utilities for MyPlatform.
Ported from ee/esa/background/celery/tasks/external_group_syncing/group_sync_utils.py - FULL VERSION
"""
from sqlalchemy.orm import Session

from myplatform.external_permissions.sync_params import (
    source_group_sync_is_cc_pair_agnostic,
)
from esa.db.connector import mark_cc_pair_as_external_group_synced
from esa.db.connector_credential_pair import get_connector_credential_pairs_for_source
from esa.db.models import ConnectorCredentialPair
from esa.utils.logger import setup_logger

logger = setup_logger()


def get_group_sync_interval_hours() -> int:
    """Get the interval in hours between external group syncs."""
    return 4  # Default to 4 hours


def should_sync_groups_for_connector(
    db_session: Session,
    connector_id: int,
) -> bool:
    """
    Determine if groups should be synced for a specific connector.
    
    Args:
        db_session: Database session
        connector_id: The connector ID to check
        
    Returns:
        True if groups should be synced, False otherwise
    """
    # Import here to avoid circular dependencies
    from myplatform.db.connector_permissions import get_connector_permission_config
    
    config = get_connector_permission_config(db_session, connector_id)
    if not config:
        return False
    
    return config.sync_groups_enabled


def _get_all_cc_pair_ids_to_mark_as_group_synced(
    db_session: Session, cc_pair: ConnectorCredentialPair
) -> list[int]:
    if not source_group_sync_is_cc_pair_agnostic(cc_pair.connector.source):
        return [cc_pair.id]

    cc_pairs = get_connector_credential_pairs_for_source(
        db_session, cc_pair.connector.source
    )
    return [cc_pair.id for cc_pair in cc_pairs]


def mark_all_relevant_cc_pairs_as_external_group_synced(
    db_session: Session, cc_pair: ConnectorCredentialPair
) -> None:
    """For some source types, one successful group sync run should count for all
    cc pairs of that type. This function handles that case."""
    cc_pair_ids = _get_all_cc_pair_ids_to_mark_as_group_synced(db_session, cc_pair)
    for cc_pair_id in cc_pair_ids:
        mark_cc_pair_as_external_group_synced(db_session, cc_pair_id)
