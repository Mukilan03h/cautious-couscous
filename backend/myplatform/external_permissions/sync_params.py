"""
Sync configuration parameters for external permissions.
Defines which document sources support permission sync and their configurations.
Ported from ee/esa/external_permissions/sync_params.py
"""
from collections.abc import Generator
from typing import Optional
from typing import TYPE_CHECKING

from pydantic import BaseModel

from myplatform.external_permissions.perm_sync_types import CensoringFuncType
from myplatform.external_permissions.perm_sync_types import DocSyncFuncType
from myplatform.external_permissions.perm_sync_types import FetchAllDocumentsFunction
from myplatform.external_permissions.perm_sync_types import FetchAllDocumentsIdsFunction
from myplatform.external_permissions.perm_sync_types import GroupSyncFuncType
from esa.configs.constants import DocumentSource

if TYPE_CHECKING:
    from esa.access.models import DocExternalAccess
    from esa.db.models import ConnectorCredentialPair
    from esa.indexing.indexing_heartbeat import IndexingHeartbeatInterface


# Default sync frequencies (in seconds)
DEFAULT_PERMISSION_DOC_SYNC_FREQUENCY = 60 * 60  # 1 hour
DEFAULT_PERMISSION_GROUP_SYNC_FREQUENCY = 60 * 60 * 4  # 4 hours

# Connector-specific sync frequencies
GOOGLE_DRIVE_PERMISSION_GROUP_SYNC_FREQUENCY = 60 * 60 * 4  # 4 hours
CONFLUENCE_PERMISSION_DOC_SYNC_FREQUENCY = 60 * 60  # 1 hour
CONFLUENCE_PERMISSION_GROUP_SYNC_FREQUENCY = 60 * 60 * 4  # 4 hours
JIRA_PERMISSION_DOC_SYNC_FREQUENCY = 60 * 60  # 1 hour
JIRA_PERMISSION_GROUP_SYNC_FREQUENCY = 60 * 60 * 4  # 4 hours
SLACK_PERMISSION_DOC_SYNC_FREQUENCY = 60 * 60  # 1 hour
GITHUB_PERMISSION_DOC_SYNC_FREQUENCY = 60 * 60  # 1 hour
GITHUB_PERMISSION_GROUP_SYNC_FREQUENCY = 60 * 60 * 4  # 4 hours
SHAREPOINT_PERMISSION_DOC_SYNC_FREQUENCY = 60 * 60  # 1 hour
SHAREPOINT_PERMISSION_GROUP_SYNC_FREQUENCY = 60 * 60 * 4  # 4 hours
TEAMS_PERMISSION_DOC_SYNC_FREQUENCY = 60 * 60  # 1 hour


class DocSyncConfig(BaseModel):
    """Configuration for document permission syncing."""
    doc_sync_frequency: int
    doc_sync_func: DocSyncFuncType
    initial_index_should_sync: bool

    class Config:
        arbitrary_types_allowed = True


class GroupSyncConfig(BaseModel):
    """Configuration for external group syncing."""
    group_sync_frequency: int
    group_sync_func: GroupSyncFuncType
    group_sync_is_cc_pair_agnostic: bool

    class Config:
        arbitrary_types_allowed = True


class CensoringConfig(BaseModel):
    """Configuration for chunk censoring."""
    chunk_censoring_func: CensoringFuncType

    class Config:
        arbitrary_types_allowed = True


class SyncConfig(BaseModel):
    """Combined sync configuration for a document source."""
    # None means we don't perform a doc_sync
    doc_sync_config: DocSyncConfig | None = None
    # None means we don't perform a group_sync
    group_sync_config: GroupSyncConfig | None = None
    # None means we don't perform a chunk_censoring
    censoring_config: CensoringConfig | None = None

    class Config:
        arbitrary_types_allowed = True


# Mock doc sync function for testing (no-op)
def mock_doc_sync(
    cc_pair: "ConnectorCredentialPair",
    fetch_all_docs_fn: FetchAllDocumentsFunction,
    fetch_all_docs_ids_fn: FetchAllDocumentsIdsFunction,
    callback: Optional["IndexingHeartbeatInterface"],
) -> Generator["DocExternalAccess", None, None]:
    """Mock doc sync function for testing - returns empty list since permissions are fetched during indexing"""
    yield from []


