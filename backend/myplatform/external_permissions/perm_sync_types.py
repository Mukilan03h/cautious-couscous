"""
Permission sync type definitions for MyPlatform.
Defines protocols and type aliases for document/group sync functions.
Ported from ee/esa/external_permissions/perm_sync_types.py
"""
from collections.abc import Callable
from collections.abc import Generator
from typing import Optional
from typing import Protocol
from typing import TYPE_CHECKING

from esa.context.search.models import InferenceChunk
from esa.db.utils import DocumentRow
from esa.db.utils import SortOrder

if TYPE_CHECKING:
    from myplatform.db.external_perm import ExternalUserGroup
    from esa.access.models import DocExternalAccess
    from esa.db.models import ConnectorCredentialPair
    from esa.indexing.indexing_heartbeat import IndexingHeartbeatInterface


class FetchAllDocumentsFunction(Protocol):
    """Protocol for a function that fetches documents for a connector credential pair.

    This protocol defines the interface for functions that retrieve documents
    from the database, typically used in permission synchronization workflows.
    """

    def __call__(
        self,
        sort_order: SortOrder | None,
    ) -> list[DocumentRow]:
        """
        Fetches documents for a connector credential pair.
        """
        ...


class FetchAllDocumentsIdsFunction(Protocol):
    """Protocol for a function that fetches document IDs for a connector credential pair.

    This protocol defines the interface for functions that retrieve document IDs
    from the database, typically used in permission synchronization workflows.
    """

    def __call__(
        self,
    ) -> list[str]:
        """
        Fetches document IDs for a connector credential pair.
        """
        ...


# Defining the input/output types for the sync functions
DocSyncFuncType = Callable[
    [
        "ConnectorCredentialPair",
        FetchAllDocumentsFunction,
        FetchAllDocumentsIdsFunction,
        Optional["IndexingHeartbeatInterface"],
    ],
    Generator["DocExternalAccess", None, None],
]

GroupSyncFuncType = Callable[
    [
        str,  # tenant_id
        "ConnectorCredentialPair",  # cc_pair
    ],
    Generator["ExternalUserGroup", None, None],
]

# list of chunks to be censored and the user email. returns censored chunks
CensoringFuncType = Callable[[list[InferenceChunk], str], list[InferenceChunk]]
