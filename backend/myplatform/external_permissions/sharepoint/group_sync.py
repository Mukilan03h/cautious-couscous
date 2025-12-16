"""
SharePoint group sync for MyPlatform.
"""
from collections.abc import Generator

from myplatform.db.external_perm import ExternalUserGroup
from esa.db.models import ConnectorCredentialPair
from esa.utils.logger import setup_logger

logger = setup_logger()


def sharepoint_group_sync(
    tenant_id: str,
    cc_pair: ConnectorCredentialPair,
) -> Generator[ExternalUserGroup, None, None]:
    """Sync user groups from SharePoint/Microsoft 365."""
    logger.info(f"Syncing SharePoint groups for CC pair {cc_pair.id}")
    # Placeholder - actual implementation would query Microsoft Graph API
    yield from []
