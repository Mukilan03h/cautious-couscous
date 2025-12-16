"""Gmail document permission sync for MyPlatform."""
from collections.abc import Generator
from typing import Optional

from myplatform.external_permissions.perm_sync_types import FetchAllDocumentsFunction
from myplatform.external_permissions.perm_sync_types import FetchAllDocumentsIdsFunction
from esa.access.models import DocExternalAccess
from esa.db.models import ConnectorCredentialPair
from esa.indexing.indexing_heartbeat import IndexingHeartbeatInterface
from esa.utils.logger import setup_logger

logger = setup_logger()


def gmail_doc_sync(
    cc_pair: ConnectorCredentialPair,
    fetch_all_docs_fn: FetchAllDocumentsFunction,
    fetch_all_docs_ids_fn: FetchAllDocumentsIdsFunction,
    callback: Optional[IndexingHeartbeatInterface],
) -> Generator[DocExternalAccess, None, None]:
    """Sync document permissions from Gmail (user-level access only)."""
    # Gmail is user-specific, permissions are implicit
    logger.info(f"Gmail doc sync for CC pair {cc_pair.id}")
    yield from []
