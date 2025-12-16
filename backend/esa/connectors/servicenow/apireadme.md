ServiceNow Data Model Integration Guide for ONYX
Complete Data Model Architecture & Relationship Handling
📋 Table of Contents
Understanding ServiceNow Data Models
Core Data Model Overview
Table Relationships & Reference Fields
Working with Related Records
CMDB & Configuration Items
Complex Query Patterns
Data Model-Specific Integration Patterns
Best Practices
ONYX Integration Examples
🏗️ Understanding ServiceNow Data Models
What Makes ServiceNow Data Models Complex?
ServiceNow is built on a highly relational database with:

150+ standard tables interconnected through relationships
Table inheritance (extended tables inherit fields from parent tables)
Reference fields that link records across tables
Many-to-many relationships using intermediary tables
Calculated fields based on related records
Dot-walking to traverse relationships in queries
Key Data Model Categories
According to the ServiceNow Data Model v3.4, there are 9 primary data model domains:

Organizational Data Model - Users, Groups, Departments, Locations, Companies
Task Data Model - Incidents, Problems, Changes, Requests (base table for workflow)
Service Catalog Data Model - Catalog Items, Requests, Requested Items
CMDB Data Model - Configuration Items, Relationships, Dependencies
Asset & Contract Data Model - Hardware/Software Assets, Contracts, Licenses
IT Cost Management - Cost Centers, Expense Lines, Rate Cards
SLA Data Model - Service Level Agreements, Metrics, Commitments
Knowledge Data Model - Knowledge Base Articles, Categories
Additional Models - Project Management, Discovery, Field Service, etc.
🗂️ Core Data Model Overview
1. Organizational Data Model
Purpose: Manages users, groups, organizational structure

Key Tables:

sys_user - Users
sys_user_group - Groups (Assignment groups, Teams, etc.)
cmn_department - Departments (hierarchical)
cmn_location - Locations (hierarchical)
core_company - Companies
cmn_cost_center - Cost Centers
sys_user_role - Roles
Relationships:

User (sys_user)
  ├── belongs to → Department (cmn_department)
  ├── located at → Location (cmn_location)
  ├── works for → Company (core_company)
  ├── member of → Groups (sys_user_group) [M2M: sys_user_grmember]
  ├── has → Roles (sys_user_role) [M2M: sys_user_has_role]
  └── reports to → Manager (sys_user)

Group (sys_user_group)
  ├── has members → Users (sys_user) [M2M: sys_user_grmember]
  ├── has → Roles (sys_user_role) [M2M: sys_group_has_role]
  └── parent → Group (sys_user_group) [hierarchical]
2. Task Data Model
Purpose: Base table for all workflow-related records

Key Concept: Table Inheritance

task (base table)
  ├── incident
  ├── problem
  │   └── problem_task
  ├── change_request
  │   ├── change_task
  │   └── change_phase
  ├── sc_request (Service Catalog Request)
  │   ├── sc_req_item (Requested Item)
  │   └── sc_task (Catalog Task)
  ├── pm_project (Project)
  │   └── pm_project_task
  └── planned_task
Common Fields (inherited by all extended tables):

Assigned to (sys_user)
Assignment Group (sys_user_group)
Configuration Item (cmdb_ci)
Caller (sys_user)
Location (cmn_location)
Company (core_company)
State, Priority, Impact, Urgency
Created by, Updated by, Closed by
3. CMDB Data Model
Purpose: Configuration Management Database - tracks IT infrastructure

Key Concept: Everything is a CI (Configuration Item)

Base Table: cmdb_ci

Major CI Categories:

cmdb_ci (Configuration Item)
  ├── cmdb_ci_hardware
  │   ├── cmdb_ci_computer
  │   │   ├── cmdb_ci_server
  │   │   │   ├── cmdb_ci_win_server
  │   │   │   ├── cmdb_ci_linux_server
  │   │   │   └── cmdb_ci_unix_server
  │   │   └── cmdb_ci_pc_hardware
  │   │       ├── cmdb_ci_desktop_pc
  │   │       └── cmdb_ci_laptop_pc
  │   ├── cmdb_ci_netgear
  │   │   ├── cmdb_ci_ip_router
  │   │   ├── cmdb_ci_ip_switch
  │   │   └── cmdb_ci_ip_firewall
  │   └── cmdb_ci_storage_device
  ├── cmdb_ci_appl (Application)
  │   ├── cmdb_ci_app_server
  │   ├── cmdb_ci_web_server
  │   └── cmdb_ci_db_instance
  ├── cmdb_ci_service (Business Service)
  │   └── cmdb_ci_business_process
  └── cmdb_ci_vm_instance (Virtual Machine)
      ├── cmdb_ci_vm_vmware
      └── cmdb_ci_hyper_v_instance
CI Relationships:

Runs on
Depends on
Uses
Provides DR for
Located in
Hosted on
Powered by
4. Service Catalog Data Model
Purpose: Manages service requests and catalog items

Key Tables:

sc_cat_item (Catalog Item)
  └── creates → sc_request (Request)
                  ├── contains → sc_req_item (Requested Item)
                  │               └── creates → sc_task (Catalog Task)
                  └── creates → Configuration Item (when fulfilled)
5. Asset & Contract Data Model
Purpose: Asset lifecycle management and contract tracking

Key Concept: Asset vs CI Relationship

alm_asset (Asset) ←→ cmdb_ci (Configuration Item)
  │                      │
  ├── Financial View     ├── Technical View
  ├── Cost               ├── Relationships
  ├── Purchase Date      ├── Dependencies
  ├── Warranty           └── Specifications
  └── Contract
      └── ast_contract
🔗 Table Relationships & Reference Fields
Types of Relationships
1. One-to-Many (Reference Field)
Example: Incident → Assigned User

javascript
// Incident record has assigned_to field pointing to sys_user
{
  "number": "INC0001234",
  "assigned_to": {
    "link": "https://instance.service-now.com/api/now/table/sys_user/abc123",
    "value": "abc123"  // sys_id of the user
  }
}
2. Many-to-Many (M2M Table)
Example: Users ↔ Groups (via sys_user_grmember)

javascript
// M2M relationship table
sys_user_grmember
├── user (reference to sys_user)
└── group (reference to sys_user_group)
3. Self-Referential
Example: User → Manager (both in sys_user)

