"""ServiceNow Enhanced Data Model Client.

Implements the advanced patterns described in apireadme.md including:
- Dot-walking and deep reference resolution
- Polymorphic task lookups (INC/CHG/PRB -> correct table)
- Recursive CMDB dependency traversal
- Hierarchical record fetching
- Batch reference resolution

Reference: apireadme.md "ServiceNow Data Model Connector"
"""

import re
from typing import Any, Iterator, Optional

from esa.connectors.servicenow.table_api import TableAPIClient
from esa.utils.logger import setup_logger

logger = setup_logger()


class EnhancedServiceNowClient(TableAPIClient):
    """Enhanced ServiceNow Connector with Data Model Relationship Support.
    
    Provides high-level abstractions over the core Table/CMDB APIs to handle
    ServiceNow's complex relational data model.
    """

    # Valid sys_id regex (32 hex chars)
    SYS_ID_PATTERN = re.compile(r'^[a-f0-9]{32}$')

    # Task number prefix to table mapping
    TASK_PREFIX_MAP = {
        'INC': 'incident',
        'PRB': 'problem',
        'CHG': 'change_request',
        'RITM': 'sc_req_item',
        'REQ': 'sc_request',
        'SCTASK': 'sc_task',
        'PRJTASK': 'pm_project_task',
        'TASK': 'task'
    }

    # ==================== CORE EXTENSIONS ====================

    def get_records_enhanced(
        self,
        table: str,
        query: str | None = None,
        fields: list[str] | None = None,
        limit: int = 100,
        offset: int = 0,
        order_by: str | None = None,
        display_value: str = "all",
    ) -> dict[str, Any]:
        """Get records with flexible configuration (wrapper around Table API).
        
        Args:
            table: Table name
            query: Encoded query string
            fields: List of fields to retrieve
            limit: Maximum records
            offset: Starting offset
            order_by: Field to order by
            display_value: 'true', 'false', or 'all' (default 'all' for rich context)
            
        Returns:
            Dictionary containing 'result' list
        """
        params: dict[str, Any] = {
            "sysparm_limit": limit,
            "sysparm_offset": offset,
            "sysparm_display_value": display_value,
        }
        
        if query:
            params["sysparm_query"] = query
        if fields:
            params["sysparm_fields"] = ",".join(fields)
        if order_by:
            params["sysparm_order_by"] = order_by
            
        endpoint = f"{self.api_version}/table/{table}"
        return self.get(endpoint, params=params)

    # ==================== REFERENCE HELPERS ====================

    @classmethod
    def is_valid_sys_id(cls, sys_id: str) -> bool:
        """Validate ServiceNow sys_id format."""
        if not sys_id or not isinstance(sys_id, str):
            return False
        return bool(cls.SYS_ID_PATTERN.match(sys_id))

    def extract_reference_value(self, field_data: Any) -> str | None:
        """Extract sys_id from a reference field (handles string or dict)."""
        if isinstance(field_data, dict):
            return field_data.get('value')
        elif isinstance(field_data, str):
            value = field_data
            # If it looks like a link, extract sys_id at the end
            if "/" in value and "api/now/table" in value:
                 return value.split("/")[-1]
            return value if self.is_valid_sys_id(value) else None
        return None
    
    def resolve_reference(
        self,
        table: str,
        sys_id: str,
        fields: list[str] | None = None,
    ) -> dict[str, Any] | None:
        """Resolve a specific reference to get the full record."""
        if not self.is_valid_sys_id(sys_id):
            return None
            
        try:
            # Reuse base get method
            params: dict[str, Any] = {"sysparm_limit": 1}
            if fields:
                params["sysparm_fields"] = ",".join(fields)
            
            endpoint = f"{self.api_version}/table/{table}/{sys_id}"
            response = self.get(endpoint, params=params)
            return response.get("result")
        except Exception as e:
            logger.warning(f"Failed to resolve reference {table}/{sys_id}: {e}")
            return None

    def batch_resolve_references(
        self,
        records: list[dict[str, Any]],
        reference_fields: dict[str, str],
    ) -> list[dict[str, Any]]:
        """Batch resolve reference fields for a list of records.
        
        Args:
            records: List of records containing reference fields
            reference_fields: Map of {field_name: target_table_name}
            
        Returns:
            Records with added '{field}_resolved' keys containing full objects
        """
        if not records:
            return []

        # 1. Collect unique sys_ids per table
        to_resolve: dict[str, set[str]] = {}
        
        for record in records:
            for field, table in reference_fields.items():
                val = record.get(field)
                sys_id = self.extract_reference_value(val)
                if sys_id:
                    if table not in to_resolve:
                        to_resolve[table] = set()
                    to_resolve[table].add(sys_id)
        
        # 2. Fetch records in batches
        resolved_cache: dict[str, dict[str, Any]] = {}
        
        for table, sys_ids in to_resolve.items():
            sys_id_list = list(sys_ids)
            # Fetch in chunks of 50 to avoid URL length issues
            for i in range(0, len(sys_id_list), 50):
                chunk = sys_id_list[i:i+50]
                query = "^OR".join([f"sys_id={sid}" for sid in chunk])
                
                # We need to make a raw get_records call here
                # Using our enhanced method
                batch_result = self.get_records_enhanced(
                    table=table,
                    query=query,
                    limit=len(chunk)
                )
                
                for rec in batch_result.get("result", []):
                    resolved_cache[rec["sys_id"]] = rec
        
        # 3. Enhance original records
        for record in records:
            for field, _ in reference_fields.items():
                val = record.get(field)
                sys_id = self.extract_reference_value(val)
                if sys_id and sys_id in resolved_cache:
                    record[f"{field}_resolved"] = resolved_cache[sys_id]
                    
        return records

    # ==================== POLYMORPHIC HELPERS ====================

    def get_task_by_number(self, task_number: str) -> dict[str, Any] | None:
        """Get any task by its number, automatically determining the table.
        
        Args:
            task_number: e.g. INC001234, CHG005678
            
        Returns:
            Task record with added '_table' metadata
        """
        # Extract prefix (letters before numbers)
        match = re.match(r'^([A-Z]+)', task_number)
        prefix = match.group(1) if match else ""
        
        table = self.TASK_PREFIX_MAP.get(prefix, 'task')
        
        result = self.get_records_enhanced(
            table=table,
            query=f"number={task_number}",
            limit=1
        )
        
        records = result.get("result", [])
        if records:
            record = records[0]
            record["_table"] = table
            return record
            
        return None

    # ==================== RELATIONSHIPS & DOT-WALKING ====================

    def build_dot_walk_query(
        self,
        base_conditions: list[dict[str, str]],
        related_filters: dict[str, list[dict[str, str]]],
    ) -> str:
        """Build an encoded query supporting dot-walking.
        
        Args:
            base_conditions: List of dicts {'field', 'operator', 'value'}
            related_filters: Dict {ref_field: [conditions]}
            
        Returns:
            Encoded query string
        """
        query_parts = []
        
        # Add base conditions
        for cond in base_conditions:
            query_parts.append(f"{cond['field']}{cond.get('operator', '=')}{cond['value']}")
            
        # Add related filters (dot-walking)
        for ref_field, filters in related_filters.items():
            for cond in filters:
                dot_field = f"{ref_field}.{cond['field']}"
                query_parts.append(f"{dot_field}{cond.get('operator', '=')}{cond['value']}")
                
        return "^".join(query_parts)

    def get_related_records(
        self,
        source_table: str,
        source_sys_id: str,
        target_table: str,
        relationship_field: str,
        fields: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """Get records related via a simple reference field.
        
        e.g. Get all Incidents (target) where Caller (relationship_field) is User X (source).
        """
        return self.get_records_enhanced(
            table=target_table,
            query=f"{relationship_field}={source_sys_id}",
            fields=fields
        ).get("result", [])

    def get_m2m_relationships(
        self,
        m2m_table: str,
        source_field: str,
        source_sys_id: str,
        target_field: str,
        fields: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """Get records via many-to-many table.
        
        Args:
            m2m_table: e.g. sys_user_grmember
            source_field: e.g. user
            source_sys_id: sys_id of the user
            target_field: e.g. group
            fields: fields to fetch from the target table (dot-walked)
        """
        # If fields requested, we need to dot-walk the target field
        # e.g. fields=['name'] -> sysparm_fields=group.name
        query_fields = None
        if fields:
            query_fields = [f"{target_field}.{f}" for f in fields]
            
        return self.get_records_enhanced(
            table=m2m_table,
            query=f"{source_field}={source_sys_id}",
            fields=query_fields
        ).get("result", [])

    # ==================== CMDB RECURSION ====================

    def get_ci_dependencies(
        self,
        ci_sys_id: str,
        depth: int = 1,
        direction: str = "parent", # 'parent' means "depends on" usually
    ) -> list[dict[str, Any]]:
        """Get CI dependencies recursively.
        
        Args:
            ci_sys_id: Starting CI
            depth: Traversal depth
            direction: 'parent' (upstream) or 'child' (downstream)
            
        Returns:
            Nested list/tree of dependencies
        """
        if depth <= 0:
            return []
            
        # Determine query based on direction
        # cmdb_rel_ci has 'parent' (The CI that is depended on) and 'child' (The dependent)
        # Type "Depends on::Used by": Parent depends on Child? No, usually Child Depends on Parent.
        # Wait, ServiceNow standard: 
        # Parent triggers Child? No. 
        # Standard: Tomcat (Child) Runs on Server (Parent).
        # So if we want what Server supports, we look for Children where Server is Parent.
        # If we want what Tomcat depends on, we look for Parents where Tomcat is Child.
        
        # Let's trust the apireadme example: 
        # "Get all CIs that depend on this CI" -> query='parent={ci_sys_id}'... wait.
        # If parent=Server, and type=Runs on, then Child=Tomcat.
        # So finding children of Parent=Server gives us things running on it (Dependents).
        
        query = f"parent={ci_sys_id}" if direction == "downstream" else f"child={ci_sys_id}"
        if direction == "upstream": 
             # We want to find what this CI depends on.
             # So this CI is the Child. We want the Parents.
             target_field = "parent"
             match_field = "child"
        else:
            # We want to find what depends on this CI.
            # So this CI is the Parent. We want the Children.
            target_field = "child"
            match_field = "parent"

        result = self.get_records_enhanced(
            table="cmdb_rel_ci",
            query=f"{match_field}={ci_sys_id}",
            fields=[
                f"{target_field}.name", 
                f"{target_field}.sys_id", 
                f"{target_field}.sys_class_name",
                "type.name"
            ]
        )
        
        rels = result.get("result", [])
        dependencies = []
        
        for rel in rels:
            target_sys_id = self.extract_reference_value(rel.get(target_field))
            if not target_sys_id:
                continue
                
            item = {
                "name": self.extract_display_value(rel.get(target_field)) or rel.get(f"{target_field}.name"),
                "sys_id": target_sys_id,
                "class": rel.get(f"{target_field}.sys_class_name"),
                "relationship_type": self.extract_display_value(rel.get("type")) or rel.get("type.name"),
            }
            
            # Recursive call
            if depth > 1:
                item["dependencies"] = self.get_ci_dependencies(
                    target_sys_id, 
                    depth - 1, 
                    direction
                )
            
            dependencies.append(item)
            
        return dependencies

    def extract_display_value(self, field_data: Any) -> str | None:
        """Extract display value from reference field."""
        if isinstance(field_data, dict):
            return field_data.get('display_value')
        return None

    # ==================== HIERARCHY ====================

    def get_hierarchical_records(
        self,
        table: str,
        root_query: str,
        parent_field: str = "parent",
        max_depth: int = 5,
    ) -> list[dict[str, Any]]:
        """Get hierarchical records (tree structure flat list)."""
        all_records = []
        
        # Get roots
        roots = self.get_records_enhanced(
            table=table,
            query=root_query,
            fields=["sys_id", "name", "label", parent_field]
        ).get("result", [])
        
        def fetch_children(parent_id: str, depth: int):
            if depth > max_depth:
                return
            
            children = self.get_records_enhanced(
                table=table,
                query=f"{parent_field}={parent_id}",
                fields=["sys_id", "name", "label", parent_field]
            ).get("result", [])
            
            for child in children:
                child["_depth"] = depth
                child["_parent"] = parent_id
                all_records.append(child)
                fetch_children(child["sys_id"], depth + 1)
        
        for root in roots:
            root["_depth"] = 0
            all_records.append(root)
            fetch_children(root["sys_id"], 1)
            
        return all_records
