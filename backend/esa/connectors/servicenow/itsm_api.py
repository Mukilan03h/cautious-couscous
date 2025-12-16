"""ServiceNow ITSM APIs Client.

Implements specialized ITSM APIs for incident, problem, change,
and service request management with enhanced functionality.

Reference: ServiceNow Zurich REST API
- Change Management API: /api/sn_chg_rest/change
- Alarm Management Open API: /api/now/v1/em
"""

from typing import Any, Iterator
from dataclasses import dataclass
from datetime import datetime

from esa.connectors.servicenow.base_client import BaseServiceNowClient
from esa.utils.logger import setup_logger

logger = setup_logger()


@dataclass
class ChangeSchedule:
    """Change request scheduling information."""
    start_date: datetime | None
    end_date: datetime | None
    work_start: datetime | None
    work_end: datetime | None
    cab_date: datetime | None


class ITSMAPIClient(BaseServiceNowClient):
    """ServiceNow ITSM API Client.
    
    Provides enhanced ITSM functionality beyond basic Table API:
    - Change Management API with scheduling
    - Standard Change templates
    - Problem management with known errors
    - Incident major incident management
    - SLA tracking
    """

    # ========== Change Management API ==========
    
    # Change types
    CHANGE_TYPES = {
        "standard": "standard",
        "normal": "normal",
        "emergency": "emergency",
    }
    
    # Change states
    CHANGE_STATES = {
        "new": -5,
        "assess": -4,
        "authorize": -3,
        "scheduled": -2,
        "implement": -1,
        "review": 0,
        "closed": 3,
        "cancelled": 4,
    }
    
    # Risk levels
    RISK_LEVELS = {
        "high": 1,
        "moderate": 2,
        "low": 3,
        "very_low": 4,
    }
    
    def get_change_request(
        self,
        change_sys_id: str | None = None,
        change_number: str | None = None,
    ) -> dict[str, Any]:
        """Get a change request by sys_id or number.
        
        Args:
            change_sys_id: Change sys_id
            change_number: Change number (e.g., CHG0010001)
            
        Returns:
            Change request record
        """
        endpoint = "sn_chg_rest/change"
        
        if change_sys_id:
            endpoint = f"{endpoint}/{change_sys_id}"
        elif change_number:
            params = {"sysparm_query": f"number={change_number}"}
            response = self.get(endpoint, params=params)
            results = response.get("result", [])
            return results[0] if results else {}
        else:
            raise ValueError("Either change_sys_id or change_number required")
        
        response = self.get(endpoint)
        return response.get("result", {})
    
    def get_change_requests(
        self,
        change_type: str | None = None,
        state: str | int | None = None,
        assigned_to: str | None = None,
        assignment_group: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """Get change requests with filtering.
        
        Args:
            change_type: Filter by type (standard/normal/emergency)
            state: Filter by state
            assigned_to: Filter by assigned user
            assignment_group: Filter by assignment group
            limit: Maximum records
            offset: Starting offset
            
        Returns:
            List of change requests
        """
        query_parts = []
        
        if change_type:
            query_parts.append(f"type={change_type}")
        if state is not None:
            state_value = self.CHANGE_STATES.get(str(state), state) if isinstance(state, str) else state
            query_parts.append(f"state={state_value}")
        if assigned_to:
            query_parts.append(f"assigned_to={assigned_to}")
        if assignment_group:
            query_parts.append(f"assignment_group={assignment_group}")
        
        query_parts.append("ORDERBYDESCsys_updated_on")
        
        endpoint = "sn_chg_rest/change"
        params: dict[str, Any] = {
            "sysparm_limit": limit,
            "sysparm_offset": offset,
        }
        if query_parts:
            params["sysparm_query"] = "^".join(query_parts)
        
        response = self.get(endpoint, params=params)
        return response.get("result", [])
    
    def create_change_request(
        self,
        short_description: str,
        change_type: str = "normal",
        description: str | None = None,
        category: str | None = None,
        risk: int = 3,
        impact: int = 3,
        assignment_group: str | None = None,
        assigned_to: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        **extra_fields: Any,
    ) -> dict[str, Any]:
        """Create a new change request.
        
        Args:
            short_description: Brief description
            change_type: Change type (standard/normal/emergency)
            description: Detailed description
            category: Category
            risk: Risk level (1-4)
            impact: Impact level (1-3)
            assignment_group: Group sys_id
            assigned_to: User sys_id
            start_date: Planned start date
            end_date: Planned end date
            **extra_fields: Additional fields
            
        Returns:
            Created change request
        """
        data: dict[str, Any] = {
            "short_description": short_description,
            "type": change_type,
            "risk": risk,
            "impact": impact,
        }
        
        if description:
            data["description"] = description
        if category:
            data["category"] = category
        if assignment_group:
            data["assignment_group"] = assignment_group
        if assigned_to:
            data["assigned_to"] = assigned_to
        if start_date:
            data["start_date"] = start_date
        if end_date:
            data["end_date"] = end_date
        
        data.update(extra_fields)
        
        endpoint = "sn_chg_rest/change"
        response = self.post(endpoint, json_data=data)
        
        return response.get("result", {})
    
    def create_standard_change(
        self,
        template_sys_id: str,
        short_description: str | None = None,
        **field_overrides: Any,
    ) -> dict[str, Any]:
        """Create a standard change from template.
        
        Args:
            template_sys_id: Standard change template sys_id
            short_description: Override description
            **field_overrides: Override template fields
            
        Returns:
            Created change request
        """
        endpoint = f"sn_chg_rest/change/standard/{template_sys_id}"
        
        data: dict[str, Any] = {}
        if short_description:
            data["short_description"] = short_description
        data.update(field_overrides)
        
        response = self.post(endpoint, json_data=data)
        return response.get("result", {})
    
    def get_standard_change_templates(self) -> list[dict[str, Any]]:
        """Get available standard change templates.
        
        Returns:
            List of standard change templates
        """
        endpoint = "sn_chg_rest/change/standard/template"
        response = self.get(endpoint)
        return response.get("result", [])
    
    def update_change_request(
        self,
        change_sys_id: str,
        updates: dict[str, Any],
    ) -> dict[str, Any]:
        """Update a change request.
        
        Args:
            change_sys_id: Change sys_id
            updates: Fields to update
            
        Returns:
            Updated change request
        """
        endpoint = f"sn_chg_rest/change/{change_sys_id}"
        response = self.patch(endpoint, json_data=updates)
        return response.get("result", {})
    
    def approve_change(
        self,
        change_sys_id: str,
        comments: str | None = None,
    ) -> dict[str, Any]:
        """Approve a change request.
        
        Args:
            change_sys_id: Change sys_id
            comments: Approval comments
            
        Returns:
            Updated change request
        """
        updates: dict[str, Any] = {"approval": "approved"}
        if comments:
            updates["comments"] = comments
        
        return self.update_change_request(change_sys_id, updates)
    
    def reject_change(
        self,
        change_sys_id: str,
        reason: str,
    ) -> dict[str, Any]:
        """Reject a change request.
        
        Args:
            change_sys_id: Change sys_id
            reason: Rejection reason
            
        Returns:
            Updated change request
        """
        return self.update_change_request(change_sys_id, {
            "approval": "rejected",
            "comments": reason,
        })
    
    def close_change(
        self,
        change_sys_id: str,
        close_code: str = "successful",
        close_notes: str | None = None,
    ) -> dict[str, Any]:
        """Close a change request.
        
        Args:
            change_sys_id: Change sys_id
            close_code: Closure code
            close_notes: Closure notes
            
        Returns:
            Updated change request
        """
        updates: dict[str, Any] = {
            "state": self.CHANGE_STATES["closed"],
            "close_code": close_code,
        }
        if close_notes:
            updates["close_notes"] = close_notes
        
        return self.update_change_request(change_sys_id, updates)
    
    def get_change_tasks(
        self,
        change_sys_id: str,
    ) -> list[dict[str, Any]]:
        """Get tasks for a change request.
        
        Args:
            change_sys_id: Change sys_id
            
        Returns:
            List of change tasks
        """
        endpoint = f"{self.api_version}/table/change_task"
        params = {
            "sysparm_query": f"change_request={change_sys_id}",
            "sysparm_display_value": "true",
        }
        
        response = self.get(endpoint, params=params)
        return response.get("result", [])
    
    def add_change_task(
        self,
        change_sys_id: str,
        short_description: str,
        **task_fields: Any,
    ) -> dict[str, Any]:
        """Add a task to a change request.
        
        Args:
            change_sys_id: Change sys_id
            short_description: Task description
            **task_fields: Additional task fields
            
        Returns:
            Created change task
        """
        data: dict[str, Any] = {
            "change_request": change_sys_id,
            "short_description": short_description,
        }
        data.update(task_fields)
        
        endpoint = f"{self.api_version}/table/change_task"
        response = self.post(endpoint, json_data=data)
        
        return response.get("result", {})
    
    # ========== Incident Management ==========
    
    INCIDENT_STATES = {
        "new": 1,
        "in_progress": 2,
        "on_hold": 3,
        "resolved": 6,
        "closed": 7,
        "cancelled": 8,
    }
    
    def create_incident(
        self,
        short_description: str,
        description: str | None = None,
        caller_id: str | None = None,
        category: str | None = None,
        subcategory: str | None = None,
        priority: int = 3,
        urgency: int = 2,
        impact: int = 2,
        assignment_group: str | None = None,
        assigned_to: str | None = None,
        **extra_fields: Any,
    ) -> dict[str, Any]:
        """Create a new incident.
        
        Args:
            short_description: Brief description
            description: Detailed description
            caller_id: Caller user sys_id
            category: Category
            subcategory: Subcategory
            priority: Priority (1-5)
            urgency: Urgency (1-3)
            impact: Impact (1-3)
            assignment_group: Group sys_id
            assigned_to: User sys_id
            **extra_fields: Additional fields
            
        Returns:
            Created incident
        """
        data: dict[str, Any] = {
            "short_description": short_description,
            "priority": priority,
            "urgency": urgency,
            "impact": impact,
        }
        
        if description:
            data["description"] = description
        if caller_id:
            data["caller_id"] = caller_id
        if category:
            data["category"] = category
        if subcategory:
            data["subcategory"] = subcategory
        if assignment_group:
            data["assignment_group"] = assignment_group
        if assigned_to:
            data["assigned_to"] = assigned_to
        
        data.update(extra_fields)
        
        endpoint = f"{self.api_version}/table/incident"
        response = self.post(endpoint, json_data=data)
        
        return response.get("result", {})
    
    def resolve_incident(
        self,
        incident_sys_id: str,
        resolution_code: str,
        resolution_notes: str,
        resolved_by: str | None = None,
    ) -> dict[str, Any]:
        """Resolve an incident.
        
        Args:
            incident_sys_id: Incident sys_id
            resolution_code: Resolution code
            resolution_notes: Resolution notes
            resolved_by: Resolver user sys_id
            
        Returns:
            Updated incident
        """
        updates: dict[str, Any] = {
            "state": self.INCIDENT_STATES["resolved"],
            "close_code": resolution_code,
            "close_notes": resolution_notes,
        }
        
        if resolved_by:
            updates["resolved_by"] = resolved_by
        
        endpoint = f"{self.api_version}/table/incident/{incident_sys_id}"
        response = self.patch(endpoint, json_data=updates)
        
        return response.get("result", {})
    
    def add_work_note(
        self,
        
        record_sys_id: str,
        note: str,
        table: str = "incident",
    ) -> dict[str, Any]:
        """Add a work note to a record.
        
        Args:
            record_sys_id: Record sys_id
            note: Work note text
            table: Table name
            
        Returns:
            Updated record
        """
        endpoint = f"{self.api_version}/table/{table}/{record_sys_id}"
        response = self.patch(endpoint, json_data={"work_notes": note})
        
        return response.get("result", {})
    
    def add_comment(
        self,
        record_sys_id: str,
        comment: str,
        table: str = "incident",
    ) -> dict[str, Any]:
        """Add a customer-visible comment to a record.
        
        Args:
            record_sys_id: Record sys_id
            comment: Comment text
            table: Table name
            
        Returns:
            Updated record
        """
        endpoint = f"{self.api_version}/table/{table}/{record_sys_id}"
        response = self.patch(endpoint, json_data={"comments": comment})
        
        return response.get("result", {})
    
    # ========== Problem Management ==========
    
    def create_problem(
        self,
        short_description: str,
        description: str | None = None,
        category: str | None = None,
        priority: int = 3,
        assignment_group: str | None = None,
        related_incidents: list[str] | None = None,
        **extra_fields: Any,
    ) -> dict[str, Any]:
        """Create a new problem record.
        
        Args:
            short_description: Brief description
            description: Detailed description
            category: Category
            priority: Priority (1-5)
            assignment_group: Group sys_id
            related_incidents: List of incident sys_ids
            **extra_fields: Additional fields
            
        Returns:
            Created problem
        """
        data: dict[str, Any] = {
            "short_description": short_description,
            "priority": priority,
        }
        
        if description:
            data["description"] = description
        if category:
            data["category"] = category
        if assignment_group:
            data["assignment_group"] = assignment_group
        
        data.update(extra_fields)
        
        endpoint = f"{self.api_version}/table/problem"
        response = self.post(endpoint, json_data=data)
        
        problem = response.get("result", {})
        
        # Link related incidents
        if related_incidents and problem.get("sys_id"):
            for incident_id in related_incidents:
                self.link_incident_to_problem(incident_id, problem["sys_id"])
        
        return problem
    
    def link_incident_to_problem(
        self,
        incident_sys_id: str,
        problem_sys_id: str,
    ) -> dict[str, Any]:
        """Link an incident to a problem.
        
        Args:
            incident_sys_id: Incident sys_id
            problem_sys_id: Problem sys_id
            
        Returns:
            Updated incident
        """
        endpoint = f"{self.api_version}/table/incident/{incident_sys_id}"
        response = self.patch(endpoint, json_data={"problem_id": problem_sys_id})
        
        return response.get("result", {})
    
    def mark_as_known_error(
        self,
        problem_sys_id: str,
        workaround: str | None = None,
    ) -> dict[str, Any]:
        """Mark a problem as a known error.
        
        Args:
            problem_sys_id: Problem sys_id
            workaround: Workaround description
            
        Returns:
            Updated problem
        """
        updates: dict[str, Any] = {"known_error": True}
        if workaround:
            updates["workaround"] = workaround
        
        endpoint = f"{self.api_version}/table/problem/{problem_sys_id}"
        response = self.patch(endpoint, json_data=updates)
        
        return response.get("result", {})
    
    # ========== Alarm Management API (Event Management) ==========
    
    def create_event(
        self,
        source: str,
        node: str,
        event_type: str,
        resource: str | None = None,
        metric_name: str | None = None,
        severity: int = 4,
        description: str | None = None,
        additional_info: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Create an event in Event Management.
        
        Args:
            source: Event source
            node: Node/host name
            event_type: Type of event
            resource: Resource affected
            metric_name: Metric name
            severity: Severity (1=Critical, 4=Info)
            description: Event description
            additional_info: Additional event data
            
        Returns:
            Created event
        """
        data: dict[str, Any] = {
            "source": source,
            "node": node,
            "type": event_type,
            "severity": severity,
        }
        
        if resource:
            data["resource"] = resource
        if metric_name:
            data["metric_name"] = metric_name
        if description:
            data["description"] = description
        if additional_info:
            data["additional_info"] = additional_info
        
        endpoint = f"{self.api_version}/em/event"
        response = self.post(endpoint, json_data=data)
        
        return response.get("result", {})
    
    def get_alerts(
        self,
        query: str | None = None,
        state: str | None = None,
        severity: int | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Get alerts from Event Management.
        
        Args:
            query: Custom query
            state: Alert state filter
            severity: Severity filter
            limit: Maximum records
            
        Returns:
            List of alerts
        """
        query_parts = []
        
        if query:
            query_parts.append(query)
        if state:
            query_parts.append(f"state={state}")
        if severity is not None:
            query_parts.append(f"severity={severity}")
        
        endpoint = f"{self.api_version}/table/em_alert"
        params: dict[str, Any] = {
            "sysparm_limit": limit,
            "sysparm_display_value": "true",
        }
        if query_parts:
            params["sysparm_query"] = "^".join(query_parts)
        
        response = self.get(endpoint, params=params)
        return response.get("result", [])
    
    def acknowledge_alert(
        self,
        alert_sys_id: str,
        user: str | None = None,
    ) -> dict[str, Any]:
        """Acknowledge an alert.
        
        Args:
            alert_sys_id: Alert sys_id
            user: Acknowledging user
            
        Returns:
            Updated alert
        """
        updates: dict[str, Any] = {"acknowledged": True}
        if user:
            updates["acknowledged_by"] = user
        
        endpoint = f"{self.api_version}/table/em_alert/{alert_sys_id}"
        response = self.patch(endpoint, json_data=updates)
        
        return response.get("result", {})