javascript
{
  "name": "John Doe",
  "manager": {
    "value": "xyz789"  // sys_id of another user
  }
}
4. Hierarchical
Example: Department → Parent Department

javascript
cmn_department
├── IT Department
    ├── IT Support (parent: IT Department)
    └── IT Development (parent: IT Department)
        └── Frontend Team (parent: IT Development)
Reference Field Format
When you retrieve records with reference fields:

javascript
// Default: Returns sys_id only
{
  "assigned_to": "abc123"
}

// With display_value=true: Returns display value
{
  "assigned_to": {
    "value": "abc123",
    "display_value": "John Doe"
  }
}

// With display_value=all: Returns full details
{
  "assigned_to": {
    "value": "abc123",
    "display_value": "John Doe",
    "link": "https://instance.service-now.com/api/now/table/sys_user/abc123"
  }
}
🔍 Working with Related Records
Dot-Walking (Traversing Relationships)
Concept: Access fields from related tables using dot notation

Syntax: reference_field.field_name

Example 1: Get Incident with Caller's Email
javascript
// Query incidents and include caller's email
const incidents = await snow.get_records(
  table='incident',
  fields=['number', 'short_description', 'caller_id.email', 'caller_id.name'],
  query='active=true'
);

// Result includes fields from related user record
{
  "number": "INC0001234",
  "short_description": "Network issue",
  "caller_id": {
    "value": "abc123",
    "display_value": "John Doe"
  },
  "caller_id.email": "john.doe@company.com",
  "caller_id.name": "John Doe"
}
Example 2: Multi-Level Dot-Walking
javascript
// Get incident → assigned user → manager → email
const incidents = await snow.get_records(
  table='incident',
  fields=[
    'number',
    'assigned_to.name',
    'assigned_to.manager.name',
    'assigned_to.manager.email'
  ]
);

// Result
{
  "number": "INC0001234",
  "assigned_to.name": "John Doe",
  "assigned_to.manager.name": "Jane Smith",
  "assigned_to.manager.email": "jane.smith@company.com"
}
Example 3: Dot-Walking in Queries
javascript
// Find incidents assigned to users in specific department
const query = 'assigned_to.department.name=IT Support';

const incidents = await snow.get_records(
  table='incident',
  query=query
);

// Find incidents for CIs located in specific datacenter
const query2 = 'cmdb_ci.location.name=Datacenter 1';
Query Operators for Related Fields
javascript
// Exact match
'assigned_to.name=John Doe'

// Contains
'assigned_to.email LIKE @company.com'

// Empty/Not Empty
'assigned_to.manager ISEMPTY'
'assigned_to.manager ISNOTEMPTY'

// Multiple conditions
'assigned_to.department.name=IT^assigned_to.active=true'
🏢 CMDB & Configuration Items
Understanding CI Relationships
ServiceNow CMDB uses a relationship model to track dependencies:

Relationship Table: cmdb_rel_ci

Common Relationship Types:

Runs on::Runs
Depends on::Used by
Hosted on::Hosts
Powered by::Powers
Backed up by::Backs up
Protected by::Protects
Querying CI Relationships
Example 1: Get All CIs That Run on a Server
javascript
// Find what applications run on a specific server
const relationships = await snow.get_records(
  table='cmdb_rel_ci',
  query='child.name=PROD-SERVER-01^type.name=Runs on::Runs',
  fields=['parent.name', 'parent.sys_class_name', 'type.name']
);

// Result shows all applications running on that server
Example 2: Get CI Dependencies
python
def get_ci_dependencies(snow, ci_sys_id, depth=2):
    """
    Get all dependencies for a CI
    
    Args:
        ci_sys_id: Configuration Item sys_id
        depth: How many levels deep to traverse
    """
    dependencies = []
    
    # Get direct dependencies
    result = snow.get_records(
        table='cmdb_rel_ci',
        query=f'parent={ci_sys_id}^type.name=Depends on::Used by',
        fields=['child.name', 'child.sys_id', 'child.sys_class_name']
    )
    
    for rel in result['result']:
        dep_ci = {
            'name': rel.get('child.name'),
            'sys_id': rel.get('child.sys_id'),
            'type': rel.get('child.sys_class_name')
        }
        dependencies.append(dep_ci)
        
        # Recursive for deeper levels
        if depth > 1:
            sub_deps = get_ci_dependencies(
                snow, 
                rel['child.sys_id'], 
                depth - 1
            )
            dep_ci['dependencies'] = sub_deps
    
    return dependencies
CI Impact Analysis
When working with incidents/changes, you need to know affected services:

javascript
// Get incident and all affected services
const incident = await snow.get_record(
  table='incident',
  sys_id='incident_sys_id'
);

// Get the affected CI
const ci_sys_id = incident.result.cmdb_ci.value;

// Get all services that depend on this CI
const affected_services = await snow.get_records(
  table='cmdb_rel_ci',
  query=`child=${ci_sys_id}^parent.sys_class_name=cmdb_ci_service`,
  fields=['parent.name', 'parent.sys_id']
);
🔎 Complex Query Patterns
Pattern 1: Cross-Table Queries with Joins
Use Case: Find all incidents for servers in a specific location

javascript
const query = snow.encode_query([
  {field: 'active', operator: '=', value: 'true'},
  {field: 'cmdb_ci.sys_class_name', operator: '=', value: 'cmdb_ci_server'},
  {field: 'cmdb_ci.location.name', operator: '=', value: 'New York Office'}
]);

const incidents = await snow.get_records(
  table='incident',
  query=query,
  fields=[
    'number',
    'short_description',
    'cmdb_ci.name',
    'cmdb_ci.location.name'
  ]
);
Pattern 2: Finding Records with M2M Relationships
Use Case: Find all users in a specific group

javascript
// Method 1: Query the M2M table
const group_members = await snow.get_records(
  table='sys_user_grmember',
  query='group.name=Network Support',
  fields=['user.name', 'user.email', 'user.sys_id']
);

// Method 2: Query users directly
const users = await snow.get_records(
  table='sys_user',
  query='sys_user_grmember.group.name=Network Support',
  fields=['name', 'email', 'department.name']
);
Pattern 3: Hierarchical Queries
Use Case: Get all departments under IT Department (including sub-departments)

