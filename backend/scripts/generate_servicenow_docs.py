"""Script to convert ServiceNow connector documentation to DOCX format."""
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.style import WD_STYLE_TYPE
from docx.enum.table import WD_TABLE_ALIGNMENT

def create_servicenow_docs():
    doc = Document()
    
    # Set up styles
    styles = doc.styles
    
    # Title style
    title_style = doc.styles['Title']
    title_style.font.size = Pt(28)
    title_style.font.bold = True
    title_style.font.color.rgb = RGBColor(0, 51, 102)
    
    # Heading 1
    h1 = doc.styles['Heading 1']
    h1.font.size = Pt(18)
    h1.font.bold = True
    h1.font.color.rgb = RGBColor(0, 51, 102)
    
    # Heading 2
    h2 = doc.styles['Heading 2']
    h2.font.size = Pt(14)
    h2.font.bold = True
    h2.font.color.rgb = RGBColor(0, 102, 153)
    
    # Heading 3
    h3 = doc.styles['Heading 3']
    h3.font.size = Pt(12)
    h3.font.bold = True
    
    # ==================== TITLE ====================
    title = doc.add_heading('ServiceNow Connector - Technical Documentation', 0)
    
    # Metadata
    meta_para = doc.add_paragraph()
    meta_para.add_run('Version: ').bold = True
    meta_para.add_run('1.0.0\n')
    meta_para.add_run('Last Updated: ').bold = True
    meta_para.add_run('December 2024\n')
    meta_para.add_run('Status: ').bold = True
    meta_para.add_run('Production Ready (Incidents Table Tested)')
    
    doc.add_paragraph()
    
    # ==================== TABLE OF CONTENTS ====================
    doc.add_heading('Table of Contents', level=1)
    toc_items = [
        '1. Overview',
        '2. Architecture',
        '3. Module Structure',
        '4. Authentication',
        '5. Supported Content Types',
        '6. Data Flow',
        '7. API Reference',
        '8. Configuration',
        '9. Testing',
        '10. Error Handling',
        '11. Rate Limiting',
        '12. Extending the Connector'
    ]
    for item in toc_items:
        doc.add_paragraph(item, style='List Number')
    
    doc.add_page_break()
    
    # ==================== 1. OVERVIEW ====================
    doc.add_heading('1. Overview', level=1)
    
    doc.add_paragraph(
        'The ServiceNow Connector is a comprehensive integration module that connects ESA '
        '(Enterprise Search Application) to ServiceNow instances for document ingestion and indexing. '
        'It implements the ServiceNow Table API v2 following the official Zurich API specification.'
    )
    
    doc.add_heading('Key Features', level=2)
    features = [
        'Multiple Authentication Methods: OAuth 2.0 and Basic Authentication',
        'Checkpoint-Based Pagination: Reliable incremental sync with state persistence',
        'Multi-Table Support: ITSM, Knowledge, CMDB, CSM, HR, Service Catalog, Security Operations',
        'Rate Limiting: Built-in rate limiting with configurable thresholds',
        'Error Recovery: Graceful handling of inaccessible tables (ACL-based)',
        'Custom Tables: Support for extended configurations'
    ]
    for feature in features:
        p = doc.add_paragraph(style='List Bullet')
        p.add_run('✅ ' + feature)
    
    doc.add_heading('Current Testing Status', level=2)
    
    status_table = doc.add_table(rows=6, cols=3)
    status_table.style = 'Table Grid'
    
    headers = ['Module', 'Status', 'Notes']
    header_cells = status_table.rows[0].cells
    for i, header in enumerate(headers):
        header_cells[i].text = header
        header_cells[i].paragraphs[0].runs[0].bold = True
    
    status_data = [
        ('Incidents', '✅ Tested', 'Full integration verified'),
        ('Problems', '🔲 Pending', 'Table mapping configured'),
        ('Changes', '🔲 Pending', 'Table mapping configured'),
        ('Knowledge', '🔲 Pending', 'Table mapping configured'),
        ('CMDB', '🔲 Pending', 'Table mapping configured'),
    ]
    
    for i, (module, status, notes) in enumerate(status_data, 1):
        row = status_table.rows[i].cells
        row[0].text = module
        row[1].text = status
        row[2].text = notes
    
    doc.add_page_break()
    
    # ==================== 2. ARCHITECTURE ====================
    doc.add_heading('2. Architecture', level=1)
    
    doc.add_paragraph('The connector follows a layered architecture:')
    
    arch_text = '''
┌─────────────────────────────────────────────────────────────────┐
│                    ESA Indexing Engine                          │
└─────────────────────┬───────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────────┐
│                 ServiceNowConnector                              │
│  (connector.py)                                                  │
│  • load_credentials()      - Initialize client with creds       │
│  • load_from_checkpoint()  - Paginated document fetching        │
│  • validate_connector_settings() - Connection validation        │
└─────────────────────┬───────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────────┐
│              EnhancedServiceNowClient                            │
│  (enhanced_client.py)                                            │
│  • get_records_enhanced()  - Flexible record fetching           │
│  • get_task_by_number()    - Polymorphic task lookup            │
│  • get_ci_dependencies()   - Recursive CMDB traversal           │
└─────────────────────┬───────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────────┐
│                   TableAPIClient                                 │
│  (table_api.py)                                                  │
│  • get_records()           - CRUD operations                    │
│  • get_records_paginated() - Auto-pagination iterator           │
│  • fetch_table_records()   - Legacy compat method               │
└─────────────────────┬───────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────────┐
│                 BaseServiceNowClient                             │
│  (base_client.py)                                                │
│  • Session management with connection pooling                   │
│  • OAuth 2.0 token management (automatic refresh)               │
│  • Rate limiting with exponential backoff                       │
│  • Retry logic (3 attempts by default)                          │
└─────────────────────┬───────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────────┐
│              ServiceNow REST API (Zurich v2)                     │
│  Endpoint: /api/now/v2/table/{tableName}                        │
└─────────────────────────────────────────────────────────────────┘
'''
    
    arch_para = doc.add_paragraph()
    arch_run = arch_para.add_run(arch_text)
    arch_run.font.name = 'Courier New'
    arch_run.font.size = Pt(8)
    
    doc.add_page_break()
    
    # ==================== 3. MODULE STRUCTURE ====================
    doc.add_heading('3. Module Structure', level=1)
    
    doc.add_paragraph('The connector package is organized as follows:')
    
    structure = '''esa/connectors/servicenow/
├── __init__.py              # Package initialization
├── connector.py             # Main connector class (ESA interface)
├── base_client.py           # Base HTTP client with auth/retry/rate-limiting
├── table_api.py             # Table API operations (CRUD)
├── enhanced_client.py       # Enhanced data model operations
├── client.py                # Legacy simple client (for reference)
├── aggregate_api.py         # Aggregate/Stats API
├── attachment_api.py        # Attachment handling
├── batch_api.py             # Batch operations
├── cmdb_api.py              # CMDB-specific operations
├── csm_api.py               # Customer Service Management
├── import_set_api.py        # Import Set operations
├── itsm_api.py              # ITSM-specific operations
├── knowledge_api.py         # Knowledge Management
├── service_catalog_api.py   # Service Catalog operations
├── asset_management_api.py  # Asset management
└── apireadme.md             # ServiceNow Data Model Guide'''
    
    struct_para = doc.add_paragraph()
    struct_run = struct_para.add_run(structure)
    struct_run.font.name = 'Courier New'
    struct_run.font.size = Pt(9)
    
    doc.add_heading('Core Files Description', level=2)
    
    files_table = doc.add_table(rows=5, cols=2)
    files_table.style = 'Table Grid'
    
    files_data = [
        ('File', 'Purpose'),
        ('connector.py', 'Main entry point - Implements ESA connector interfaces (CheckpointedConnector, SlimConnectorWithPermSync)'),
        ('base_client.py', 'Foundation layer - HTTP session, authentication, rate limiting, error handling'),
        ('table_api.py', 'Table operations - Full CRUD with pagination, query building, field configuration'),
        ('enhanced_client.py', 'Advanced features - Dot-walking, polymorphic lookups, CMDB relationships'),
    ]
    
    for i, (file, purpose) in enumerate(files_data):
        row = files_table.rows[i].cells
        row[0].text = file
        row[1].text = purpose
        if i == 0:
            row[0].paragraphs[0].runs[0].bold = True
            row[1].paragraphs[0].runs[0].bold = True
    
    doc.add_page_break()
    
    # ==================== 4. AUTHENTICATION ====================
    doc.add_heading('4. Authentication', level=1)
    
    doc.add_paragraph('The connector supports two authentication methods:')
    
    doc.add_heading('Basic Authentication', level=2)
    
    basic_auth_code = '''credentials = {
    "servicenow_instance_url": "https://dev314000.service-now.com",
    "servicenow_username": "admin",
    "servicenow_password": "your_password"
}'''
    
    p = doc.add_paragraph()
    run = p.add_run(basic_auth_code)
    run.font.name = 'Courier New'
    run.font.size = Pt(9)
    
    doc.add_paragraph('Implementation: Uses HTTP Basic Auth header via requests library.')
    
    doc.add_heading('OAuth 2.0 (Recommended for Production)', level=2)
    
    oauth_code = '''credentials = {
    "servicenow_instance_url": "https://your-instance.service-now.com",
    "servicenow_username": "service_account",
    "servicenow_password": "account_password",
    "servicenow_client_id": "your_client_id",
    "servicenow_client_secret": "your_client_secret"
}'''
    
    p = doc.add_paragraph()
    run = p.add_run(oauth_code)
    run.font.name = 'Courier New'
    run.font.size = Pt(9)
    
    doc.add_heading('OAuth Implementation Details', level=3)
    oauth_details = [
        'Grant Type: password (Resource Owner Password Credentials)',
        'Token Endpoint: {instance_url}/oauth_token.do',
        'Auto-refresh: Tokens refresh 60 seconds before expiry',
        'Token caching: Access tokens cached in memory'
    ]
    for detail in oauth_details:
        doc.add_paragraph(detail, style='List Bullet')
    
    doc.add_page_break()
    
    # ==================== 5. SUPPORTED CONTENT TYPES ====================
    doc.add_heading('5. Supported Content Types', level=1)
    
    doc.add_paragraph('The connector maps content types to ServiceNow tables:')
    
    doc.add_heading('ITSM (IT Service Management)', level=2)
    
    itsm_table = doc.add_table(rows=7, cols=3)
    itsm_table.style = 'Table Grid'
    
    itsm_data = [
        ('Content Type', 'Table(s)', 'Description'),
        ('incidents', 'incident', 'IT incidents'),
        ('problems', 'problem', 'Problem records'),
        ('changes', 'change_request', 'Change requests'),
        ('requests', 'sc_request, sc_req_item', 'Service requests'),
        ('tasks', 'task, sc_task', 'Generic tasks'),
        ('all_itsm', 'Multiple', 'All ITSM tables'),
    ]
    
    for i, row_data in enumerate(itsm_data):
        row = itsm_table.rows[i].cells
        for j, cell_data in enumerate(row_data):
            row[j].text = cell_data
            if i == 0:
                row[j].paragraphs[0].runs[0].bold = True
    
    doc.add_heading('Knowledge Management', level=2)
    
    kb_table = doc.add_table(rows=3, cols=3)
    kb_table.style = 'Table Grid'
    
    kb_data = [
        ('Content Type', 'Table(s)', 'Description'),
        ('knowledge', 'kb_knowledge', 'Knowledge articles'),
        ('all_knowledge', 'kb_knowledge', 'All knowledge content'),
    ]
    
    for i, row_data in enumerate(kb_data):
        row = kb_table.rows[i].cells
        for j, cell_data in enumerate(row_data):
            row[j].text = cell_data
            if i == 0:
                row[j].paragraphs[0].runs[0].bold = True
    
    doc.add_heading('CMDB (Configuration Management Database)', level=2)
    
    cmdb_table = doc.add_table(rows=8, cols=3)
    cmdb_table.style = 'Table Grid'
    
    cmdb_data = [
        ('Content Type', 'Table(s)', 'Description'),
        ('cmdb_servers', 'cmdb_ci_server', 'Server CIs'),
        ('cmdb_computers', 'cmdb_ci_computer', 'Computer CIs'),
        ('cmdb_applications', 'cmdb_ci_appl', 'Application CIs'),
        ('cmdb_services', 'cmdb_ci_service', 'Service CIs'),
        ('cmdb_hardware', 'cmdb_ci_hardware', 'Hardware CIs'),
        ('cmdb_all', 'cmdb_ci', 'All CIs (base table)'),
    ]
    
    for i, row_data in enumerate(cmdb_data):
        row = cmdb_table.rows[i].cells
        for j, cell_data in enumerate(row_data):
            row[j].text = cell_data
            if i == 0:
                row[j].paragraphs[0].runs[0].bold = True
    
    doc.add_heading('Customer Service Management (CSM)', level=2)
    
    csm_table = doc.add_table(rows=5, cols=3)
    csm_table.style = 'Table Grid'
    
    csm_data = [
        ('Content Type', 'Table(s)', 'Description'),
        ('csm_cases', 'sn_customerservice_case', 'Customer cases'),
        ('csm_accounts', 'customer_account', 'Customer accounts'),
        ('csm_contacts', 'customer_contact', 'Customer contacts'),
        ('csm_all', 'Multiple', 'All CSM tables'),
    ]
    
    for i, row_data in enumerate(csm_data):
        row = csm_table.rows[i].cells
        for j, cell_data in enumerate(row_data):
            row[j].text = cell_data
            if i == 0:
                row[j].paragraphs[0].runs[0].bold = True
    
    doc.add_heading('HR Service Delivery', level=2)
    hr_items = [
        'hr_cases → sn_hr_core_case (HR cases)',
        'hr_tasks → sn_hr_core_task (HR tasks)',
        'hr_all → Multiple (All HR tables)'
    ]
    for item in hr_items:
        doc.add_paragraph(item, style='List Bullet')
    
    doc.add_heading('Service Catalog', level=2)
    catalog_items = [
        'catalog_items → sc_cat_item (Catalog items)',
        'catalog_categories → sc_category (Categories)',
        'catalog_all → Multiple (All catalog content)'
    ]
    for item in catalog_items:
        doc.add_paragraph(item, style='List Bullet')
    
    doc.add_heading('Security Operations', level=2)
    security_items = [
        'security_incidents → sn_si_incident (Security incidents)',
        'security_vulnerabilities → sn_vul_vulnerable_item (Vulnerabilities)',
        'security_all → Multiple (All security content)'
    ]
    for item in security_items:
        doc.add_paragraph(item, style='List Bullet')
    
    doc.add_page_break()
    
    # ==================== 6. DATA FLOW ====================
    doc.add_heading('6. Data Flow', level=1)
    
    doc.add_heading('Document Ingestion Flow', level=2)
    
    flow_steps = [
        ('Step 1: Connector Initialization', 'ServiceNowConnector(content_type="incidents")'),
        ('Step 2: Credential Loading', 'connector.load_credentials({...}) → Creates EnhancedServiceNowClient'),
        ('Step 3: Connection Validation', 'connector.validate_connector_settings() → Fetches 1 record from incident table'),
        ('Step 4: Document Fetching', 'connector.load_from_checkpoint(start, end, checkpoint) → Paginated fetching'),
        ('Step 5: Document Conversion', '_record_to_document(record, table_name) → Converts to ESA Document format'),
    ]
    
    for step, desc in flow_steps:
        p = doc.add_paragraph()
        p.add_run(step + ': ').bold = True
        p.add_run(desc)
    
    doc.add_heading('Checkpoint Structure', level=2)
    
    checkpoint_code = '''class ServiceNowConnectorCheckpoint(ConnectorCheckpoint):
    """Tracks pagination state across multiple tables."""
    
    table_offsets: dict[str, int]    # Offset per table
    current_table_index: int          # Current table in list
    has_more: bool                    # More data available'''
    
    p = doc.add_paragraph()
    run = p.add_run(checkpoint_code)
    run.font.name = 'Courier New'
    run.font.size = Pt(9)
    
    doc.add_heading('Example Checkpoint State', level=3)
    
    checkpoint_example = '''{
  "table_offsets": {
    "incident": 200,
    "problem": 0
  },
  "current_table_index": 0,
  "has_more": true
}'''
    
    p = doc.add_paragraph()
    run = p.add_run(checkpoint_example)
    run.font.name = 'Courier New'
    run.font.size = Pt(9)
    
    doc.add_page_break()
    
    # ==================== 7. API REFERENCE ====================
    doc.add_heading('7. API Reference', level=1)
    
    doc.add_heading('ServiceNowConnector (Main Class)', level=2)
    
    connector_api = '''class ServiceNowConnector:
    
    def __init__(
        self,
        content_type: str = "all_itsm",
        custom_tables: str | None = None,
        calls_per_minute: int = 600,
    ) -> None:
        """Initialize connector.
        
        Args:
            content_type: Type of content to index
            custom_tables: Comma-separated list of additional tables
            calls_per_minute: API rate limit
        """
    
    def load_credentials(self, credentials: dict) -> None:
        """Load ServiceNow credentials and initialize client."""
    
    def validate_connector_settings(self) -> None:
        """Validate credentials and connectivity."""
    
    def load_from_checkpoint(self, start, end, checkpoint):
        """Load documents with checkpoint-based pagination."""
    
    def retrieve_all_slim_docs_perm_sync(self, ...):
        """Retrieve slim documents for permission sync."""
    
    def build_dummy_checkpoint(self):
        """Build initial empty checkpoint."""'''
    
    p = doc.add_paragraph()
    run = p.add_run(connector_api)
    run.font.name = 'Courier New'
    run.font.size = Pt(8)
    
    doc.add_heading('EnhancedServiceNowClient', level=2)
    
    enhanced_api = '''class EnhancedServiceNowClient(TableAPIClient):
    
    def get_records_enhanced(self, table, query=None, fields=None, 
                             limit=100, offset=0, display_value="all"):
        """Get records with flexible configuration."""
    
    def get_task_by_number(self, task_number: str):
        """Get any task by number, auto-determining table."""
    
    def get_ci_dependencies(self, ci_sys_id, depth=1, direction="parent"):
        """Get CI dependencies recursively."""
    
    def batch_resolve_references(self, records, reference_fields):
        """Batch resolve reference fields."""'''
    
    p = doc.add_paragraph()
    run = p.add_run(enhanced_api)
    run.font.name = 'Courier New'
    run.font.size = Pt(8)
    
    doc.add_heading('TableAPIClient', level=2)
    
    table_api = '''class TableAPIClient(BaseServiceNowClient):
    
    def get_records(self, table_name, offset=0, limit=100, query=None, 
                   fields=None, display_value="all"):
        """Fetch records from a table."""
    
    def get_record(self, table_name, sys_id):
        """Get a single record by sys_id."""
    
    def create_record(self, table_name, data):
        """Create a new record."""
    
    def update_record(self, table_name, sys_id, data):
        """Update a record (PATCH)."""
    
    def delete_record(self, table_name, sys_id):
        """Delete a record."""
    
    def fetch_table_records(self, table_name, offset=0, limit=100, 
                           updated_after=None):
        """Fetch records with has_more indicator."""'''
    
    p = doc.add_paragraph()
    run = p.add_run(table_api)
    run.font.name = 'Courier New'
    run.font.size = Pt(8)
    
    doc.add_page_break()
    
    # ==================== 8. CONFIGURATION ====================
    doc.add_heading('8. Configuration', level=1)
    
    doc.add_heading('Environment Variables', level=2)
    
    env_vars = '''# Required
SERVICENOW_INSTANCE=https://your-instance.service-now.com
SERVICENOW_USERNAME=service_account
SERVICENOW_PASSWORD=password

# Optional (OAuth)
SERVICENOW_CLIENT_ID=your_client_id
SERVICENOW_CLIENT_SECRET=your_client_secret'''
    
    p = doc.add_paragraph()
    run = p.add_run(env_vars)
    run.font.name = 'Courier New'
    run.font.size = Pt(9)
    
    doc.add_heading('Connector Configuration in ESA', level=2)
    
    esa_config = '''Connector Type: servicenow
Content Type: incidents  # or "all_itsm", "knowledge", etc.
Custom Tables: ""        # Optional comma-separated list

Credentials:
  servicenow_instance_url: "https://your-instance.service-now.com"
  servicenow_username: "service_account"
  servicenow_password: "password"
  # Optional OAuth
  servicenow_client_id: "client_id"
  servicenow_client_secret: "client_secret"'''
    
    p = doc.add_paragraph()
    run = p.add_run(esa_config)
    run.font.name = 'Courier New'
    run.font.size = Pt(9)
    
    doc.add_page_break()
    
    # ==================== 9. TESTING ====================
    doc.add_heading('9. Testing', level=1)
    
    doc.add_heading('Test Files Location', level=2)
    
    test_files = '''backend/tests/servicenow/
├── test_servicenow_clients.py      # Unit tests for clients
├── verify_connector_orchestration.py  # Integration test
└── debug_connector_logic.py        # Debug/development script

backend/scripts/
├── test_servicenow_live.py         # Live API testing
└── test_servicenow_catalog.py      # Service Catalog testing'''
    
    p = doc.add_paragraph()
    run = p.add_run(test_files)
    run.font.name = 'Courier New'
    run.font.size = Pt(9)
    
    doc.add_heading('Running Tests', level=2)
    
    doc.add_paragraph('Unit Tests:', style='List Bullet')
    p = doc.add_paragraph()
    run = p.add_run('python -m pytest tests/servicenow/test_servicenow_clients.py -v')
    run.font.name = 'Courier New'
    run.font.size = Pt(9)
    
    doc.add_paragraph('Integration Tests:', style='List Bullet')
    p = doc.add_paragraph()
    run = p.add_run('python tests/servicenow/verify_connector_orchestration.py')
    run.font.name = 'Courier New'
    run.font.size = Pt(9)
    
    doc.add_heading('Test Results Summary (Current)', level=2)
    
    test_table = doc.add_table(rows=6, cols=3)
    test_table.style = 'Table Grid'
    
    test_data = [
        ('Test', 'Result', 'Notes'),
        ('EnhancedServiceNowClient connection', '✅ Pass', 'Basic auth verified'),
        ('Incident table fetch', '✅ Pass', 'Records retrieved successfully'),
        ('Knowledge articles fetch', '✅ Pass', 'KB articles accessible'),
        ('Full connector pipeline', '✅ Pass', 'Documents generated correctly'),
        ('Checkpoint pagination', '✅ Pass', 'State maintained across calls'),
    ]
    
    for i, row_data in enumerate(test_data):
        row = test_table.rows[i].cells
        for j, cell_data in enumerate(row_data):
            row[j].text = cell_data
            if i == 0:
                row[j].paragraphs[0].runs[0].bold = True
    
    doc.add_page_break()
    
    # ==================== 10. ERROR HANDLING ====================
    doc.add_heading('10. Error Handling', level=1)
    
    doc.add_heading('Exception Hierarchy', level=2)
    
    exceptions = '''ServiceNowAPIError                # Base exception
├── ServiceNowAuthError           # 401 - Authentication failed
├── ServiceNowPermissionError     # 403 - Insufficient permissions
├── ServiceNowNotFoundError       # 404 - Resource not found
├── ServiceNowRateLimitError      # 429 - Rate limit exceeded
├── ServiceNowConflictError       # 409 - Concurrent update conflict
├── ServiceNowValidationError     # 400 - Bad request
└── ServiceNowServerError         # 5xx - Server errors'''
    
    p = doc.add_paragraph()
    run = p.add_run(exceptions)
    run.font.name = 'Courier New'
    run.font.size = Pt(9)
    
    doc.add_heading('Error Recovery Behavior', level=2)
    
    error_table = doc.add_table(rows=6, cols=2)
    error_table.style = 'Table Grid'
    
    error_data = [
        ('Error', 'Behavior'),
        ('401 Auth Failed', 'Clear OAuth token, raise CredentialExpiredError'),
        ('403 Permission Denied', 'Skip table, log warning, continue with next table'),
        ('404 Not Found', 'Skip table (plugin not installed), continue'),
        ('429 Rate Limited', 'Wait Retry-After seconds, retry'),
        ('5xx Server Error', 'Retry with exponential backoff (3 attempts)'),
    ]
    
    for i, row_data in enumerate(error_data):
        row = error_table.rows[i].cells
        for j, cell_data in enumerate(row_data):
            row[j].text = cell_data
            if i == 0:
                row[j].paragraphs[0].runs[0].bold = True
    
    doc.add_page_break()
    
    # ==================== 11. RATE LIMITING ====================
    doc.add_heading('11. Rate Limiting', level=1)
    
    doc.add_heading('Default Configuration', level=2)
    doc.add_paragraph('DEFAULT_RATE_LIMIT = 30 requests per minute (conservative)')
    
    doc.add_heading('ServiceNow Rate Limits (per Zurich docs)', level=2)
    
    rate_table = doc.add_table(rows=3, cols=2)
    rate_table.style = 'Table Grid'
    
    rate_data = [
        ('Instance Type', 'Limit'),
        ('Personal Developer', '1,800 requests/hour/user'),
        ('Enterprise', '7,200 requests/hour/user'),
    ]
    
    for i, row_data in enumerate(rate_data):
        row = rate_table.rows[i].cells
        for j, cell_data in enumerate(row_data):
            row[j].text = cell_data
            if i == 0:
                row[j].paragraphs[0].runs[0].bold = True
    
    doc.add_heading('429 Response Handling', level=2)
    
    rate_code = '''if response.status_code == 429:
    retry_after = int(response.headers.get("Retry-After", "60"))
    logger.warning(f"Rate limited, waiting {retry_after}s")
    time.sleep(retry_after)
    return self.request(...)  # Retry'''
    
    p = doc.add_paragraph()
    run = p.add_run(rate_code)
    run.font.name = 'Courier New'
    run.font.size = Pt(9)
    
    doc.add_page_break()
    
    # ==================== 12. EXTENDING THE CONNECTOR ====================
    doc.add_heading('12. Extending the Connector', level=1)
    
    doc.add_heading('Adding New Content Types', level=2)
    
    doc.add_paragraph('1. Update CONTENT_TYPE_TABLES in connector.py:')
    
    extend_code1 = '''CONTENT_TYPE_TABLES = {
    # Existing types...
    
    # Add new type
    "my_custom_type": ["custom_table_1", "custom_table_2"],
}'''
    
    p = doc.add_paragraph()
    run = p.add_run(extend_code1)
    run.font.name = 'Courier New'
    run.font.size = Pt(9)
    
    doc.add_paragraph('2. Add table configuration in table_api.py:')
    
    extend_code2 = '''TABLE_CONFIGS = {
    # Existing configs...
    
    "custom_table_1": {
        "fields": "sys_id,name,description,state,sys_updated_on",
        "display_field": "name",
        "order_by": "sys_updated_on",
    },
}'''
    
    p = doc.add_paragraph()
    run = p.add_run(extend_code2)
    run.font.name = 'Courier New'
    run.font.size = Pt(9)
    
    doc.add_heading('Adding New API Clients', level=2)
    
    new_client_code = '''# new_api.py
from esa.connectors.servicenow.base_client import BaseServiceNowClient

class NewAPIClient(BaseServiceNowClient):
    """Client for ServiceNow New API."""
    
    def custom_operation(self, **kwargs):
        """Implement custom API logic."""
        endpoint = f"{self.api_version}/new_api/action"
        return self.get(endpoint, params=kwargs)'''
    
    p = doc.add_paragraph()
    run = p.add_run(new_client_code)
    run.font.name = 'Courier New'
    run.font.size = Pt(9)
    
    doc.add_page_break()
    
    # ==================== APPENDIX ====================
    doc.add_heading('Appendix', level=1)
    
    doc.add_heading('ServiceNow Table Reference', level=2)
    
    ref_table = doc.add_table(rows=8, cols=3)
    ref_table.style = 'Table Grid'
    
    ref_data = [
        ('Table', 'Description', 'Common Fields'),
        ('incident', 'IT Incidents', 'number, short_description, state, priority'),
        ('problem', 'Problem records', 'number, short_description, known_error'),
        ('change_request', 'Change requests', 'number, type, risk, state'),
        ('kb_knowledge', 'Knowledge articles', 'number, text, workflow_state'),
        ('cmdb_ci', 'Configuration Items', 'name, operational_status'),
        ('sys_user', 'Users', 'user_name, name, email'),
        ('sys_user_group', 'Groups', 'name, manager'),
    ]
    
    for i, row_data in enumerate(ref_data):
        row = ref_table.rows[i].cells
        for j, cell_data in enumerate(row_data):
            row[j].text = cell_data
            if i == 0:
                row[j].paragraphs[0].runs[0].bold = True
    
    doc.add_heading('Document ID Format', level=2)
    doc.add_paragraph('servicenow_{table_name}_{sys_id}')
    doc.add_paragraph('Example: servicenow_incident_abc123def456...')
    
    doc.add_heading('URL Format', level=2)
    doc.add_paragraph('{instance_url}/nav_to.do?uri={table_name}.do?sys_id={sys_id}')
    doc.add_paragraph('Example: https://dev314000.service-now.com/nav_to.do?uri=incident.do?sys_id=abc123')
    
    doc.add_heading('References', level=2)
    refs = [
        'ServiceNow REST API (Zurich) - https://developer.servicenow.com/dev.do#!/reference/api',
        'Table API Documentation - https://developer.servicenow.com/dev.do#!/reference/api/vancouver/rest/c_TableAPI',
        'ServiceNow Data Model - https://docs.servicenow.com/bundle/vancouver-platform-administration/page/administer/field-administration/concept/c_SystemDictionary.html'
    ]
    for ref in refs:
        doc.add_paragraph(ref, style='List Bullet')
    
    # Save the document
    doc.save('f:/Onyx-servicenow/Onyx/backend/esa/connectors/servicenow/ServiceNow_Connector_Technical_Documentation.docx')
    print("✅ Document created successfully!")

if __name__ == "__main__":
    create_servicenow_docs()