def _build_sync_config_map() -> dict[DocumentSource, SyncConfig]:
    """
    Build the source to sync config mapping.
    Import connector-specific sync functions lazily to avoid circular imports.
    """
    config_map: dict[DocumentSource, SyncConfig] = {}
    
    # Try to import Google Drive sync functions
    try:
        from myplatform.external_permissions.google_drive.doc_sync import gdrive_doc_sync
        from myplatform.external_permissions.google_drive.group_sync import gdrive_group_sync
        config_map[DocumentSource.GOOGLE_DRIVE] = SyncConfig(
            doc_sync_config=DocSyncConfig(
                doc_sync_frequency=DEFAULT_PERMISSION_DOC_SYNC_FREQUENCY,
                doc_sync_func=gdrive_doc_sync,
                initial_index_should_sync=True,
            ),
            group_sync_config=GroupSyncConfig(
                group_sync_frequency=GOOGLE_DRIVE_PERMISSION_GROUP_SYNC_FREQUENCY,
                group_sync_func=gdrive_group_sync,
                group_sync_is_cc_pair_agnostic=False,
            ),
        )
    except ImportError:
        pass

    # Try to import Confluence sync functions
    try:
        from myplatform.external_permissions.confluence.doc_sync import confluence_doc_sync
        from myplatform.external_permissions.confluence.group_sync import confluence_group_sync
        config_map[DocumentSource.CONFLUENCE] = SyncConfig(
            doc_sync_config=DocSyncConfig(
                doc_sync_frequency=CONFLUENCE_PERMISSION_DOC_SYNC_FREQUENCY,
                doc_sync_func=confluence_doc_sync,
                initial_index_should_sync=False,
            ),
            group_sync_config=GroupSyncConfig(
                group_sync_frequency=CONFLUENCE_PERMISSION_GROUP_SYNC_FREQUENCY,
                group_sync_func=confluence_group_sync,
                group_sync_is_cc_pair_agnostic=True,
            ),
        )
    except ImportError:
        pass

    # Try to import SharePoint sync functions
    try:
        from myplatform.external_permissions.sharepoint.doc_sync import sharepoint_doc_sync
        from myplatform.external_permissions.sharepoint.group_sync import sharepoint_group_sync
        config_map[DocumentSource.SHAREPOINT] = SyncConfig(
            doc_sync_config=DocSyncConfig(
                doc_sync_frequency=SHAREPOINT_PERMISSION_DOC_SYNC_FREQUENCY,
                doc_sync_func=sharepoint_doc_sync,
                initial_index_should_sync=True,
            ),
            group_sync_config=GroupSyncConfig(
                group_sync_frequency=SHAREPOINT_PERMISSION_GROUP_SYNC_FREQUENCY,
                group_sync_func=sharepoint_group_sync,
                group_sync_is_cc_pair_agnostic=False,
            ),
        )
    except ImportError:
        pass

    # Try to import Slack sync functions
    try:
        from myplatform.external_permissions.slack.doc_sync import slack_doc_sync
        config_map[DocumentSource.SLACK] = SyncConfig(
            doc_sync_config=DocSyncConfig(
                doc_sync_frequency=SLACK_PERMISSION_DOC_SYNC_FREQUENCY,
                doc_sync_func=slack_doc_sync,
                initial_index_should_sync=True,
            ),
        )
    except ImportError:
        pass

    # Try to import GitHub sync functions
    try:
        from myplatform.external_permissions.github.doc_sync import github_doc_sync
        from myplatform.external_permissions.github.group_sync import github_group_sync
        config_map[DocumentSource.GITHUB] = SyncConfig(
            doc_sync_config=DocSyncConfig(
                doc_sync_frequency=GITHUB_PERMISSION_DOC_SYNC_FREQUENCY,
                doc_sync_func=github_doc_sync,
                initial_index_should_sync=True,
            ),
            group_sync_config=GroupSyncConfig(
                group_sync_frequency=GITHUB_PERMISSION_GROUP_SYNC_FREQUENCY,
                group_sync_func=github_group_sync,
                group_sync_is_cc_pair_agnostic=False,
            ),
        )
    except ImportError:
        pass

    # Try to import Jira sync functions
    try:
        from myplatform.external_permissions.jira.doc_sync import jira_doc_sync
        from myplatform.external_permissions.jira.group_sync import jira_group_sync
        config_map[DocumentSource.JIRA] = SyncConfig(
            doc_sync_config=DocSyncConfig(
                doc_sync_frequency=JIRA_PERMISSION_DOC_SYNC_FREQUENCY,
                doc_sync_func=jira_doc_sync,
                initial_index_should_sync=True,
            ),
            group_sync_config=GroupSyncConfig(
                group_sync_frequency=JIRA_PERMISSION_GROUP_SYNC_FREQUENCY,
                group_sync_func=jira_group_sync,
                group_sync_is_cc_pair_agnostic=True,
            ),
        )
    except ImportError:
        pass

    # Try to import Gmail sync functions
    try:
        from myplatform.external_permissions.gmail.doc_sync import gmail_doc_sync
        config_map[DocumentSource.GMAIL] = SyncConfig(
            doc_sync_config=DocSyncConfig(
                doc_sync_frequency=DEFAULT_PERMISSION_DOC_SYNC_FREQUENCY,
                doc_sync_func=gmail_doc_sync,
                initial_index_should_sync=False,
            ),
        )
    except ImportError:
        pass

    # Try to import Teams sync functions
    try:
        from myplatform.external_permissions.teams.doc_sync import teams_doc_sync
        config_map[DocumentSource.TEAMS] = SyncConfig(
            doc_sync_config=DocSyncConfig(
                doc_sync_frequency=TEAMS_PERMISSION_DOC_SYNC_FREQUENCY,
                doc_sync_func=teams_doc_sync,
                initial_index_should_sync=True,
            ),
        )
    except ImportError:
        pass

    # Try to import Salesforce censoring
    try:
        from myplatform.external_permissions.salesforce.postprocessing import censor_salesforce_chunks
        config_map[DocumentSource.SALESFORCE] = SyncConfig(
            censoring_config=CensoringConfig(
                chunk_censoring_func=censor_salesforce_chunks,
            ),
        )
    except ImportError:
        pass

    # Mock connector for testing
    config_map[DocumentSource.MOCK_CONNECTOR] = SyncConfig(
        doc_sync_config=DocSyncConfig(
            doc_sync_frequency=DEFAULT_PERMISSION_DOC_SYNC_FREQUENCY,
            doc_sync_func=mock_doc_sync,
            initial_index_should_sync=True,
        ),
    )

    return config_map