javascript
// Direct children only
const direct_children = await snow.get_records(
  table='cmn_department',
  query='parent.name=IT Department',
  fields=['name', 'head.name']
);

// All descendants (recursive)
function async getAllSubDepartments(snow, parent_sys_id, all_depts = []) {
  const children = await snow.get_records(
    table='cmn_department',
    query=`parent=${parent_sys_id}`,
    fields=['sys_id', 'name', 'head.name']
  );
  
  for (const dept of children.result) {
    all_depts.push(dept);
    await getAllSubDepartments(snow, dept.sys_id, all_depts);
  }
  
  return all_depts;
}
Pattern 4: Aggregate Queries with Relationships
Use Case: Count incidents by assignment group and priority

javascript
const stats = await snow.aggregate_query(
  table='incident',
  group_by=['assignment_group.name', 'priority'],
  count=true,
  avg=['calendar_duration'],
  query='active=true'
);

// Result format:
// [
//   {
//     "groupby_fields": {
//       "assignment_group.name": "Network Support",
//       "priority": "1"
//     },
//     "stats": {
//       "count": "15",
//       "avg_calendar_duration": "3600"
//     }
//   }
// ]
📊 Data Model-Specific Integration Patterns
1. Working with Task Records
Challenge: Task table is extended by many tables (incident, problem, change, etc.)

Solution: Use sysparm_display_value=all and check sys_class_name

python
class TaskManager:
    """Unified task management across all task types"""
    
    def __init__(self, connector):
        self.connector = connector
    
    def get_task_by_number(self, task_number):
        """
        Get any task by its number (INC, PRB, CHG, etc.)
        Automatically determines the correct table
        """
        # Task number prefixes
        table_map = {
            'INC': 'incident',
            'PRB': 'problem',
            'CHG': 'change_request',
            'RITM': 'sc_req_item',
            'REQ': 'sc_request',
            'TASK': 'sc_task',
            'PRJTASK': 'pm_project_task'
        }
        
        # Determine table from number prefix
        prefix = task_number.split('0')[0]
        table = table_map.get(prefix, 'task')
        
        # Get record
        result = self.connector.get_records(
            table=table,
            query=f'number={task_number}',
            limit=1
        )
        
        if result['result']:
            return result['result'][0]
        return None
    
    def get_related_tasks(self, parent_sys_id, parent_table='task'):
        """Get all child tasks of a parent task"""
        return self.connector.get_records(
            table='task',
            query=f'parent={parent_sys_id}',
            fields=[
                'number',
                'short_description',
                'sys_class_name',
                'state',
                'assigned_to.name'
            ]
        )
2. Working with Service Catalog
Challenge: Service Catalog involves multiple related tables

Pattern: Request → Requested Item → Tasks → CI

python
def process_catalog_request(snow, request_number):
    """
    Complete catalog request processing
    """
    # 1. Get the request
    request = snow.get_records(
        table='sc_request',
        query=f'number={request_number}',
        limit=1
    )
    
    if not request['result']:
        return None
    
    request_data = request['result'][0]
    request_sys_id = request_data['sys_id']
    
    # 2. Get all requested items
    requested_items = snow.get_records(
        table='sc_req_item',
        query=f'request={request_sys_id}',
        fields=[
            'number',
            'cat_item.name',
            'state',
            'configuration_item.name'
        ]
    )
    
    # 3. For each requested item, get tasks
    for item in requested_items['result']:
        item_sys_id = item['sys_id']
        
        tasks = snow.get_records(
            table='sc_task',
            query=f'request_item={item_sys_id}',
            fields=[
                'number',
                'short_description',
                'state',
                'assigned_to.name'
            ]
        )
        
        item['tasks'] = tasks['result']
    
    return {
        'request': request_data,
        'requested_items': requested_items['result']
    }
3. Working with Assets and CIs
Challenge: Assets and CIs are synchronized but separate

Pattern: Always maintain both records for hardware

python
def create_hardware_with_ci(snow, hardware_data):
    """
    Create hardware asset and corresponding CI
    Maintains the asset-CI relationship
    """
    # 1. Create the hardware asset
    asset_data = {
        'asset_tag': hardware_data['asset_tag'],
        'model': hardware_data['model_sys_id'],
        'assigned_to': hardware_data['user_sys_id'],
        'location': hardware_data['location_sys_id'],
        'cost': hardware_data['cost'],
        'purchase_date': hardware_data['purchase_date'],
        'po_number': hardware_data['po_number']
    }
    
    asset_result = snow.create_record(
        table='alm_hardware',
        data=asset_data
    )
    
    asset_sys_id = asset_result['result']['sys_id']
    
    # 2. Get the auto-created CI (synchronized)
    # Wait a moment for sync
    import time
    time.sleep(2)
    
    ci_result = snow.get_records(
        table='cmdb_ci_computer',
        query=f'asset={asset_sys_id}',
        limit=1
    )
    
    if ci_result['result']:
        ci_sys_id = ci_result['result'][0]['sys_id']
        
        # 3. Update CI with technical details
        ci_updates = {
            'os': hardware_data.get('operating_system'),
            'ram': hardware_data.get('ram'),
            'disk_space': hardware_data.get('disk_space'),
            'ip_address': hardware_data.get('ip_address')
        }
        
        snow.patch_record(
            table='cmdb_ci_computer',
            sys_id=ci_sys_id,
            data=ci_updates
        )
    
    return {
        'asset_sys_id': asset_sys_id,
        'ci_sys_id': ci_sys_id if ci_result['result'] else None
    }
4. Working with Contracts and Assets
Challenge: M2M relationship between contracts and assets

python
def link_assets_to_contract(snow, contract_sys_id, asset_sys_ids):
    """
    Link multiple assets to a contract via M2M table
    """
    results = []
    
    for asset_sys_id in asset_sys_ids:
        # Create M2M record
        m2m_data = {
            'contract': contract_sys_id,
            'ci_item': asset_sys_id
        }
        
        result = snow.create_record(
            table='clm_m2m_contract_asset',
            data=m2m_data
        )
        
        results.append(result)
    
    return results

