"""ServiceNow Customer Service Management (CSM) API Client.

Implements CSM APIs for case management, accounts, contacts, and consumers.

Reference: ServiceNow Zurich REST API
- Case API: /api/sn_customerservice/case
- Account API: /api/now/account
- Consumer API: /api/now/consumer
- Contact API: /api/now/contact
"""

from typing import Any, Iterator

from esa.connectors.servicenow.base_client import BaseServiceNowClient
from esa.utils.logger import setup_logger

logger = setup_logger()


class CSMAPIClient(BaseServiceNowClient):
    """ServiceNow Customer Service Management API Client.
    
    Provides comprehensive CSM functionality:
    - Case management (create, update, resolve, close)
    - Account management
    - Contact management
    - Consumer (B2C) management
    - Entitlements and SLAs
    """

    # Case states
    CASE_STATES = {
        "new": 1,
        "open": 2,
        "awaiting_info": 3,
        "resolved": 6,
        "closed": 7,
        "cancelled": 8,
    }

    # Case priorities
    CASE_PRIORITIES = {
        "critical": 1,
        "high": 2,
        "moderate": 3,
        "low": 4,
        "planning": 5,
    }

    # ========== Case API ==========
    
    def get_case(
        self,
        case_sys_id: str | None = None,
        case_number: str | None = None,
    ) -> dict[str, Any]:
        """Get a CSM case by sys_id or number.
        
        Args:
            case_sys_id: Case sys_id
            case_number: Case number
            
        Returns:
            Case record
        """
        if case_sys_id:
            endpoint = f"sn_customerservice/case/{case_sys_id}"
        elif case_number:
            endpoint = f"{self.api_version}/table/sn_customerservice_case"
            params = {"sysparm_query": f"number={case_number}"}
            response = self.get(endpoint, params=params)
            results = response.get("result", [])
            return results[0] if results else {}
        else:
            raise ValueError("Either case_sys_id or case_number required")
        
        response = self.get(endpoint)
        return response.get("result", {})
    
    def get_cases(
        self,
        account: str | None = None,
        contact: str | None = None,
        consumer: str | None = None,
        state: str | int | None = None,
        priority: str | int | None = None,
        assigned_to: str | None = None,
        assignment_group: str | None = None,
        limit: int = 100,
        offset: int = 0,
        updated_after: float | None = None,
    ) -> tuple[list[dict[str, Any]], bool]:
        """Get CSM cases with filtering.
        
        Args:
            account: Filter by account sys_id
            contact: Filter by contact sys_id
            consumer: Filter by consumer sys_id
            state: Filter by state
            priority: Filter by priority
            assigned_to: Filter by assigned user
            assignment_group: Filter by group
            limit: Maximum records
            offset: Starting offset
            updated_after: Unix timestamp filter
            
        Returns:
            Tuple of (cases list, has_more)
        """
        query_parts = []
        
        if account:
            query_parts.append(f"account={account}")
        if contact:
            query_parts.append(f"contact={contact}")
        if consumer:
            query_parts.append(f"consumer={consumer}")
        if state is not None:
            state_val = self.CASE_STATES.get(str(state), state) if isinstance(state, str) else state
            query_parts.append(f"state={state_val}")
        if priority is not None:
            pri_val = self.CASE_PRIORITIES.get(str(priority), priority) if isinstance(priority, str) else priority
            query_parts.append(f"priority={pri_val}")
        if assigned_to:
            query_parts.append(f"assigned_to={assigned_to}")
        if assignment_group:
            query_parts.append(f"assignment_group={assignment_group}")
        if updated_after:
            import time
            dt_str = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(updated_after))
            query_parts.append(f"sys_updated_on>{dt_str}")
        
        query_parts.append("ORDERBYDESCsys_updated_on")
        
        endpoint = f"{self.api_version}/table/sn_customerservice_case"
        params: dict[str, Any] = {
            "sysparm_limit": limit,
            "sysparm_offset": offset,
            "sysparm_display_value": "all",
        }
        if query_parts:
            params["sysparm_query"] = "^".join(query_parts)
        
        response = self.get(endpoint, params=params)
        cases = response.get("result", [])
        
        return cases, len(cases) == limit
    
    def create_case(
        self,
        short_description: str,
        account: str | None = None,
        contact: str | None = None,
        consumer: str | None = None,
        description: str | None = None,
        priority: int = 3,
        product: str | None = None,
        asset: str | None = None,
        assignment_group: str | None = None,
        assigned_to: str | None = None,
        **extra_fields: Any,
    ) -> dict[str, Any]:
        """Create a new CSM case.
        
        Args:
            short_description: Brief description
            account: Account sys_id
            contact: Contact sys_id
            consumer: Consumer sys_id
            description: Detailed description
            priority: Priority (1-5)
            product: Product sys_id
            asset: Asset sys_id
            assignment_group: Group sys_id
            assigned_to: User sys_id
            **extra_fields: Additional fields
            
        Returns:
            Created case
        """
        data: dict[str, Any] = {
            "short_description": short_description,
            "priority": priority,
        }
        
        if account:
            data["account"] = account
        if contact:
            data["contact"] = contact
        if consumer:
            data["consumer"] = consumer
        if description:
            data["description"] = description
        if product:
            data["product"] = product
        if asset:
            data["asset"] = asset
        if assignment_group:
            data["assignment_group"] = assignment_group
        if assigned_to:
            data["assigned_to"] = assigned_to
        
        data.update(extra_fields)
        
        endpoint = "sn_customerservice/case"
        response = self.post(endpoint, json_data=data)
        
        return response.get("result", {})
    
    def update_case(
        self,
        case_sys_id: str,
        updates: dict[str, Any],
    ) -> dict[str, Any]:
        """Update a CSM case.
        
        Args:
            case_sys_id: Case sys_id
            updates: Fields to update
            
        Returns:
            Updated case
        """
        endpoint = f"sn_customerservice/case/{case_sys_id}"
        response = self.patch(endpoint, json_data=updates)
        
        return response.get("result", {})
    
    def resolve_case(
        self,
        case_sys_id: str,
        resolution_code: str,
        resolution_notes: str,
    ) -> dict[str, Any]:
        """Resolve a CSM case.
        
        Args:
            case_sys_id: Case sys_id
            resolution_code: Resolution code
            resolution_notes: Resolution notes
            
        Returns:
            Updated case
        """
        return self.update_case(case_sys_id, {
            "state": self.CASE_STATES["resolved"],
            "resolution_code": resolution_code,
            "close_notes": resolution_notes,
        })
    
    def close_case(
        self,
        case_sys_id: str,
        close_notes: str | None = None,
    ) -> dict[str, Any]:
        """Close a CSM case.
        
        Args:
            case_sys_id: Case sys_id
            close_notes: Closure notes
            
        Returns:
            Updated case
        """
        updates: dict[str, Any] = {"state": self.CASE_STATES["closed"]}
        if close_notes:
            updates["close_notes"] = close_notes
        
        return self.update_case(case_sys_id, updates)
    
    def escalate_case(
        self,
        case_sys_id: str,
        reason: str,
        escalation_level: int = 1,
    ) -> dict[str, Any]:
        """Escalate a CSM case.
        
        Args:
            case_sys_id: Case sys_id
            reason: Escalation reason
            escalation_level: Escalation level
            
        Returns:
            Updated case
        """
        return self.update_case(case_sys_id, {
            "escalation": escalation_level,
            "escalation_reason": reason,
        })
    
    # ========== Account API ==========
    
    def get_account(self, account_sys_id: str) -> dict[str, Any]:
        """Get a customer account.
        
        Args:
            account_sys_id: Account sys_id
            
        Returns:
            Account record
        """
        endpoint = f"now/account/{account_sys_id}"
        response = self.get(endpoint)
        return response.get("result", {})
    
    def get_accounts(
        self,
        query: str | None = None,
        active_only: bool = True,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """Get customer accounts.
        
        Args:
            query: Custom query
            active_only: Only active accounts
            limit: Maximum records
            offset: Starting offset
            
        Returns:
            List of accounts
        """
        query_parts = []
        if query:
            query_parts.append(query)
        if active_only:
            query_parts.append("active=true")
        
        endpoint = f"{self.api_version}/table/customer_account"
        params: dict[str, Any] = {
            "sysparm_limit": limit,
            "sysparm_offset": offset,
            "sysparm_display_value": "true",
        }
        if query_parts:
            params["sysparm_query"] = "^".join(query_parts)
        
        response = self.get(endpoint, params=params)
        return response.get("result", [])
    
    def create_account(
        self,
        name: str,
        account_code: str | None = None,
        industry: str | None = None,
        street: str | None = None,
        city: str | None = None,
        state: str | None = None,
        country: str | None = None,
        phone: str | None = None,
        website: str | None = None,
        **extra_fields: Any,
    ) -> dict[str, Any]:
        """Create a customer account.
        
        Args:
            name: Account name
            account_code: Account code
            industry: Industry
            street: Street address
            city: City
            state: State/Province
            country: Country
            phone: Phone number
            website: Website URL
            **extra_fields: Additional fields
            
        Returns:
            Created account
        """
        data: dict[str, Any] = {"name": name}
        
        if account_code:
            data["account_code"] = account_code
        if industry:
            data["industry"] = industry
        if street:
            data["street"] = street
        if city:
            data["city"] = city
        if state:
            data["state"] = state
        if country:
            data["country"] = country
        if phone:
            data["phone"] = phone
        if website:
            data["website"] = website
        
        data.update(extra_fields)
        
        endpoint = f"{self.api_version}/table/customer_account"
        response = self.post(endpoint, json_data=data)
        
        return response.get("result", {})
    
    def update_account(
        self,
        account_sys_id: str,
        updates: dict[str, Any],
    ) -> dict[str, Any]:
        """Update a customer account.
        
        Args:
            account_sys_id: Account sys_id
            updates: Fields to update
            
        Returns:
            Updated account
        """
        endpoint = f"now/account/{account_sys_id}"
        response = self.patch(endpoint, json_data=updates)
        
        return response.get("result", {})
    
    # ========== Contact API ==========
    
    def get_contact(self, contact_sys_id: str) -> dict[str, Any]:
        """Get a customer contact.
        
        Args:
            contact_sys_id: Contact sys_id
            
        Returns:
            Contact record
        """
        endpoint = f"now/contact/{contact_sys_id}"
        response = self.get(endpoint)
        return response.get("result", {})
    
    def get_contacts(
        self,
        account: str | None = None,
        email: str | None = None,
        active_only: bool = True,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """Get customer contacts.
        
        Args:
            account: Filter by account sys_id
            email: Filter by email
            active_only: Only active contacts
            limit: Maximum records
            offset: Starting offset
            
        Returns:
            List of contacts
        """
        query_parts = []
        if account:
            query_parts.append(f"account={account}")
        if email:
            query_parts.append(f"email={email}")
        if active_only:
            query_parts.append("active=true")
        
        endpoint = f"{self.api_version}/table/customer_contact"
        params: dict[str, Any] = {
            "sysparm_limit": limit,
            "sysparm_offset": offset,
            "sysparm_display_value": "true",
        }
        if query_parts:
            params["sysparm_query"] = "^".join(query_parts)
        
        response = self.get(endpoint, params=params)
        return response.get("result", [])
    
    def create_contact(
        self,
        first_name: str,
        last_name: str,
        email: str,
        account: str | None = None,
        phone: str | None = None,
        mobile_phone: str | None = None,
        title: str | None = None,
        **extra_fields: Any,
    ) -> dict[str, Any]:
        """Create a customer contact.
        
        Args:
            first_name: First name
            last_name: Last name
            email: Email address
            account: Account sys_id
            phone: Phone number
            mobile_phone: Mobile number
            title: Job title
            **extra_fields: Additional fields
            
        Returns:
            Created contact
        """
        data: dict[str, Any] = {
            "first_name": first_name,
            "last_name": last_name,
            "email": email,
        }
        
        if account:
            data["account"] = account
        if phone:
            data["phone"] = phone
        if mobile_phone:
            data["mobile_phone"] = mobile_phone
        if title:
            data["title"] = title
        
        data.update(extra_fields)
        
        endpoint = f"{self.api_version}/table/customer_contact"
        response = self.post(endpoint, json_data=data)
        
        return response.get("result", {})
    
    def update_contact(
        self,
        contact_sys_id: str,
        updates: dict[str, Any],
    ) -> dict[str, Any]:
        """Update a customer contact.
        
        Args:
            contact_sys_id: Contact sys_id
            updates: Fields to update
            
        Returns:
            Updated contact
        """
        endpoint = f"now/contact/{contact_sys_id}"
        response = self.patch(endpoint, json_data=updates)
        
        return response.get("result", {})
    
    # ========== Consumer API ==========
    
    def get_consumer(self, consumer_sys_id: str) -> dict[str, Any]:
        """Get a consumer record.
        
        Args:
            consumer_sys_id: Consumer sys_id
            
        Returns:
            Consumer record
        """
        endpoint = f"now/consumer/{consumer_sys_id}"
        response = self.get(endpoint)
        return response.get("result", {})
    
    def get_consumers(
        self,
        email: str | None = None,
        active_only: bool = True,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """Get consumers.
        
        Args:
            email: Filter by email
            active_only: Only active consumers
            limit: Maximum records
            offset: Starting offset
            
        Returns:
            List of consumers
        """
        query_parts = []
        if email:
            query_parts.append(f"email={email}")
        if active_only:
            query_parts.append("active=true")
        
        endpoint = f"{self.api_version}/table/csm_consumer"
        params: dict[str, Any] = {
            "sysparm_limit": limit,
            "sysparm_offset": offset,
            "sysparm_display_value": "true",
        }
        if query_parts:
            params["sysparm_query"] = "^".join(query_parts)
        
        response = self.get(endpoint, params=params)
        return response.get("result", [])
    
    def create_consumer(
        self,
        first_name: str,
        last_name: str,
        email: str,
        phone: str | None = None,
        mobile_phone: str | None = None,
        user: str | None = None,
        **extra_fields: Any,
    ) -> dict[str, Any]:
        """Create a consumer record.
        
        Args:
            first_name: First name
            last_name: Last name
            email: Email address
            phone: Phone number
            mobile_phone: Mobile number
            user: Associated user sys_id
            **extra_fields: Additional fields
            
        Returns:
            Created consumer
        """
        data: dict[str, Any] = {
            "first_name": first_name,
            "last_name": last_name,
            "email": email,
        }
        
        if phone:
            data["phone"] = phone
        if mobile_phone:
            data["mobile_phone"] = mobile_phone
        if user:
            data["user"] = user
        
        data.update(extra_fields)
        
        endpoint = f"{self.api_version}/table/csm_consumer"
        response = self.post(endpoint, json_data=data)
        
        return response.get("result", {})
    
    def update_consumer(
        self,
        consumer_sys_id: str,
        updates: dict[str, Any],
    ) -> dict[str, Any]:
        """Update a consumer record.
        
        Args:
            consumer_sys_id: Consumer sys_id
            updates: Fields to update
            
        Returns:
            Updated consumer
        """
        endpoint = f"now/consumer/{consumer_sys_id}"
        response = self.patch(endpoint, json_data=updates)
        
        return response.get("result", {})
    
    # ========== Entitlements ==========
    
    def get_account_entitlements(
        self,
        account_sys_id: str,
    ) -> list[dict[str, Any]]:
        """Get entitlements for an account.
        
        Args:
            account_sys_id: Account sys_id
            
        Returns:
            List of entitlements
        """
        endpoint = f"{self.api_version}/table/service_entitlement"
        params = {
            "sysparm_query": f"account={account_sys_id}^active=true",
            "sysparm_display_value": "true",
        }
        
        response = self.get(endpoint, params=params)
        return response.get("result", [])
    
    def check_entitlement(
        self,
        account_sys_id: str,
        product: str | None = None,
        service: str | None = None,
    ) -> dict[str, Any]:
        """Check if account has a specific entitlement.
        
        Args:
            account_sys_id: Account sys_id
            product: Product sys_id
            service: Service sys_id
            
        Returns:
            Entitlement status
        """
        query_parts = [f"account={account_sys_id}", "active=true"]
        
        if product:
            query_parts.append(f"product={product}")
        if service:
            query_parts.append(f"service={service}")
        
        endpoint = f"{self.api_version}/table/service_entitlement"
        params = {
            "sysparm_query": "^".join(query_parts),
            "sysparm_limit": 1,
        }
        
        response = self.get(endpoint, params=params)
        results = response.get("result", [])
        
        return {
            "entitled": len(results) > 0,
            "entitlement": results[0] if results else None,
        }
