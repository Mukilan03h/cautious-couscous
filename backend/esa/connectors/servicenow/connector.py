"""ServiceNow Connector for ESA.

Comprehensive connector supporting all major ServiceNow modules:
- ITSM: Incidents, Problems, Changes, Requests, Tasks
- Knowledge Management: KB Articles
- CMDB: Configuration Items (servers, applications, hardware, etc.)
- Customer Service Management: Cases, Contacts, Accounts
- HR Service Delivery: HR Cases, HR Tasks
- Service Catalog: Catalog Items
- Security Operations: Security Incidents

Reference: ServiceNow Zurich REST API Documentation
"""

import copy
from typing import Any

from requests.exceptions import HTTPError
from typing_extensions import override

from esa.configs.constants import DocumentSource
from esa.connectors.cross_connector_utils.miscellaneous_utils import time_str_to_utc
from esa.connectors.exceptions import (
    ConnectorValidationError,
    CredentialExpiredError,
    InsufficientPermissionsError,
)
from esa.connectors.interfaces import (
    CheckpointedConnector,
    CheckpointOutput,
    ConnectorFailure,
    GenerateSlimDocumentOutput,
    SecondsSinceUnixEpoch,
    SlimConnectorWithPermSync,
)
from esa.connectors.models import (
    ConnectorCheckpoint,
    Document,
    DocumentFailure,
    SlimDocument,
    TextSection,
)
from esa.connectors.servicenow.client import (
    ServiceNowAPIError,
    ServiceNowAuthError,
    ServiceNowAPIError,
    ServiceNowAuthError,
    ServiceNowNotFoundError,
    ServiceNowPermissionError,
)
from esa.connectors.servicenow.enhanced_client import EnhancedServiceNowClient
from esa.file_processing.html_utils import parse_html_page_basic
from esa.indexing.indexing_heartbeat import IndexingHeartbeatInterface
from esa.utils.logger import setup_logger

logger = setup_logger()

# Maximum records per API request (per Zurich docs best practices)
MAX_PAGE_SIZE = 100

# Batch size for slim document retrieval
_SLIM_BATCH_SIZE = 1000

# Content type to table mapping
# Each content type can index one or more tables
CONTENT_TYPE_TABLES: dict[str, list[str]] = {
    # Individual ITSM modules
    "incidents": ["incident"],
    "problems": ["problem"],
    "changes": ["change_request"],
    "requests": ["sc_request", "sc_req_item"],
    "tasks": ["task", "sc_task"],
    
    # Knowledge Management
    "knowledge": ["kb_knowledge"],
    
    # CMDB modules
    "cmdb_servers": ["cmdb_ci_server"],
    "cmdb_computers": ["cmdb_ci_computer"],
    "cmdb_applications": ["cmdb_ci_appl"],
    "cmdb_services": ["cmdb_ci_service"],
    "cmdb_hardware": ["cmdb_ci_hardware"],
    "cmdb_all": ["cmdb_ci"],
    
    # Customer Service Management
    "csm_cases": ["sn_customerservice_case"],
    "csm_accounts": ["customer_account"],
    "csm_contacts": ["customer_contact"],
    "csm_all": ["sn_customerservice_case", "customer_account", "customer_contact"],
    
    # HR Service Delivery
    "hr_cases": ["sn_hr_core_case"],
    "hr_tasks": ["sn_hr_core_task"],
    "hr_all": ["sn_hr_core_case", "sn_hr_core_task"],
    
    # Service Catalog
    "catalog_items": ["sc_cat_item"],
    "catalog_categories": ["sc_category"],
    "catalog_all": ["sc_cat_item", "sc_category"],
    
    # Security Operations
    "security_incidents": ["sn_si_incident"],
    "security_vulnerabilities": ["sn_vul_vulnerable_item"],
    "security_all": ["sn_si_incident", "sn_vul_vulnerable_item"],
    
    # Users and Groups
    "users": ["sys_user"],
    "groups": ["sys_user_group"],
    "users_all": ["sys_user", "sys_user_group"],
    
    # Combined content types
    "all_itsm": ["incident", "problem", "change_request", "task"],
    "all_knowledge": ["kb_knowledge"],
    "all_cmdb": ["cmdb_ci_server", "cmdb_ci_computer", "cmdb_ci_appl", "cmdb_ci_service"],
    "all": [
        "incident", "problem", "change_request", "kb_knowledge",
        "cmdb_ci_server", "cmdb_ci_appl", "sc_cat_item",
    ],
}