def get_contract_assets(snow, contract_number):
    """
    Get all assets covered by a contract
    """
    # First get contract
    contract = snow.get_records(
        table='ast_contract',
        query=f'number={contract_number}',
        limit=1
    )
    
    if not contract['result']:
        return []
    
    contract_sys_id = contract['result'][0]['sys_id']
    
    # Get M2M relationships
    assets = snow.get_records(
        table='clm_m2m_contract_asset',
        query=f'contract={contract_sys_id}',
        fields=[
            'ci_item.name',
            'ci_item.asset_tag',
            'ci_item.model.name',
            'ci_item.assigned_to.name'
        ]
    )
    
    return assets['result']
✅ Best Practices
1. Always Use Display Values for References
python
# Good: Include display values
result = snow.get_records(
    table='incident',
    query='active=true',
    limit=10
)

# Better: Explicitly request display values
url_params = {
    'sysparm_display_value': 'all',  # or 'true'
    'sysparm_limit': 10
}
2. Limit Fields to What You Need
python
# Bad: Get all fields (slow, wastes bandwidth)
incidents = snow.get_records(table='incident')

# Good: Specify only needed fields
incidents = snow.get_records(
    table='incident',
    fields=[
        'number',
        'short_description',
        'assigned_to.name',
        'state'
    ]
)
3. Use Encoded Queries for Complex Conditions
python
# Build complex queries programmatically
conditions = [
    {'field': 'active', 'operator': '=', 'value': 'true'},
    {'field': 'priority', 'operator': '<=', 'value': '2'},
    {'field': 'assigned_to.department.name', 'operator': '=', 'value': 'IT Support'}
]

query = snow.encode_query(conditions)
# Result: active=true^priority<=2^assigned_to.department.name=IT Support
4. Handle Reference Fields Properly
python
def safe_get_reference(record, field_path):
    """
    Safely extract reference field values with dot-walking
    
    Args:
        record: ServiceNow record dict
        field_path: Field path with dots (e.g., 'assigned_to.manager.email')
    """
    # Handle display_value format
    if isinstance(record.get(field_path), dict):
        return record[field_path].get('display_value')
    
    # Handle simple format
    return record.get(field_path)

# Usage
assigned_user = safe_get_reference(incident, 'assigned_to')
manager_email = safe_get_reference(incident, 'assigned_to.manager.email')
5. Cache Reference Data
python
from functools import lru_cache

class ServiceNowReferenceCache:
    """Cache frequently accessed reference data"""
    
    def __init__(self, connector):
        self.connector = connector
    
    @lru_cache(maxsize=1000)
    def get_user(self, sys_id):
        """Cache user lookups"""
        result = self.connector.get_record(
            table='sys_user',
            sys_id=sys_id,
            fields=['name', 'email', 'department.name']
        )
        return result['result']
    
    @lru_cache(maxsize=500)
    def get_group(self, sys_id):
        """Cache group lookups"""
        result = self.connector.get_record(
            table='sys_user_group',
            sys_id=sys_id,
            fields=['name', 'manager.name']
        )
        return result['result']
6. Validate sys_id Before Using
python
def is_valid_sys_id(sys_id):
    """Validate ServiceNow sys_id format (32-character hex)"""
    import re
    pattern = r'^[a-f0-9]{32}$'
    return bool(re.match(pattern, sys_id))

# Usage
if is_valid_sys_id(user_sys_id):
    user = snow.get_record('sys_user', user_sys_id)
🎯 ONYX Integration Examples
Example 1: Intelligent Incident Creation with Context
python
class IntelligentIncidentCreator:
    """
    Create incidents with full context and relationships
    """
    
    def __init__(self, snow):
        self.snow = snow
    
    def create_incident_with_context(
        self,
        description: str,
        user_email: str,
        affected_service: str = None,
        affected_ci: str = None
    ):
        """
        Create incident with automatic relationship resolution
        """
        # 1. Find the user (caller)
        user = self.snow.get_records(
            table='sys_user',
            query=f'email={user_email}',
            fields=['sys_id', 'name', 'department', 'location', 'company'],
            limit=1
        )
        
        if not user['result']:
            raise ValueError(f"User not found: {user_email}")
        
        user_data = user['result'][0]
        
        # 2. Determine affected CI
        ci_sys_id = None
        if affected_ci:
            ci = self.snow.get_records(
                table='cmdb_ci',
                query=f'name={affected_ci}',
                limit=1
            )
            if ci['result']:
                ci_sys_id = ci['result'][0]['sys_id']
        
        # 3. Determine affected business service
        service_sys_id = None
        if affected_service:
            service = self.snow.get_records(
                table='cmdb_ci_service',
                query=f'name={affected_service}',
                limit=1
            )
            if service['result']:
                service_sys_id = service['result'][0]['sys_id']
        
        # 4. Find appropriate assignment group based on CI
        assignment_group = None
        if ci_sys_id:
            # Get support group for this CI
            support_groups = self.snow.get_records(
                table='cmdb_ci',
                query=f'sys_id={ci_sys_id}',
                fields=['support_group.sys_id', 'support_group.name'],
                limit=1
            )
            if support_groups['result']:
                assignment_group = support_groups['result'][0].get('support_group.sys_id')
        
        # 5. Create the incident with all context
        incident_data = {
            'short_description': description[:160],
            'description': description,
            'caller_id': user_data['sys_id'],
            'company': user_data.get('company'),
            'location': user_data.get('location'),
            'cmdb_ci': ci_sys_id,
            'business_service': service_sys_id,
            'assignment_group': assignment_group,
            'impact': '2',
            'urgency': '2',
            'category': 'Hardware' if ci_sys_id else 'Inquiry'
        }
        
        result = self.snow.create_record(
            table='incident',
            data=incident_data
        )
        
        # 6. Link affected CIs if multiple
        incident_sys_id = result['result']['sys_id']
        
        return {
            'incident_number': result['result']['number'],
            'incident_sys_id': incident_sys_id,
            'assigned_to_group': assignment_group,
            'context': {
                'caller': user_data['name'],
                'affected_ci': affected_ci,
                'affected_service': affected_service
            }
        }
