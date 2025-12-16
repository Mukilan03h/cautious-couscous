"""Slack document permission sync for MyPlatform."""
from collections.abc import Generator
from typing import Optional

from myplatform.external_permissions.perm_sync_types import FetchAllDocumentsFunction
from myplatform.external_permissions.perm_sync_types import FetchAllDocumentsIdsFunction
from myplatform.external_permissions.utils import generic_doc_sync
from esa.access.models import DocExternalAccess
from esa.configs.constants import DocumentSource
from esa.db.models import ConnectorCredentialPair
from esa.indexing.indexing_heartbeat import IndexingHeartbeatInterface
from esa.utils.logger import setup_logger

logger = setup_logger()


def slack_doc_sync(
    cc_pair: ConnectorCredentialPair,
    fetch_all_docs_fn: FetchAllDocumentsFunction,
    fetch_all_docs_ids_fn: FetchAllDocumentsIdsFunction,
    callback: Optional[IndexingHeartbeatInterface],
) -> Generator[DocExternalAccess, None, None]:
    """Sync document permissions from Slack (channel-level access)."""
    from esa.connectors.slack.connector import SlackConnector
    
    connector = SlackConnector(**cc_pair.connector.connector_specific_config)
    connector.load_credentials(cc_pair.credential.credential_json)
    
    yield from generic_doc_sync(
        cc_pair=cc_pair,
        fetch_all_existing_docs_ids_fn=fetch_all_docs_ids_fn,
        callback=callback,
        doc_source=DocumentSource.SLACK,
        slim_connector=connector,
        label="Slack Permission Sync",
    )