# Lazy-loaded config map
_SOURCE_TO_SYNC_CONFIG: dict[DocumentSource, SyncConfig] | None = None


def _get_sync_config_map() -> dict[DocumentSource, SyncConfig]:
    """Get the sync config map, lazily loading it on first access."""
    global _SOURCE_TO_SYNC_CONFIG
    if _SOURCE_TO_SYNC_CONFIG is None:
        _SOURCE_TO_SYNC_CONFIG = _build_sync_config_map()
    return _SOURCE_TO_SYNC_CONFIG


def source_requires_doc_sync(source: DocumentSource) -> bool:
    """Checks if the given DocumentSource requires doc syncing."""
    config_map = _get_sync_config_map()
    if source not in config_map:
        return False
    return config_map[source].doc_sync_config is not None


def source_requires_external_group_sync(source: DocumentSource) -> bool:
    """Checks if the given DocumentSource requires external group syncing."""
    config_map = _get_sync_config_map()
    if source not in config_map:
        return False
    return config_map[source].group_sync_config is not None


def get_source_perm_sync_config(source: DocumentSource) -> SyncConfig | None:
    """Returns the sync config for the given DocumentSource."""
    return _get_sync_config_map().get(source)


def source_group_sync_is_cc_pair_agnostic(source: DocumentSource) -> bool:
    """Checks if the given DocumentSource has cc_pair agnostic group syncing."""
    config_map = _get_sync_config_map()
    if source not in config_map:
        return False

    group_sync_config = config_map[source].group_sync_config
    if group_sync_config is None:
        return False

    return group_sync_config.group_sync_is_cc_pair_agnostic


def get_all_cc_pair_agnostic_group_sync_sources() -> set[DocumentSource]:
    """Returns the set of sources that have external group syncing that is cc_pair agnostic."""
    return {
        source
        for source, sync_config in _get_sync_config_map().items()
        if sync_config.group_sync_config is not None
        and sync_config.group_sync_config.group_sync_is_cc_pair_agnostic
    }


def check_if_valid_sync_source(source_type: DocumentSource) -> bool:
    """Check if the source type supports permission sync."""
    return source_type in _get_sync_config_map()


def get_all_censoring_enabled_sources() -> set[DocumentSource]:
    """Returns the set of sources that have censoring enabled."""
    return {
        source
        for source, sync_config in _get_sync_config_map().items()
        if sync_config.censoring_config is not None
    }


def source_should_fetch_permissions_during_indexing(source: DocumentSource) -> bool:
    """Returns True if the given DocumentSource requires permissions to be fetched during indexing."""
    config_map = _get_sync_config_map()
    if source not in config_map:
        return False

    doc_sync_config = config_map[source].doc_sync_config
    if doc_sync_config is None:
        return False

    return doc_sync_config.initial_index_should_sync
