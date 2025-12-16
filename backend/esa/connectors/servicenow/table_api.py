"""ServiceNow Table API Client.

Implements the ServiceNow Table API (v2) for CRUD operations on any table.
This is the foundational API for most ServiceNow integrations.

Reference: ServiceNow Zurich REST API - Table API
Endpoint: /api/now/{version}/table/{tableName}
"""

from typing import Any, Iterator

from esa.connectors.servicenow.base_client import (
    BaseServiceNowClient,
    ServiceNowAPIError,
)
from esa.utils.logger import setup_logger

logger = setup_logger()


class TableAPIClient(BaseServiceNowClient):
    """ServiceNow Table API Client.
    
    Provides full CRUD operations on any ServiceNow table with:
    - Pagination with sysparm_offset/sysparm_limit
    - Query filtering with encoded queries
    - Field selection with sysparm_fields
    - Display value options
    - Reference link expansion
    """

    # Common table configurations with optimal field selections
    TABLE_CONFIGS: dict[str, dict[str, Any]] = {
        # ITSM Core
        "incident": {
            "fields": "sys_id,number,short_description,description,state,priority,urgency,impact,category,subcategory,assigned_to,assignment_group,caller_id,opened_by,opened_at,resolved_at,resolved_by,closed_at,close_code,close_notes,work_notes,sys_updated_on,sys_created_on",
            "display_field": "number",
            "order_by": "sys_updated_on",
        },
        "problem": {
            "fields": "sys_id,number,short_description,description,state,priority,category,assigned_to,assignment_group,opened_by,opened_at,resolved_at,resolved_by,known_error,workaround,fix,sys_updated_on,sys_created_on",
            "display_field": "number",
            "order_by": "sys_updated_on",
        },
        "change_request": {
            "fields": "sys_id,number,short_description,description,state,type,risk,impact,category,priority,assigned_to,assignment_group,requested_by,opened_at,start_date,end_date,work_start,work_end,cab_date,cab_recommendation,implementation_plan,backout_plan,test_plan,sys_updated_on,sys_created_on",
            "display_field": "number",
            "order_by": "sys_updated_on",
        },
        "change_task": {
            "fields": "sys_id,number,short_description,description,state,priority,assigned_to,assignment_group,change_request,planned_start_date,planned_end_date,sys_updated_on,sys_created_on",
            "display_field": "number",
            "order_by": "sys_updated_on",
        },
        "sc_request": {
            "fields": "sys_id,number,short_description,description,request_state,stage,requested_for,opened_by,opened_at,delivery_address,special_instructions,sys_updated_on,sys_created_on",
            "display_field": "number",
            "order_by": "sys_updated_on",
        },
        "sc_req_item": {
            "fields": "sys_id,number,short_description,description,state,stage,cat_item,request,quantity,price,recurring_price,opened_at,backordered,sys_updated_on,sys_created_on",
            "display_field": "number",
            "order_by": "sys_updated_on",
        },
        "sc_task": {
            "fields": "sys_id,number,short_description,description,state,priority,assigned_to,assignment_group,request_item,opened_at,sys_updated_on,sys_created_on",
            "display_field": "number",
            "order_by": "sys_updated_on",
        },
        "task": {
            "fields": "sys_id,number,short_description,description,state,priority,assigned_to,assignment_group,opened_by,opened_at,sys_class_name,parent,sys_updated_on,sys_created_on",
            "display_field": "number",
            "order_by": "sys_updated_on",
        },
        "task_sla": {
            "fields": "sys_id,task,sla,stage,start_time,end_time,pause_time,business_pause_duration,original_breach_time,planned_end_time,has_breached,sys_updated_on",
            "display_field": "sys_id",
            "order_by": "sys_updated_on",
        },
        
        # Knowledge Management
        "kb_knowledge": {
            "fields": "sys_id,number,short_description,text,wiki,author,kb_knowledge_base,kb_category,topic,workflow_state,published,valid_to,rating,sys_view_count,article_type,sys_created_on,sys_updated_on",
            "display_field": "number",
            "order_by": "sys_updated_on",
        },
        "kb_knowledge_base": {
            "fields": "sys_id,title,description,owner,manager,kb_version,active,sys_updated_on",
            "display_field": "title",
            "order_by": "sys_updated_on",
        },
        "kb_category": {
            "fields": "sys_id,label,description,parent,kb_knowledge_base,active,full_category,sys_updated_on",
            "display_field": "label",
            "order_by": "sys_updated_on",
        },
        "kb_feedback": {
            "fields": "sys_id,article,user,rating,comments,flagged,sys_created_on",
            "display_field": "sys_id",
            "order_by": "sys_created_on",
        },
        
        # CMDB Configuration Items
        "cmdb_ci": {
            "fields": "sys_id,name,short_description,sys_class_name,operational_status,install_status,asset_tag,serial_number,manufacturer,vendor,model_id,location,department,assigned_to,supported_by,support_group,owned_by,managed_by,sys_updated_on,sys_created_on",
            "display_field": "name",
            "order_by": "sys_updated_on",
        },
        "cmdb_ci_server": {
            "fields": "sys_id,name,short_description,ip_address,dns_domain,os,os_version,os_service_pack,manufacturer,model_id,serial_number,cpu_count,cpu_type,cpu_speed,ram,disk_space,virtual,object_id,classification,operational_status,install_status,sys_updated_on,sys_created_on",
            "display_field": "name",
            "order_by": "sys_updated_on",
        },
        "cmdb_ci_vm_instance": {
            "fields": "sys_id,name,short_description,ip_address,dns_domain,vcenter_uuid,object_id,state,cpus,memory,disks_size,os,vm_inst_id,sys_updated_on,sys_created_on",
            "display_field": "name",
            "order_by": "sys_updated_on",
        },
        "cmdb_ci_computer": {
            "fields": "sys_id,name,short_description,ip_address,mac_address,os,os_version,manufacturer,model_id,serial_number,cpu_type,cpu_count,ram,disk_space,form_factor,sys_updated_on,sys_created_on",
            "display_field": "name",
            "order_by": "sys_updated_on",
        },
        "cmdb_ci_appl": {
            "fields": "sys_id,name,short_description,version,vendor,used_for,install_status,operational_status,running_process,running_process_command,sys_updated_on,sys_created_on",
            "display_field": "name",
            "order_by": "sys_updated_on",
        },
        "cmdb_ci_service": {
            "fields": "sys_id,name,short_description,service_classification,service_status,operational_status,busines_criticality,owned_by,managed_by,sys_updated_on,sys_created_on",
            "display_field": "name",
            "order_by": "sys_updated_on",
        },
        "cmdb_ci_service_auto": {
            "fields": "sys_id,name,short_description,service_classification,service_status,operational_status,owned_by,managed_by,url,sys_updated_on,sys_created_on",
            "display_field": "name",
            "order_by": "sys_updated_on",
        },
        "cmdb_ci_hardware": {
            "fields": "sys_id,name,short_description,asset_tag,serial_number,manufacturer,model_id,install_status,hardware_status,hardware_substatus,sys_updated_on,sys_created_on",
            "display_field": "name",
            "order_by": "sys_updated_on",
        },
        "cmdb_ci_network_adapter": {
            "fields": "sys_id,name,ip_address,mac_address,netmask,cmdb_ci,dhcp_enabled,sys_updated_on",
            "display_field": "name",
            "order_by": "sys_updated_on",
        },
        "cmdb_ci_db_instance": {
            "fields": "sys_id,name,short_description,type,version,port,tcp_port,host,install_status,operational_status,sys_updated_on,sys_created_on",
            "display_field": "name",
            "order_by": "sys_updated_on",
        },
        "cmdb_ci_cloud_service_account": {
            "fields": "sys_id,name,account_id,object_id,datacenter_type,datacenter_url,sys_updated_on,sys_created_on",
            "display_field": "name",
            "order_by": "sys_updated_on",
        },
        "cmdb_rel_ci": {
            "fields": "sys_id,parent,child,type,connection_strength,sys_updated_on",
            "display_field": "sys_id",
            "order_by": "sys_updated_on",
        },
        
        # Customer Service Management (CSM)
        "sn_customerservice_case": {
            "fields": "sys_id,number,short_description,description,state,priority,contact,account,consumer,asset,product,opened_at,opened_by,closed_at,closed_by,escalation,resolution_code,resolved_at,knowledge,sys_updated_on,sys_created_on",
            "display_field": "number",
            "order_by": "sys_updated_on",
        },
        "customer_contact": {
            "fields": "sys_id,name,first_name,last_name,email,phone,mobile_phone,account,title,department,time_zone,active,sys_updated_on,sys_created_on",
            "display_field": "name",
            "order_by": "sys_updated_on",
        },
        "customer_account": {
            "fields": "sys_id,name,account_code,number,industry,street,city,state,zip,country,phone,fax,website,customer,vendor,partner,active,sys_updated_on,sys_created_on",
            "display_field": "name",
            "order_by": "sys_updated_on",
        },
        "csm_consumer": {
            "fields": "sys_id,name,first_name,last_name,email,phone,mobile_phone,user,active,sys_updated_on,sys_created_on",
            "display_field": "name",
            "order_by": "sys_updated_on",
        },
        
        # HR Service Delivery
        "sn_hr_core_case": {
            "fields": "sys_id,number,short_description,description,state,hr_service,subject_person,opened_for,opened_by,assigned_to,assignment_group,opened_at,closed_at,hr_case_type,sys_updated_on,sys_created_on",
            "display_field": "number",
            "order_by": "sys_updated_on",
        },
        "sn_hr_core_task": {
            "fields": "sys_id,number,short_description,description,state,priority,assigned_to,assignment_group,parent,due_date,opened_at,closed_at,sys_updated_on,sys_created_on",
            "display_field": "number",
            "order_by": "sys_updated_on",
        },
        "sn_hr_le_case": {
            "fields": "sys_id,number,short_description,description,state,assigned_to,assignment_group,opened_for,opened_by,opened_at,confidential,sys_updated_on,sys_created_on",
            "display_field": "number",
            "order_by": "sys_updated_on",
        },
        
        # Service Catalog
        "sc_cat_item": {
            "fields": "sys_id,name,short_description,description,category,sc_catalogs,active,price,recurring_price,type,workflow,delivery_plan,order,sys_updated_on,sys_created_on",
            "display_field": "name",
            "order_by": "sys_updated_on",
        },
        "sc_category": {
            "fields": "sys_id,title,description,parent,sc_catalog,active,header_icon,icon,location,sys_updated_on",
            "display_field": "title",
            "order_by": "sys_updated_on",
        },
        "sc_catalog": {
            "fields": "sys_id,title,description,active,manager,desktop_image,desktop_home_page,sys_updated_on",
            "display_field": "title",
            "order_by": "sys_updated_on",
        },
        "sc_cat_item_producer": {
            "fields": "sys_id,name,short_description,description,category,table_name,script,active,sys_updated_on,sys_created_on",
            "display_field": "name",
            "order_by": "sys_updated_on",
        },
        
        # Security Operations
        "sn_si_incident": {
            "fields": "sys_id,number,short_description,description,state,severity,priority,category,subcategory,assigned_to,assignment_group,opened_at,closed_at,attack_vector,business_impact,sys_updated_on,sys_created_on",
            "display_field": "number",
            "order_by": "sys_updated_on",
        },
        "sn_vul_vulnerable_item": {
            "fields": "sys_id,vulnerability,cmdb_ci,risk_score,state,first_found,last_found,remediation_date,exception_date,sys_updated_on",
            "display_field": "sys_id",
            "order_by": "sys_updated_on",
        },
        "sn_vul_entry": {
            "fields": "sys_id,cve_id,summary,description,severity,cvss_score,published_date,solution,references,sys_updated_on,sys_created_on",
            "display_field": "cve_id",
            "order_by": "sys_updated_on",
        },
        "sn_ti_observable": {
            "fields": "sys_id,value,type,source,confidence,first_seen,last_seen,active,sys_updated_on,sys_created_on",
            "display_field": "value",
            "order_by": "sys_updated_on",
        },
        
        # Asset Management
        "alm_asset": {
            "fields": "sys_id,display_name,asset_tag,serial_number,model,model_category,ci,cost,install_status,substatus,assigned_to,assigned,location,department,company,sys_updated_on,sys_created_on",
            "display_field": "display_name",
            "order_by": "sys_updated_on",
        },
        "alm_hardware": {
            "fields": "sys_id,display_name,asset_tag,serial_number,model,manufacturer,ci,install_status,substatus,assigned_to,location,department,sys_updated_on,sys_created_on",
            "display_field": "display_name",
            "order_by": "sys_updated_on",
        },
        "alm_consumable": {
            "fields": "sys_id,display_name,model,quantity,cost,cost_center,location,vendor,sys_updated_on,sys_created_on",
            "display_field": "display_name",
            "order_by": "sys_updated_on",
        },
        
        # Software Asset Management
        "samp_sw_install": {
            "fields": "sys_id,display_name,software_model,installed_on,discovery_model,last_scanned,install_date,version,edition,sys_updated_on",
            "display_field": "display_name",
            "order_by": "sys_updated_on",
        },
        "samp_entitlement_result": {
            "fields": "sys_id,software_model,license_type,rights,installs,allocated,compliance_status,sys_updated_on",
            "display_field": "sys_id",
            "order_by": "sys_updated_on",
        },
        
        # Project Portfolio Management
        "pm_project": {
            "fields": "sys_id,number,short_description,description,state,phase,priority,project_manager,start_date,end_date,percent_complete,budget_cost,cost,sys_updated_on,sys_created_on",
            "display_field": "number",
            "order_by": "sys_updated_on",
        },
        "pm_project_task": {
            "fields": "sys_id,number,short_description,description,state,priority,assigned_to,parent,top_task,start_date,end_date,percent_complete,planned_hours,actual_hours,sys_updated_on,sys_created_on",
            "display_field": "number",
            "order_by": "sys_updated_on",
        },
        "pm_resource_plan": {
            "fields": "sys_id,resource,project,planned_hours,planned_start_date,planned_end_date,state,sys_updated_on",
            "display_field": "sys_id",
            "order_by": "sys_updated_on",
        },
        
        # Contracts
        "ast_contract": {
            "fields": "sys_id,number,short_description,description,vendor,contract_administrator,starts,ends,contract_type,state,total_amount,sys_updated_on,sys_created_on",
            "display_field": "number",
            "order_by": "sys_updated_on",
        },
        "clm_agreement": {
            "fields": "sys_id,number,short_description,description,type,state,effective_date,expiration_date,contract_value,vendor,sys_updated_on,sys_created_on",
            "display_field": "number",
            "order_by": "sys_updated_on",
        },
        
        # Users and Groups
        "sys_user": {
            "fields": "sys_id,user_name,name,first_name,last_name,email,title,department,manager,company,location,phone,mobile_phone,time_zone,active,locked_out,vip,sys_updated_on",
            "display_field": "name",
            "order_by": "sys_updated_on",
        },
        "sys_user_group": {
            "fields": "sys_id,name,description,manager,email,type,active,parent,include_members,sys_updated_on",
            "display_field": "name",
            "order_by": "sys_updated_on",
        },
        "sys_user_grmember": {
            "fields": "sys_id,user,group,sys_updated_on",
            "display_field": "sys_id",
            "order_by": "sys_updated_on",
        },
        "sys_user_role": {
            "fields": "sys_id,name,description,elevated_privilege,assignable_by,sys_updated_on",
            "display_field": "name",
            "order_by": "sys_updated_on",
        },
        
        # Locations
        "cmn_location": {
            "fields": "sys_id,name,full_name,street,city,state,zip,country,latitude,longitude,parent,company,contact,phone,time_zone,sys_updated_on",
            "display_field": "name",
            "order_by": "sys_updated_on",
        },
        "cmn_building": {
            "fields": "sys_id,name,location,floors,street,city,state,zip,country,sys_updated_on",
            "display_field": "name",
            "order_by": "sys_updated_on",
        },
        
        # Company
        "core_company": {
            "fields": "sys_id,name,stock_symbol,street,city,state,zip,country,phone,fax,website,customer,vendor,manufacturer,parent,sys_updated_on",
            "display_field": "name",
            "order_by": "sys_updated_on",
        },
        
        # Notifications
        "sys_email": {
            "fields": "sys_id,type,recipients,subject,body_text,body,instance,mailbox,sent,sys_created_on",
            "display_field": "subject",
            "order_by": "sys_created_on",
        },
        
        # Audit and Logging
        "sys_audit": {
            "fields": "sys_id,tablename,documentkey,fieldname,oldvalue,newvalue,user,sys_created_on",
            "display_field": "sys_id",
            "order_by": "sys_created_on",
        },
        "syslog": {
            "fields": "sys_id,source,message,level,sys_created_on",
            "display_field": "sys_id",
            "order_by": "sys_created_on",
        },
    }

    def get_table_config(self, table_name: str) -> dict[str, Any]:
        """Get configuration for a table."""
        return self.TABLE_CONFIGS.get(table_name, {
            "fields": "sys_id,number,short_description,description,state,sys_updated_on,sys_created_on",
            "display_field": "number",
            "order_by": "sys_updated_on",
        })
    
    def get_records(
        self,
        table_name: str,
        offset: int = 0,
        limit: int = 100,
        query: str | None = None,
        fields: str | None = None,
        order_by: str | None = None,
        order_dir: str = "asc",
        display_value: str = "all",
        exclude_reference_link: bool = False,
        suppress_pagination_header: bool = False,
    ) -> tuple[list[dict[str, Any]], int | None]:
        """Fetch records from a ServiceNow table.
        
        Args:
            table_name: Name of the table
            offset: Starting record index (sysparm_offset)
            limit: Maximum records to return (sysparm_limit)
            query: Encoded query string (sysparm_query)
            fields: Comma-separated field names (sysparm_fields)
            order_by: Field to order by
            order_dir: Order direction (asc/desc)
            display_value: Display value option (true/false/all)
            exclude_reference_link: Exclude reference links from response
            suppress_pagination_header: Suppress X-Total-Count header
            
        Returns:
            Tuple of (records list, total count or None)
        """
        config = self.get_table_config(table_name)
        
        params: dict[str, Any] = {
            "sysparm_limit": limit,
            "sysparm_offset": offset,
            "sysparm_fields": fields or config.get("fields", ""),
            "sysparm_display_value": display_value,
        }
        
        # Build query with ordering
        query_parts = []
        if query:
            query_parts.append(query)
        
        effective_order = order_by or config.get("order_by", "sys_updated_on")
        order_prefix = "ORDERBYDESC" if order_dir == "desc" else "ORDERBY"
        query_parts.append(f"{order_prefix}{effective_order}")
        
        if query_parts:
            params["sysparm_query"] = "^".join(query_parts)
        
        if exclude_reference_link:
            params["sysparm_exclude_reference_link"] = "true"
        
        if suppress_pagination_header:
            params["sysparm_suppress_pagination_header"] = "true"
        
        endpoint = f"{self.api_version}/table/{table_name}"
        response = self.get(endpoint, params=params)
        
        records = response.get("result", [])
        
        # Total count from header (if available)
        total_count = None
        # Note: In actual implementation, we'd get this from response headers
        
        return records, total_count
    
    def get_records_paginated(
        self,
        table_name: str,
        query: str | None = None,
        fields: str | None = None,
        limit: int = 100,
        max_records: int | None = None,
        updated_after: float | None = None,
    ) -> Iterator[dict[str, Any]]:
        """Iterate through all records with automatic pagination.
        
        Args:
            table_name: Name of the table
            query: Encoded query string
            fields: Comma-separated field names
            limit: Page size
            max_records: Maximum total records to fetch
            updated_after: Unix timestamp filter
            
        Yields:
            Individual records
        """
        offset = 0
        count = 0
        
        # Add updated_after to query
        final_query = query or ""
        if updated_after:
            import time as time_module
            dt_str = time_module.strftime("%Y-%m-%d %H:%M:%S", time_module.gmtime(updated_after))
            filter_clause = f"sys_updated_on>{dt_str}"
            if final_query:
                final_query = f"{filter_clause}^{final_query}"
            else:
                final_query = filter_clause
        
        while True:
            records, _ = self.get_records(
                table_name=table_name,
                offset=offset,
                limit=limit,
                query=final_query,
                fields=fields,
            )
            
            if not records:
                break
            
            for record in records:
                yield record
                count += 1
                if max_records and count >= max_records:
                    return
            
            if len(records) < limit:
                break
            
            offset += limit
    
    def get_record(
        self,
        table_name: str,
        sys_id: str,
        fields: str | None = None,
        display_value: str = "all",
    ) -> dict[str, Any]:
        """Get a single record by sys_id.
        
        Args:
            table_name: Name of the table
            sys_id: Record sys_id
            fields: Comma-separated field names
            display_value: Display value option
            
        Returns:
            Record data
        """
        config = self.get_table_config(table_name)
        
        params: dict[str, Any] = {
            "sysparm_fields": fields or config.get("fields", ""),
            "sysparm_display_value": display_value,
        }
        
        endpoint = f"{self.api_version}/table/{table_name}/{sys_id}"
        response = self.get(endpoint, params=params)
        
        return response.get("result", {})
    
    def create_record(
        self,
        table_name: str,
        data: dict[str, Any],
        fields: str | None = None,
        display_value: str = "all",
    ) -> dict[str, Any]:
        """Create a new record.
        
        Args:
            table_name: Name of the table
            data: Record data
            fields: Fields to return in response
            display_value: Display value option
            
        Returns:
            Created record data
        """
        params: dict[str, Any] = {
            "sysparm_display_value": display_value,
        }
        if fields:
            params["sysparm_fields"] = fields
        
        endpoint = f"{self.api_version}/table/{table_name}"
        response = self.post(endpoint, json_data=data, params=params)
        
        return response.get("result", {})
    
    def update_record(
        self,
        table_name: str,
        sys_id: str,
        data: dict[str, Any],
        fields: str | None = None,
        display_value: str = "all",
    ) -> dict[str, Any]:
        """Update a record (PATCH - partial update).
        
        Args:
            table_name: Name of the table
            sys_id: Record sys_id
            data: Fields to update
            fields: Fields to return in response
            display_value: Display value option
            
        Returns:
            Updated record data
        """
        params: dict[str, Any] = {
            "sysparm_display_value": display_value,
        }
        if fields:
            params["sysparm_fields"] = fields
        
        endpoint = f"{self.api_version}/table/{table_name}/{sys_id}"
        response = self.patch(endpoint, json_data=data, params=params)
        
        return response.get("result", {})
    
    def replace_record(
        self,
        table_name: str,
        sys_id: str,
        data: dict[str, Any],
        fields: str | None = None,
        display_value: str = "all",
    ) -> dict[str, Any]:
        """Replace a record (PUT - full replacement).
        
        Args:
            table_name: Name of the table
            sys_id: Record sys_id
            data: Complete record data
            fields: Fields to return in response
            display_value: Display value option
            
        Returns:
            Replaced record data
        """
        params: dict[str, Any] = {
            "sysparm_display_value": display_value,
        }
        if fields:
            params["sysparm_fields"] = fields
        
        endpoint = f"{self.api_version}/table/{table_name}/{sys_id}"
        response = self.put(endpoint, json_data=data, params=params)
        
        return response.get("result", {})
    
    def delete_record(self, table_name: str, sys_id: str) -> bool:
        """Delete a record.
        
        Args:
            table_name: Name of the table
            sys_id: Record sys_id
            
        Returns:
            True if deleted successfully
        """
        endpoint = f"{self.api_version}/table/{table_name}/{sys_id}"
        self.delete(endpoint)
        return True
    
    def build_query(
        self,
        conditions: list[tuple[str, str, Any]] | None = None,
        encoded_query: str | None = None,
    ) -> str:
        """Build an encoded query string.
        
        Args:
            conditions: List of (field, operator, value) tuples
            encoded_query: Pre-encoded query string to append
            
        Returns:
            Encoded query string
            
        Operators:
            =, !=, <, >, <=, >=, LIKE, STARTSWITH, ENDSWITH,
            CONTAINS, IN, NOT IN, ISEMPTY, ISNOTEMPTY,
            SAMEAS, NSAMEAS, INSTANCEOF
        """
        parts = []
        
        if conditions:
            for field, operator, value in conditions:
                if operator.upper() in ("IN", "NOT IN"):
                    # Handle IN operator
                    if isinstance(value, (list, tuple)):
                        value = ",".join(str(v) for v in value)
                    parts.append(f"{field}{operator}{value}")
                elif operator.upper() in ("ISEMPTY", "ISNOTEMPTY"):
                    parts.append(f"{field}{operator}")
                else:
                    parts.append(f"{field}{operator}{value}")
        
        if encoded_query:
            parts.append(encoded_query)
        
        return "^".join(parts)
    
    def build_record_url(self, table_name: str, sys_id: str) -> str:
        """Build a URL to view a record in the ServiceNow UI."""
        return f"{self.instance_url}/nav_to.do?uri={table_name}.do%3Fsys_id%3D{sys_id}"

    def fetch_table_records(
        self,
        table_name: str,
        offset: int = 0,
        limit: int = 100,
        updated_after: float | None = None,
        custom_query: str | None = None,
        fields: str | None = None,
    ) -> tuple[list[dict[str, Any]], bool]:
        """Fetch records from a ServiceNow table (Legacy Compat).
        
        Args:
            table_name: ServiceNow table name
            offset: Starting record index
            limit: Maximum records to return
            updated_after: Unix timestamp to filter by sys_updated_on
            custom_query: Additional query conditions
            fields: Override default fields
            
        Returns:
            Tuple of (records list, has_more boolean)
        """
        # Build query
        query_parts = []
        
        # Add updated_after filter
        if updated_after:
            import time
            dt_str = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(updated_after))
            query_parts.append(f"sys_updated_on>{dt_str}")
        
        # Add custom query
        if custom_query:
            query_parts.append(custom_query)
            
        full_query = "^".join(query_parts) if query_parts else None
        
        # Use new get_records method
        records, _ = self.get_records(
            table_name=table_name,
            offset=offset,
            limit=limit,
            query=full_query,
            fields=fields,
            display_value="all", # Legacy client used all
            suppress_pagination_header=True
        )
        
        has_more = len(records) == limit
        return records, has_more