class ServiceNowCredentialsError(PermissionError):
    """Raised when ServiceNow credentials are not configured."""

    def __init__(self) -> None:
        super().__init__(
            "ServiceNow credentials not set up, was load_credentials called?"
        )


class ServiceNowConnectorCheckpoint(ConnectorCheckpoint):
    """Checkpoint state for ServiceNow connector.
    
    Tracks pagination state across multiple tables for efficient
    incremental indexing.
    """
    # Track offset per table for multi-table pagination
    table_offsets: dict[str, int]
    # Current table index in the tables list
    current_table_index: int


class ServiceNowConnector(
    SlimConnectorWithPermSync,
    CheckpointedConnector[ServiceNowConnectorCheckpoint],
):
    """Comprehensive ServiceNow connector for ESA.
    
    Implements the ServiceNow Table API (v2) following the official
    Zurich API specification. Supports all major ServiceNow modules
    with configurable content type selection.
    
    Features:
    - Multiple content type selection (ITSM, Knowledge, CMDB, etc.)
    - Custom table support for extended configurations
    - OAuth 2.0 and Basic Authentication
    - Checkpoint-based pagination for reliable incremental sync
    - Graceful handling of inaccessible tables (ACL-based)
    """

    def __init__(
        self,
        content_type: str = "all_itsm",
        custom_tables: str | None = None,
        calls_per_minute: int = 600,
    ) -> None:
        """Initialize ServiceNow connector.
        
        Args:
            content_type: Type of content to index (see CONTENT_TYPE_TABLES)
            custom_tables: Comma-separated list of additional tables to index
            calls_per_minute: Optional rate limit for API calls
        """
        self.content_type = content_type
        self.custom_tables = (
            [t.strip() for t in custom_tables.split(",") if t.strip()]
            if custom_tables
            else []
        )
        self.calls_per_minute = calls_per_minute
        
        # Handle UI mapping mismatches (Frontend sends display names)
        # TODO: Fix frontend definition to send keys
        if self.content_type == "Incidents Only":
            self.content_type = "incidents"
        elif self.content_type == "Service Catalog Items":
            self.content_type = "catalog_items"
        elif self.content_type == "Knowledge Base":
            self.content_type = "knowledge"
        elif self.content_type == "All ITSM":
            self.content_type = "all_itsm"
        
        self.client: EnhancedServiceNowClient | None = None

    def _get_tables_to_index(self) -> list[str]:
        """Get the list of tables to index based on content type."""
        tables = list(CONTENT_TYPE_TABLES.get(self.content_type, []))
        
        # Add custom tables
        if self.custom_tables:
            for table in self.custom_tables:
                if table not in tables:
                    tables.append(table)
        
        return tables

    def load_credentials(self, credentials: dict[str, Any]) -> dict[str, Any] | None:
        """Load ServiceNow credentials.
        
        Required credentials:
        - servicenow_instance_url: Instance URL or subdomain
        - servicenow_username: Service account username
        - servicenow_password: Service account password
        
        Optional credentials (for OAuth 2.0):
        - servicenow_client_id: OAuth client ID
        - servicenow_client_secret: OAuth client secret
        """
        instance_url = credentials.get("servicenow_instance_url", "")
        username = credentials.get("servicenow_username")
        password = credentials.get("servicenow_password")
        client_id = credentials.get("servicenow_client_id")
        client_secret = credentials.get("servicenow_client_secret")
        
        self.client = EnhancedServiceNowClient(
            instance_url=instance_url,
            username=username,
            password=password,
            client_id=client_id,
            client_secret=client_secret,
            calls_per_minute=self.calls_per_minute,
        )
        
        return None

    def _get_value(self, record: dict[str, Any], field: str) -> str:
        """Get raw value from record field."""
        val = record.get(field)
        if isinstance(val, dict):
            return str(val.get("value") or "")
        return str(val or "")

    def _get_display_value(self, record: dict[str, Any], field: str) -> str:
        """Get display value from record field."""
        val = record.get(field)
        if isinstance(val, dict):
            return str(val.get("display_value") or "")
        return str(val or "")

    def _record_to_document(
        self,
        record: dict[str, Any],
        table_name: str,
    ) -> Document:
        """Convert a ServiceNow record to an ESA Document."""
        sys_id = self._get_value(record, "sys_id")
        
        # Get display field configuration via TableAPIClient method
        config = self.client.get_table_config(table_name) if self.client else {}
        display_field = config.get("display_field", "number")
        
        # Get display value
        display_value = (
            self._get_display_value(record, display_field)
            or self._get_value(record, display_field)
            or sys_id
        )
        
        # Build text content
        short_desc = self._get_display_value(record, "short_description")
        
        # Get description/text content, handling HTML
        description = ""
        for field in ["description", "text"]:
            content = self._get_display_value(record, field)
            if content:
                # Parse HTML if present
                if "<" in content and ">" in content:
                    description = parse_html_page_basic(content)
                else:
                    description = content
                break
        
        # Build full document text
        table_display = table_name.replace("_", " ").replace("sn ", "").title()
        full_text = f"{table_display}: {display_value}\n\n"
        if short_desc:
            full_text += f"{short_desc}\n\n"
        if description:
            full_text += description
        
        # Build record URL
        link = self.client.build_record_url(table_name, sys_id) if self.client else ""
        
        # Parse updated timestamp
        updated_at = self._get_value(record, "sys_updated_on") or self._get_value(record, "opened_at")
        update_time = time_str_to_utc(updated_at) if updated_at else None
        
        # Build metadata from available fields
        metadata: dict[str, str | list[str]] = {"table": table_name}
        
        # Extract common metadata fields
        metadata_fields = [
            "state", "priority", "urgency", "impact", "category",
            "subcategory", "type", "risk", "severity", "workflow_state",
            "operational_status", "install_status", "active",
        ]
        for field in metadata_fields:
            # Prefer display values
            value = self._get_display_value(record, field)
            if value and value.strip():
                metadata[field] = value
        
        # Build semantic identifier
        semantic_id = f"{table_display} {display_value}"
        if short_desc:
            # Truncate long descriptions
            truncated_desc = short_desc[:100] + "..." if len(short_desc) > 100 else short_desc
            semantic_id = f"{semantic_id}: {truncated_desc}"
        
        return Document(
            id=f"servicenow_{table_name}_{sys_id}",
            sections=[TextSection(link=link, text=full_text.strip())],
            source=DocumentSource.SERVICENOW,
            semantic_identifier=semantic_id,
            doc_updated_at=update_time,
            metadata=metadata,
        )

    @override
    def load_from_checkpoint(
        self,
        start: SecondsSinceUnixEpoch,
        end: SecondsSinceUnixEpoch,
        checkpoint: ServiceNowConnectorCheckpoint,
    ) -> CheckpointOutput[ServiceNowConnectorCheckpoint]:
        """Load documents from ServiceNow using checkpoint-based pagination.
        
        Iterates through configured tables, processing each one completely
        before moving to the next. Handles table access errors gracefully
        by skipping inaccessible tables.
        """
        if self.client is None:
            raise ServiceNowCredentialsError()
        
        checkpoint = copy.deepcopy(checkpoint)
        tables = self._get_tables_to_index()
        
        # Process tables starting from checkpoint position
        while checkpoint.current_table_index < len(tables):
            table_name = tables[checkpoint.current_table_index]
            offset = checkpoint.table_offsets.get(table_name, 0)
            
            logger.info(
                f"ServiceNow: Fetching {table_name} at offset {offset}"
            )
            
            try:
                records, has_more = self.client.fetch_table_records(
                    table_name=table_name,
                    offset=offset,
                    limit=MAX_PAGE_SIZE,
                    updated_after=start if start else None,
                )
            except ServiceNowPermissionError as e:
                # Skip tables user doesn't have ACL access to
                logger.warning(
                    f"ServiceNow: Skipping {table_name} - insufficient permissions: {e}"
                )
                checkpoint.current_table_index += 1
                continue
            except ServiceNowNotFoundError as e:
                # Skip tables that don't exist (might be plugin-dependent)
                logger.warning(
                    f"ServiceNow: Skipping {table_name} - table not found: {e}"
                )
                checkpoint.current_table_index += 1
                continue
            except ServiceNowAPIError as e:
                # Log other API errors but continue
                logger.error(f"ServiceNow: Error fetching {table_name}: {e}")
                checkpoint.current_table_index += 1
                continue
            
            # Convert records to documents
            for record in records:
                try:
                    doc = self._record_to_document(record, table_name)
                    yield doc
                except Exception as e:
                    # Yield failure for individual record errors
                    yield ConnectorFailure(
                        failed_document=DocumentFailure(
                            document_id=record.get("sys_id", "unknown"),
                            document_link=self.client.build_record_url(
                                table_name, record.get("sys_id", "")
                            ) if self.client else "",
                        ),
                        failure_message=f"Failed to convert {table_name} record: {e}",
                        exception=e,
                    )
            
            # Update checkpoint
            checkpoint.table_offsets[table_name] = offset + len(records)
            
            if has_more:
                # More records in this table
                checkpoint.has_more = True
                return checkpoint
            
            # Table complete, move to next
            checkpoint.current_table_index += 1
        
        # All tables processed
        checkpoint.has_more = False
        return checkpoint

    def retrieve_all_slim_docs_perm_sync(
        self,
        start: SecondsSinceUnixEpoch | None = None,
        end: SecondsSinceUnixEpoch | None = None,
        callback: IndexingHeartbeatInterface | None = None,
    ) -> GenerateSlimDocumentOutput:
        """Retrieve slim documents for permission sync and pruning.
        
        Fetches only document IDs without full content for efficient
        comparison during pruning operations.
        """
        if self.client is None:
            raise ServiceNowCredentialsError()
        
        slim_batch: list[SlimDocument] = []
        tables = self._get_tables_to_index()
        
        for table_name in tables:
            offset = 0
            
            while True:
                try:
                    records, has_more = self.client.fetch_table_records(
                        table_name=table_name,
                        offset=offset,
                        limit=MAX_PAGE_SIZE,
                        fields="sys_id",  # Only need ID field
                    )
                except (ServiceNowPermissionError, ServiceNowNotFoundError):
                    # Skip inaccessible tables
                    break
                except ServiceNowAPIError:
                    break
                
                for record in records:
                    sys_id = record.get("sys_id", "")
                    if sys_id:
                        slim_batch.append(
                            SlimDocument(id=f"servicenow_{table_name}_{sys_id}")
                        )
                        
                        if len(slim_batch) >= _SLIM_BATCH_SIZE:
                            yield slim_batch
                            slim_batch = []
                
                if not has_more:
                    break
                    
                offset += MAX_PAGE_SIZE
        
        # Yield remaining documents
        if slim_batch:
            yield slim_batch

    @override
    def validate_connector_settings(self) -> None:
        """Validate ServiceNow credentials and connectivity.
        
        Tests authentication and basic table access per Zurich docs:
        - 401: Authentication failed
        - 403: Insufficient ACL permissions
        - 200: Success
        """
        if self.client is None:
            raise ServiceNowCredentialsError()
        
        try:
            # Try to fetch a single incident to validate
            self.client.fetch_table_records("incident", limit=1)
            logger.info("ServiceNow: Connection validated successfully")
            
        except ServiceNowAuthError as e:
            raise CredentialExpiredError(
                f"ServiceNow authentication failed: {e}"
            ) from e
        except ServiceNowPermissionError as e:
            raise InsufficientPermissionsError(
                f"ServiceNow permissions insufficient: {e}"
            ) from e
        except ServiceNowAPIError as e:
            raise ConnectorValidationError(
                f"ServiceNow connection failed: {e}"
            ) from e

    @override
    def validate_checkpoint_json(
        self, checkpoint_json: str
    ) -> ServiceNowConnectorCheckpoint:
        """Validate and parse checkpoint JSON."""
        return ServiceNowConnectorCheckpoint.model_validate_json(checkpoint_json)

    @override
    def build_dummy_checkpoint(self) -> ServiceNowConnectorCheckpoint:
        """Build initial empty checkpoint."""
        return ServiceNowConnectorCheckpoint(
            table_offsets={},
            current_table_index=0,
            has_more=True,
        )


# Development/testing entrypoint
if __name__ == "__main__":
    import os
    import time
    
    connector = ServiceNowConnector(content_type="incidents")
    connector.load_credentials({
        "servicenow_instance_url": os.environ.get("SERVICENOW_INSTANCE", ""),
        "servicenow_username": os.environ.get("SERVICENOW_USERNAME", ""),
        "servicenow_password": os.environ.get("SERVICENOW_PASSWORD", ""),
    })
    
    try:
        connector.validate_connector_settings()
        print("Connection validated successfully")
        
        current = time.time()
        one_day_ago = current - 24 * 60 * 60
        
        for doc in connector.load_from_checkpoint(
            one_day_ago,
            current,
            connector.build_dummy_checkpoint(),
        ):
            if isinstance(doc, Document):
                print(f"Document: {doc.semantic_identifier}")
                break
            elif isinstance(doc, ConnectorFailure):
                print(f"Failure: {doc.failure_message}")
                
    except Exception as e:
        print(f"Error: {e}")
