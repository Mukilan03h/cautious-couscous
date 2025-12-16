"""
Permission sync validation for connectors.
Ported from ee/esa/connectors/perm_sync_valid.py
"""
from esa.configs.constants import DocumentSource


# Set of sources that support permission synchronization
PERM_SYNC_VALID_SOURCES = {
    DocumentSource.GOOGLE_DRIVE,
    DocumentSource.CONFLUENCE,
    DocumentSource.SLACK,
    DocumentSource.GITHUB,
    DocumentSource.JIRA,
    DocumentSource.SHAREPOINT,
    DocumentSource.GMAIL,
    DocumentSource.TEAMS,
    DocumentSource.SALESFORCE,
}


def is_perm_sync_valid(source: DocumentSource) -> bool:
    """
    Check if a document source supports permission synchronization.
    
    Args:
        source: The document source to check
        
    Returns:
        True if the source supports permission sync
    """
    return source in PERM_SYNC_VALID_SOURCES


def get_perm_sync_valid_sources() -> set[DocumentSource]:
    """
    Get the set of sources that support permission synchronization.
    
    Returns:
        Set of DocumentSource enums that support permission sync
    """
    return PERM_SYNC_VALID_SOURCES.copy()