Example 2: CMDB Impact Analysis
python
class CMDBImpactAnalyzer:
    """
    Analyze impact of CI changes
    """
    
    def __init__(self, snow):
        self.snow = snow
    
    def analyze_ci_impact(self, ci_name):
        """
        Analyze what would be affected if a CI goes down
        """
        # 1. Find the CI
        ci = self.snow.get_records(
            table='cmdb_ci',
            query=f'name={ci_name}',
            limit=1
        )
        
        if not ci['result']:
            return {'error': 'CI not found'}
        
        ci_sys_id = ci['result'][0]['sys_id']
        ci_data = ci['result'][0]
        
        # 2. Get all dependent CIs
        dependent_cis = self.snow.get_records(
            table='cmdb_rel_ci',
            query=f'child={ci_sys_id}',
            fields=[
                'parent.name',
                'parent.sys_class_name',
                'parent.operational_status',
                'type.name'
            ]
        )
        
        # 3. Get affected business services
        affected_services = self.snow.get_records(
            table='cmdb_rel_ci',
            query=f'child={ci_sys_id}^parent.sys_class_name=cmdb_ci_service',
            fields=['parent.name', 'parent.service_level']
        )
        
        # 4. Get users assigned to this CI
        users = self.snow.get_records(
            table='sys_user',
            query=f'u_primary_computer={ci_sys_id}',
            fields=['name', 'email', 'department.name']
        )
        
        # 5. Check for active incidents
        active_incidents = self.snow.get_records(
            table='incident',
            query=f'cmdb_ci={ci_sys_id}^active=true',
            fields=['number', 'short_description', 'state']
        )
        
        return {
            'ci_name': ci_data['name'],
            'ci_type': ci_data['sys_class_name'],
            'dependent_cis': {
                'count': len(dependent_cis.get('result', [])),
                'items': dependent_cis.get('result', [])
            },
            'affected_services': {
                'count': len(affected_services.get('result', [])),
                'items': affected_services.get('result', [])
            },
            'affected_users': {
                'count': len(users.get('result', [])),
                'items': users.get('result', [])
            },
            'active_incidents': {
                'count': len(active_incidents.get('result', [])),
                'items': active_incidents.get('result', [])
            }
        }
Example 3: Service Catalog with Fulfillment
python
class ServiceCatalogManager:
    """
    Manage complete service catalog lifecycle
    """
    
    def __init__(self, snow):
        self.snow = snow
    
    def order_catalog_item(
        self,
        catalog_item_name: str,
        requested_for_email: str,
        variables: dict = None
    ):
        """
        Order a catalog item with automatic workflow
        """
        # 1. Find catalog item
        cat_item = self.snow.get_records(
            table='sc_cat_item',
            query=f'name={catalog_item_name}^active=true',
            limit=1
        )
        
        if not cat_item['result']:
            return {'error': 'Catalog item not found'}
        
        cat_item_sys_id = cat_item['result'][0]['sys_id']
        
        # 2. Find requested_for user
        user = self.snow.get_records(
            table='sys_user',
            query=f'email={requested_for_email}',
            limit=1
        )
        
        if not user['result']:
            return {'error': 'User not found'}
        
        user_sys_id = user['result'][0]['sys_id']
        
        # 3. Create cart item
        cart_item_data = {
            'cat_item': cat_item_sys_id,
            'quantity': 1,
            'variables': variables or {}
        }
        
        cart_item = self.snow.create_record(
            table='sc_cart_item',
            data=cart_item_data
        )
        
        # 4. Submit order (creates request)
        # Note: In reality, this would use Cart API or submit action
        request_data = {
            'requested_for': user_sys_id,
            'request_state': 'pending_approval'
        }
        
        request = self.snow.create_record(
            table='sc_request',
            data=request_data
        )
        
        request_sys_id = request['result']['sys_id']
        
        # 5. Create requested item
        req_item_data = {
            'request': request_sys_id,
            'cat_item': cat_item_sys_id,
            'quantity': 1
        }
        
        req_item = self.snow.create_record(
            table='sc_req_item',
            data=req_item_data
        )
        
        return {
            'request_number': request['result']['number'],
            'requested_item_number': req_item['result']['number'],
            'status': 'submitted',
            'requested_for': user['result'][0]['name']
        }
    
    def check_fulfillment_status(self, request_number):
        """
        Check complete status of service catalog request
        """
        # Get request
        request = self.snow.get_records(
            table='sc_request',
            query=f'number={request_number}',
            limit=1
        )
        
        if not request['result']:
            return {'error': 'Request not found'}
        
        request_sys_id = request['result'][0]['sys_id']
        request_data = request['result'][0]
        
        # Get requested items
        req_items = self.snow.get_records(
            table='sc_req_item',
            query=f'request={request_sys_id}',
            fields=[
                'number',
                'cat_item.name',
                'state',
                'stage',
                'configuration_item.name'
            ]
        )
        
        # Get fulfillment tasks
        tasks = self.snow.get_records(
            table='sc_task',
            query=f'request={request_sys_id}',
            fields=[
                'number',
                'short_description',
                'state',
                'assigned_to.name',
                'closed_at'
            ]
        )
        
        return {
            'request_number': request_data['number'],
            'request_state': request_data['request_state'],
            'requested_items': req_items['result'],
            'fulfillment_tasks': tasks['result']
        }
📚 Summary
Key Takeaways
ServiceNow is Highly Relational
Most data depends on other tables
Always consider relationships when querying
Use Dot-Walking
Access related data efficiently
Reduce API calls by including related fields
Understand Table Inheritance
Task table hierarchy affects queries
Use appropriate table for specific record types
CMDB is Central
Most modules relate to Configuration Items
Track relationships for impact analysis
Reference Fields are Key
Store sys_id, display display_value
Validate sys_id format before using
M2M Relationships Need Special Handling
Use intermediary tables
Query both directions as needed
Next Steps for ONYX Integration
Map Your Use Cases to specific data models
Identify Required Relationships for each action
Build Helper Functions for common relationship patterns
Cache Reference Data to reduce API calls
Test with Real Data to verify relationships work correctly
Version: 1.0.0
Last Updated: December 2025
For: ONYX ServiceNow Integration




"""
Enhanced ServiceNow Connector with Data Model Relationship Support
====================================================================

This enhanced connector includes:
- Reference field handling and resolution
- Dot-walking support
- CMDB relationship management
- M2M relationship helpers
- Table inheritance handling
- Complex query builders

Author: ONYX Integration Team
Version: 2.0.0
"""

