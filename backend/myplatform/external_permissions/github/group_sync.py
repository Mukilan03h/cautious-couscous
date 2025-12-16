"""GitHub group sync for MyPlatform."""
from collections.abc import Generator
from myplatform.db.external_perm import ExternalUserGroup
from esa.db.models import ConnectorCredentialPair
from esa.utils.logger import setup_logger

logger = setup_logger()


def github_group_sync(
    tenant_id: str,
    cc_pair: ConnectorCredentialPair,
) -> Generator[ExternalUserGroup, None, None]:
    """Sync user groups (teams/orgs) from GitHub."""
    logger.info(f"Syncing GitHub groups for CC pair {cc_pair.id}")
    yield from []
