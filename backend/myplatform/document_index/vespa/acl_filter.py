"""
Vespa ACL filter builder for MyPlatform.
Builds YQL filters for access control in Vespa search.
"""
from esa.access.utils import prefix_external_group
from esa.access.utils import prefix_user_group
from esa.access.utils import prefix_user_email
from esa.utils.logger import setup_logger

logger = setup_logger()


def build_acl_filter(
    user_acl: set[str],
    include_public: bool = True,
) -> str:
    """
    Build a Vespa YQL filter for access control.
    
    This creates a filter clause that matches documents where:
    - Document is public, OR
    - Document has an ACL entry matching one of the user's ACL entries
    
    Args:
        user_acl: Set of ACL entries the user has access to
        include_public: Whether to include public documents
        
    Returns:
        YQL filter string for Vespa query
    """
    if not user_acl and not include_public:
        # User has no ACL entries and we're not including public docs
        # This should return nothing
        return "false"
    
    filter_parts = []
    
    # Add public document check
    if include_public:
        filter_parts.append("access_control_list contains 'PUBLIC'")
    
    # Add each ACL entry as an alternative
    for acl_entry in user_acl:
        # Escape any special characters in the ACL entry
        escaped_entry = acl_entry.replace("'", "\\'")
        filter_parts.append(f"access_control_list contains '{escaped_entry}'")
    
    if not filter_parts:
        return "true"  # No restrictions
    
    # Combine with OR
    return f"({' or '.join(filter_parts)})"


def build_user_acl_entries(
    user_email: str | None,
    user_group_names: list[str] | None = None,
    external_group_ids: list[str] | None = None,
) -> set[str]:
    """
    Build ACL entries for a user based on their email and groups.
    
    Args:
        user_email: The user's email address
        user_group_names: List of internal group names the user belongs to
        external_group_ids: List of external group IDs the user belongs to
        
    Returns:
        Set of ACL entry strings
    """
    acl_entries = set()
    
    # Add user's email as an ACL entry
    if user_email:
        acl_entries.add(prefix_user_email(user_email.lower()))
    
    # Add user's internal groups
    if user_group_names:
        for group_name in user_group_names:
            acl_entries.add(prefix_user_group(group_name))
    
    # Add user's external groups
    if external_group_ids:
        for group_id in external_group_ids:
            acl_entries.add(prefix_external_group(group_id))
    
    return acl_entries


def build_document_acl_entries(
    user_emails: list[str] | None = None,
    user_groups: list[str] | None = None,
    external_user_emails: list[str] | None = None,
    external_user_group_ids: list[str] | None = None,
    is_public: bool = False,
) -> list[str]:
    """
    Build ACL entries for a document.
    
    These entries are stored with the document in Vespa and matched
    against user ACL entries during search.
    
    Args:
        user_emails: List of user emails with access
        user_groups: List of internal group names with access
        external_user_emails: List of external user emails
        external_user_group_ids: List of external group IDs with access
        is_public: Whether the document is public
        
    Returns:
        List of ACL entry strings to store with document
    """
    acl_entries = []
    
    # Add public marker
    if is_public:
        acl_entries.append("PUBLIC")
    
    # Add user emails
    if user_emails:
        for email in user_emails:
            acl_entries.append(prefix_user_email(email.lower()))
    
    # Add internal groups
    if user_groups:
        for group_name in user_groups:
            acl_entries.append(prefix_user_group(group_name))
    
    # Add external user emails
    if external_user_emails:
        for email in external_user_emails:
            acl_entries.append(prefix_user_email(email.lower()))
    
    # Add external groups
    if external_user_group_ids:
        for group_id in external_user_group_ids:
            acl_entries.append(prefix_external_group(group_id))
    
    return acl_entries