import requests
import json
from typing import Dict, List, Optional, Any, Union
from functools import lru_cache
import re


class ServiceNowDataModelConnector:
    """
    Enhanced ServiceNow connector with full data model support
    """
    
    def __init__(
        self,
        instance: str,
        username: str,
        password: str,
        api_version: str = "now",
        timeout: int = 30,
        verify_ssl: bool = True
    ):
        self.instance = instance.replace('.service-now.com', '')
        self.base_url = f"https://{self.instance}.service-now.com/api/{api_version}"
        self.username = username
        self.password = password
        self.timeout = timeout
        self.verify_ssl = verify_ssl
        self.session = requests.Session()
        self.session.auth = (username, password)
        self.session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })
    
    # ==================== CORE API METHODS ====================
    
    def get_records(
        self,
        table: str,
        query: Optional[str] = None,
        fields: Optional[List[str]] = None,
        limit: int = 100,
        offset: int = 0,
        order_by: Optional[str] = None,
        display_value: str = "all"
    ) -> Dict[str, Any]:
        """
        Get records with enhanced field and relationship support
        """
        params = {
            'sysparm_limit': limit,
            'sysparm_offset': offset,
            'sysparm_display_value': display_value
        }
        
        if query:
            params['sysparm_query'] = query
        if fields:
            params['sysparm_fields'] = ','.join(fields)
        if order_by:
            params['sysparm_order_by'] = order_by
        
        return self._make_request('GET', f'table/{table}', params=params)
    
    def _make_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict] = None,
        data: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Make HTTP request"""
        url = f"{self.base_url}/{endpoint}"
        
        try:
            response = self.session.request(
                method=method,
                url=url,
                params=params,
                json=data,
                timeout=self.timeout,
                verify=self.verify_ssl
            )
            response.raise_for_status()
            return response.json() if response.content else {}
        except requests.exceptions.RequestException as e:
            raise Exception(f"API Error: {str(e)}")
    
    # ==================== REFERENCE FIELD HELPERS ====================
    
    @staticmethod
    def is_valid_sys_id(sys_id: str) -> bool:
        """Validate ServiceNow sys_id format (32-char hex)"""
        if not sys_id or not isinstance(sys_id, str):
            return False
        return bool(re.match(r'^[a-f0-9]{32}$', sys_id))
    
    def extract_reference_value(self, field_data: Any) -> Optional[str]:
        """
        Extract sys_id from reference field (handles multiple formats)
        
        Args:
            field_data: Can be string (sys_id) or dict with 'value' key
        
        Returns:
            sys_id string or None
        """
        if isinstance(field_data, dict):
            return field_data.get('value')
        elif isinstance(field_data, str):
            return field_data if self.is_valid_sys_id(field_data) else None
        return None
    
    def extract_display_value(self, field_data: Any) -> Optional[str]:
        """
        Extract display value from reference field
        """
        if isinstance(field_data, dict):
            return field_data.get('display_value')
        elif isinstance(field_data, str):
            return field_data
        return None
    
    def resolve_reference(
        self,
        table: str,
        sys_id: str,
        fields: Optional[List[str]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Resolve a reference field to get the full record
        
        Args:
            table: Table name
            sys_id: Record sys_id
            fields: Fields to retrieve
        
        Returns:
            Full record or None
        """
        if not self.is_valid_sys_id(sys_id):
            return None
        
        try:
            result = self.get_records(
                table=table,
                query=f'sys_id={sys_id}',
                fields=fields,
                limit=1
            )
            return result['result'][0] if result.get('result') else None
        except:
            return None
    
    # ==================== RELATIONSHIP MANAGEMENT ====================
    
    def get_related_records(
        self,
        source_table: str,
        source_sys_id: str,
        target_table: str,
        relationship_field: str,
        fields: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Get records related via a reference field
        
        Example: Get all incidents assigned to a specific user
        """
        query = f'{relationship_field}={source_sys_id}'
        
        result = self.get_records(
            table=target_table,
            query=query,
            fields=fields
        )
        
        return result.get('result', [])
    
    def get_m2m_relationships(
        self,
        m2m_table: str,
        source_field: str,
        source_sys_id: str,
        target_field: str,
        target_table: str = None,
        fields: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Get records via many-to-many relationship
        
        Example: Get all groups a user belongs to
        
        Args:
            m2m_table: M2M table name (e.g., 'sys_user_grmember')
            source_field: Source field in M2M table (e.g., 'user')
            source_sys_id: Source record sys_id
            target_field: Target field in M2M table (e.g., 'group')
            target_table: Optional target table for field expansion
            fields: Fields to retrieve from target records
        """
        # Build field list for dot-walking
        if fields and target_table:
            expanded_fields = [f'{target_field}.{f}' for f in fields]
        else:
            expanded_fields = [target_field]
        
        result = self.get_records(
            table=m2m_table,
            query=f'{source_field}={source_sys_id}',
            fields=expanded_fields
        )
        
        return result.get('result', [])
    
    def create_m2m_relationship(
        self,
        m2m_table: str,
        source_field: str,
        source_sys_id: str,
        target_field: str,
        target_sys_id: str
    ) -> Dict[str, Any]:
        """
        Create a many-to-many relationship
        
        Example: Add user to a group
        """
        data = {
            source_field: source_sys_id,
            target_field: target_sys_id
        }
        
        return self._make_request('POST', f'table/{m2m_table}', data=data)
    
    # ==================== CMDB RELATIONSHIP METHODS ====================
    
    def get_ci_relationships(
        self,
        ci_sys_id: str,
        direction: str = "both",
        relationship_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get CI relationships
        
        Args:
            ci_sys_id: Configuration Item sys_id
            direction: 'parent', 'child', or 'both'
            relationship_type: Filter by relationship type name
        
        Returns:
            List of relationships
        """
        conditions = []
        
        if direction in ['parent', 'both']:
            parent_query = f'parent={ci_sys_id}'
            if relationship_type:
                parent_query += f'^type.name={relationship_type}'
            conditions.append(parent_query)
        
        if direction in ['child', 'both']:
            child_query = f'child={ci_sys_id}'
            if relationship_type:
                child_query += f'^type.name={relationship_type}'
            conditions.append(child_query)
        
        query = '^OR'.join(conditions) if len(conditions) > 1 else conditions[0]
        
        result = self.get_records(
            table='cmdb_rel_ci',
            query=query,
            fields=[
                'parent.name',
                'parent.sys_id',
                'parent.sys_class_name',
                'child.name',
                'child.sys_id',
                'child.sys_class_name',
                'type.name'
            ]
        )
        
        return result.get('result', [])
    
    def get_ci_dependencies(
        self,
        ci_sys_id: str,
        depth: int = 1
    ) -> Dict[str, Any]:
        """
        Get all CIs that depend on this CI (recursive)
        
        Args:
            ci_sys_id: Configuration Item sys_id
            depth: How many levels to traverse
        
        Returns:
            Tree structure of dependencies
        """
        def _get_deps_recursive(sys_id, current_depth):
            if current_depth > depth:
                return []
            
            relationships = self.get_ci_relationships(
                ci_sys_id=sys_id,
                direction='parent',
                relationship_type='Depends on::Used by'
            )
            
            deps = []
            for rel in relationships:
                child_sys_id = rel.get('child.sys_id')
                dep = {
                    'name': rel.get('child.name'),
                    'sys_id': child_sys_id,
                    'type': rel.get('child.sys_class_name'),
                    'relationship': rel.get('type.name')
                }
                
                if current_depth < depth:
                    dep['dependencies'] = _get_deps_recursive(
                        child_sys_id,
                        current_depth + 1
                    )
                
                deps.append(dep)
            
            return deps
        
        return _get_deps_recursive(ci_sys_id, 1)
    
    def get_affected_services(
        self,
        ci_sys_id: str
    ) -> List[Dict[str, Any]]:
        """
        Get all business services affected by this CI
        """
        result = self.get_records(
            table='cmdb_rel_ci',
            query=f'child={ci_sys_id}^parent.sys_class_name=cmdb_ci_service',
            fields=[
                'parent.name',
                'parent.sys_id',
                'parent.service_level',
                'parent.operational_status',
                'type.name'
            ]
        )
        
        return result.get('result', [])
    
    def create_ci_relationship(
        self,
        parent_ci_sys_id: str,
        child_ci_sys_id: str,
        relationship_type: str = "Depends on::Used by"
    ) -> Dict[str, Any]:
        """
        Create a relationship between two CIs
        
        Args:
            parent_ci_sys_id: Parent CI sys_id
            child_ci_sys_id: Child CI sys_id
            relationship_type: Relationship type name
        """
        # First, get the relationship type sys_id
        rel_type = self.get_records(
            table='cmdb_rel_type',
            query=f'name={relationship_type}',
            limit=1
        )
        
        if not rel_type.get('result'):
            raise ValueError(f"Relationship type not found: {relationship_type}")
        
        rel_type_sys_id = rel_type['result'][0]['sys_id']
        
        # Create the relationship
        data = {
            'parent': parent_ci_sys_id,
            'child': child_ci_sys_id,
            'type': rel_type_sys_id
        }
        
        return self._make_request('POST', 'table/cmdb_rel_ci', data=data)
    
    # ==================== COMPLEX QUERY BUILDERS ====================
    
    def build_query(
        self,
        conditions: List[Dict[str, str]],
        operator: str = "AND"
    ) -> str:
        """
        Build encoded query from conditions
        
        Args:
            conditions: List of condition dicts with 'field', 'operator', 'value'
            operator: Join operator ('AND' or 'OR')
        
        Example:
            conditions = [
                {'field': 'active', 'operator': '=', 'value': 'true'},
                {'field': 'priority', 'operator': '<=', 'value': '2'}
            ]
            query = build_query(conditions)
            # Result: "active=true^priority<=2"
        """
        query_parts = []
        
        for condition in conditions:
            field = condition['field']
            op = condition.get('operator', '=')
            value = condition['value']
            query_parts.append(f"{field}{op}{value}")
        
        separator = '^OR' if operator == 'OR' else '^'
        return separator.join(query_parts)
    
    def query_with_relationships(
        self,
        table: str,
        base_conditions: List[Dict[str, str]],
        related_filters: Dict[str, List[Dict[str, str]]],
        fields: Optional[List[str]] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Query with filters on related records using dot-walking
        
        Args:
            table: Main table
            base_conditions: Conditions on main table
            related_filters: Dict of reference_field: conditions
            fields: Fields to return
            limit: Max records
        
        Example:
            # Find incidents assigned to IT Support group members
            # who are located in New York
            results = query_with_relationships(
                table='incident',
                base_conditions=[
                    {'field': 'active', 'operator': '=', 'value': 'true'}
                ],
                related_filters={
                    'assigned_to': [
                        {'field': 'location.name', 'operator': '=', 'value': 'New York'}
                    ],
                    'assignment_group': [
                        {'field': 'name', 'operator': '=', 'value': 'IT Support'}
                    ]
                }
            )
        """
        all_conditions = base_conditions.copy()
        
        # Add related filters using dot-walking
        for ref_field, filters in related_filters.items():
            for filter_cond in filters:
                dot_walked_field = f"{ref_field}.{filter_cond['field']}"
                all_conditions.append({
                    'field': dot_walked_field,
                    'operator': filter_cond.get('operator', '='),
                    'value': filter_cond['value']
                })
        
        query = self.build_query(all_conditions)
        
        result = self.get_records(
            table=table,
            query=query,
            fields=fields,
            limit=limit
        )
        
        return result.get('result', [])
    
    # ==================== TABLE INHERITANCE HELPERS ====================
    
    def get_task_by_number(
        self,
        task_number: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get any task by its number, automatically determining the table
        
        Args:
            task_number: Task number (INC0001234, CHG0001234, etc.)
        
        Returns:
            Task record with actual table info
        """
        # Prefix to table mapping
        table_map = {
            'INC': 'incident',
            'PRB': 'problem',
            'CHG': 'change_request',
            'RITM': 'sc_req_item',
            'REQ': 'sc_request',
            'SCTASK': 'sc_task',
            'PRJTASK': 'pm_project_task',
            'TASK': 'task'
        }
        
        # Extract prefix
        prefix = task_number.split('0')[0]
        table = table_map.get(prefix, 'task')
        
        # Query the appropriate table
        result = self.get_records(
            table=table,
            query=f'number={task_number}',
            limit=1
        )
        
        if result.get('result'):
            record = result['result'][0]
            record['_table'] = table  # Add metadata
            return record
        
        return None
    
    def get_all_child_tasks(
        self,
        parent_sys_id: str
    ) -> List[Dict[str, Any]]:
        """
        Get all child tasks of a parent task (works across task types)
        """
        result = self.get_records(
            table='task',
            query=f'parent={parent_sys_id}',
            fields=[
                'sys_id',
                'number',
                'sys_class_name',
                'short_description',
                'state',
                'assigned_to.name'
            ]
        )
        
        return result.get('result', [])
    
    # ==================== ADVANCED FEATURES ====================
    
    def batch_resolve_references(
        self,
        records: List[Dict[str, Any]],
        reference_fields: Dict[str, str]
    ) -> List[Dict[str, Any]]:
        """
        Batch resolve reference fields in records
        
        Args:
            records: List of records with reference fields
            reference_fields: Dict of {field_name: table_name}
        
        Returns:
            Records with resolved references
        """
        # Collect all unique sys_ids per table
        to_resolve = {}
        
        for record in records:
            for field, table in reference_fields.items():
                sys_id = self.extract_reference_value(record.get(field))
                if sys_id:
                    if table not in to_resolve:
                        to_resolve[table] = set()
                    to_resolve[table].add(sys_id)
        
        # Fetch all referenced records in batches
        resolved_cache = {}
        
        for table, sys_ids in to_resolve.items():
            sys_id_list = list(sys_ids)
            query = '^OR'.join([f'sys_id={sid}' for sid in sys_id_list])
            
            result = self.get_records(
                table=table,
                query=query,
                limit=len(sys_id_list)
            )
            
            for rec in result.get('result', []):
                resolved_cache[rec['sys_id']] = rec
        
        # Enhance records with resolved data
        for record in records:
            for field, table in reference_fields.items():
                sys_id = self.extract_reference_value(record.get(field))
                if sys_id and sys_id in resolved_cache:
                    record[f'{field}_resolved'] = resolved_cache[sys_id]
        
        return records
    
    def get_hierarchical_records(
        self,
        table: str,
        root_query: Optional[str] = None,
        parent_field: str = 'parent',
        max_depth: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get hierarchical records (like department structure)
        
        Args:
            table: Table name
            root_query: Query to find root records
            parent_field: Parent reference field name
            max_depth: Maximum depth to traverse
        
        Returns:
            Flat list with depth information
        """
        all_records = []
        
        # Get root records
        root_records = self.get_records(
            table=table,
            query=root_query or f'{parent_field}ISEMPTY',
            fields=['sys_id', 'name', parent_field]
        )
        
        def get_children(parent_sys_id, depth):
            if depth > max_depth:
                return
            
            children = self.get_records(
                table=table,
                query=f'{parent_field}={parent_sys_id}',
                fields=['sys_id', 'name', parent_field]
            )
            
            for child in children.get('result', []):
                child['_depth'] = depth
                child['_parent_sys_id'] = parent_sys_id
                all_records.append(child)
                get_children(child['sys_id'], depth + 1)
        
        # Add root records
        for root in root_records.get('result', []):
            root['_depth'] = 0
            all_records.append(root)
            get_children(root['sys_id'], 1)
        
        return all_records


# ==================== USAGE EXAMPLES ====================

if __name__ == "__main__":
    # Initialize enhanced connector
    snow = ServiceNowDataModelConnector(
        instance='your-instance',
        username='your-username',
        password='your-password'
    )
    
    # Example 1: Get incidents with related data using dot-walking
    print("=== Example 1: Dot-Walking ===")
    incidents = snow.get_records(
        table='incident',
        query='active=true',
        fields=[
            'number',
            'short_description',
            'caller_id.name',
            'caller_id.email',
            'assigned_to.name',
            'assigned_to.manager.name',
            'assignment_group.name',
            'cmdb_ci.name',
            'cmdb_ci.location.name'
        ],
        limit=5
    )
    print(f"Found {len(incidents.get('result', []))} incidents")
    
    # Example 2: Get CI dependencies
    print("\n=== Example 2: CI Dependencies ===")
    ci = snow.get_records(
        table='cmdb_ci_server',
        query='name=PROD-WEB-01',
        limit=1
    )
    
    if ci.get('result'):
        ci_sys_id = ci['result'][0]['sys_id']
        dependencies = snow.get_ci_dependencies(ci_sys_id, depth=2)
        print(f"CI Dependencies: {json.dumps(dependencies, indent=2)}")
    
    # Example 3: M2M Relationships (User Groups)
    print("\n=== Example 3: User Groups ===")
    user = snow.get_records(
        table='sys_user',
        query='email=john.doe@company.com',
        limit=1
    )
    
    if user.get('result'):
        user_sys_id = user['result'][0]['sys_id']
        groups = snow.get_m2m_relationships(
            m2m_table='sys_user_grmember',
            source_field='user',
            source_sys_id=user_sys_id,
            target_field='group',
            target_table='sys_user_group',
            fields=['name', 'description']
        )
        print(f"User is member of {len(groups)} groups")
    
    # Example 4: Complex Query with Relationships
    print("\n=== Example 4: Complex Query ===")
    results = snow.query_with_relationships(
        table='incident',
        base_conditions=[
            {'field': 'active', 'operator': '=', 'value': 'true'},
            {'field': 'priority', 'operator': '<=', 'value': '2'}
        ],
        related_filters={
            'assigned_to': [
                {'field': 'department.name', 'operator': '=', 'value': 'IT Support'}
            ]
        },
        limit=10
    )
    print(f"Found {len(results)} matching incidents")
    
    # Example 5: Get Task by Number (any type)
    print("\n=== Example 5: Get Task ===")
    task = snow.get_task_by_number('INC0001234')
    if task:
        print(f"Task: {task['number']} (Type: {task['_table']})")
    
    # Example 6: Hierarchical Department Structure
    print("\n=== Example 6: Department Hierarchy ===")
    departments = snow.get_hierarchical_records(
        table='cmn_department',
        root_query='name=IT Department',
        parent_field='parent',
        max_depth=5
    )
    for dept in departments:
        indent = "  " * dept['_depth']
        print(f"{indent}- {dept['name']}")