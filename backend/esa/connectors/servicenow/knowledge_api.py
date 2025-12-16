"""ServiceNow Knowledge Management API Client.

Implements the ServiceNow Knowledge Management REST API for knowledge
base articles, categories, and search functionality.

Reference: ServiceNow Zurich REST API - Knowledge Management REST API
Endpoint: /api/sn_km_api/knowledge
"""

from typing import Any, Iterator

from esa.connectors.servicenow.base_client import BaseServiceNowClient
from esa.utils.logger import setup_logger

logger = setup_logger()


class KnowledgeAPIClient(BaseServiceNowClient):
    """ServiceNow Knowledge Management API Client.
    
    Provides comprehensive KB functionality:
    - Article search and retrieval
    - Article lifecycle management
    - Category navigation
    - Most viewed/featured articles
    - Article feedback and ratings
    - KB analytics
    """

    # Article workflow states
    WORKFLOW_STATES = {
        "draft": "Draft",
        "review": "Review",
        "pending_publication": "Pending Publication",
        "published": "Published",
        "pending_retirement": "Pending Retirement",
        "retired": "Retired",
        "outdated": "Outdated",
    }

    # Article types
    ARTICLE_TYPES = {
        "text": "text",
        "html": "html",
        "wiki": "wiki",
    }

    # ========== Article Retrieval ==========
    
    def search_articles(
        self,
        query: str,
        knowledge_base: str | None = None,
        category: str | None = None,
        limit: int = 20,
        offset: int = 0,
        workflow_state: str = "published",
    ) -> tuple[list[dict[str, Any]], int]:
        """Search knowledge articles.
        
        Args:
            query: Search text
            knowledge_base: KB sys_id to search within
            category: Category sys_id to filter by
            limit: Maximum results
            offset: Starting offset
            workflow_state: Article state filter
            
        Returns:
            Tuple of (articles list, total count)
        """
        params: dict[str, Any] = {
            "sysparm_search": query,
            "sysparm_limit": limit,
            "sysparm_offset": offset,
        }
        
        if knowledge_base:
            params["sysparm_knowledge_base"] = knowledge_base
        if category:
            params["sysparm_category"] = category
        if workflow_state:
            params["sysparm_workflow_state"] = workflow_state
        
        endpoint = "sn_km_api/knowledge/articles"
        response = self.get(endpoint, params=params)
        
        result = response.get("result", {})
        articles = result.get("articles", [])
        total = result.get("meta", {}).get("total", len(articles))
        
        return articles, total
    
    def get_article(
        self,
        article_sys_id: str | None = None,
        article_number: str | None = None,
        include_body: bool = True,
    ) -> dict[str, Any]:
        """Get a knowledge article by sys_id or number.
        
        Args:
            article_sys_id: Article sys_id
            article_number: Article number (e.g., KB0010001)
            include_body: Whether to include full article content
            
        Returns:
            Article data
        """
        if article_sys_id:
            endpoint = f"sn_km_api/knowledge/articles/{article_sys_id}"
        elif article_number:
            # Search by number
            endpoint = f"{self.api_version}/table/kb_knowledge"
            params = {
                "sysparm_query": f"number={article_number}",
                "sysparm_limit": 1,
            }
            response = self.get(endpoint, params=params)
            results = response.get("result", [])
            return results[0] if results else {}
        else:
            raise ValueError("Either article_sys_id or article_number required")
        
        params: dict[str, Any] = {}
        if not include_body:
            params["sysparm_exclude_content"] = "true"
        
        response = self.get(endpoint, params=params)
        return response.get("result", {})
    
    def get_article_content(self, article_sys_id: str) -> str:
        """Get just the article body content.
        
        Args:
            article_sys_id: Article sys_id
            
        Returns:
            Article body text/HTML
        """
        article = self.get_article(article_sys_id, include_body=True)
        
        # Check for wiki, text, or html content
        return (
            article.get("text", "") or 
            article.get("wiki", "") or 
            article.get("article_body", "")
        )
    
    def get_articles(
        self,
        knowledge_base: str | None = None,
        category: str | None = None,
        workflow_state: str = "published",
        limit: int = 100,
        offset: int = 0,
        order_by: str = "sys_updated_on",
        order_dir: str = "desc",
        updated_after: float | None = None,
    ) -> tuple[list[dict[str, Any]], bool]:
        """Get knowledge articles with filtering.
        
        Args:
            knowledge_base: KB sys_id filter
            category: Category sys_id filter
            workflow_state: State filter
            limit: Page size
            offset: Starting offset
            order_by: Sort field
            order_dir: Sort direction
            updated_after: Unix timestamp filter
            
        Returns:
            Tuple of (articles list, has_more boolean)
        """
        query_parts = []
        
        if knowledge_base:
            query_parts.append(f"kb_knowledge_base={knowledge_base}")
        if category:
            query_parts.append(f"kb_category={category}")
        if workflow_state:
            query_parts.append(f"workflow_state={workflow_state}")
        if updated_after:
            import time
            dt_str = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(updated_after))
            query_parts.append(f"sys_updated_on>{dt_str}")
        
        # Add ordering
        order_prefix = "ORDERBYDESC" if order_dir == "desc" else "ORDERBY"
        query_parts.append(f"{order_prefix}{order_by}")
        
        query = "^".join(query_parts) if query_parts else None
        
        endpoint = f"{self.api_version}/table/kb_knowledge"
        params: dict[str, Any] = {
            "sysparm_limit": limit,
            "sysparm_offset": offset,
            "sysparm_display_value": "all",
        }
        if query:
            params["sysparm_query"] = query
        
        response = self.get(endpoint, params=params)
        articles = response.get("result", [])
        
        return articles, len(articles) == limit
    
    def get_articles_paginated(
        self,
        knowledge_base: str | None = None,
        category: str | None = None,
        workflow_state: str = "published",
        limit: int = 100,
        max_records: int | None = None,
    ) -> Iterator[dict[str, Any]]:
        """Iterate through all articles with pagination.
        
        Yields:
            Individual article records
        """
        offset = 0
        count = 0
        
        while True:
            articles, has_more = self.get_articles(
                knowledge_base=knowledge_base,
                category=category,
                workflow_state=workflow_state,
                limit=limit,
                offset=offset,
            )
            
            if not articles:
                break
            
            for article in articles:
                yield article
                count += 1
                if max_records and count >= max_records:
                    return
            
            if not has_more:
                break
            
            offset += limit
    
    # ========== Featured & Popular Articles ==========
    
    def get_featured_articles(
        self,
        knowledge_base: str | None = None,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Get featured knowledge articles.
        
        Args:
            knowledge_base: KB sys_id filter
            limit: Maximum articles
            
        Returns:
            List of featured articles
        """
        endpoint = "sn_km_api/knowledge/articles/featured"
        params: dict[str, Any] = {"sysparm_limit": limit}
        
        if knowledge_base:
            params["sysparm_knowledge_base"] = knowledge_base
        
        response = self.get(endpoint, params=params)
        return response.get("result", {}).get("articles", [])
    
    def get_most_viewed_articles(
        self,
        knowledge_base: str | None = None,
        limit: int = 10,
        time_period: str = "30",  # days
    ) -> list[dict[str, Any]]:
        """Get most viewed knowledge articles.
        
        Args:
            knowledge_base: KB sys_id filter
            limit: Maximum articles
            time_period: Days to look back
            
        Returns:
            List of popular articles
        """
        endpoint = "sn_km_api/knowledge/articles/most_viewed"
        params: dict[str, Any] = {
            "sysparm_limit": limit,
            "sysparm_time_period": f"-{time_period}d@0:0:0",
        }
        
        if knowledge_base:
            params["sysparm_knowledge_base"] = knowledge_base
        
        response = self.get(endpoint, params=params)
        return response.get("result", {}).get("articles", [])
    
    def get_most_helpful_articles(
        self,
        knowledge_base: str | None = None,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Get most helpful (highly rated) articles.
        
        Args:
            knowledge_base: KB sys_id filter
            limit: Maximum articles
            
        Returns:
            List of helpful articles
        """
        endpoint = "sn_km_api/knowledge/articles/most_helpful"
        params: dict[str, Any] = {"sysparm_limit": limit}
        
        if knowledge_base:
            params["sysparm_knowledge_base"] = knowledge_base
        
        response = self.get(endpoint, params=params)
        return response.get("result", {}).get("articles", [])
    
    # ========== Knowledge Bases & Categories ==========
    
    def get_knowledge_bases(
        self,
        active_only: bool = True,
    ) -> list[dict[str, Any]]:
        """Get all knowledge bases.
        
        Args:
            active_only: Only return active KBs
            
        Returns:
            List of knowledge base records
        """
        endpoint = f"{self.api_version}/table/kb_knowledge_base"
        params: dict[str, Any] = {}
        
        if active_only:
            params["sysparm_query"] = "active=true"
        
        response = self.get(endpoint, params=params)
        return response.get("result", [])
    
    def get_categories(
        self,
        knowledge_base: str | None = None,
        parent_category: str | None = None,
        active_only: bool = True,
    ) -> list[dict[str, Any]]:
        """Get knowledge base categories.
        
        Args:
            knowledge_base: Filter by KB sys_id
            parent_category: Filter by parent category
            active_only: Only active categories
            
        Returns:
            List of category records
        """
        query_parts = []
        
        if knowledge_base:
            query_parts.append(f"kb_knowledge_base={knowledge_base}")
        if parent_category:
            query_parts.append(f"parent={parent_category}")
        elif parent_category is None:
            # Root categories only
            query_parts.append("parent=NULL")
        if active_only:
            query_parts.append("active=true")
        
        endpoint = f"{self.api_version}/table/kb_category"
        params: dict[str, Any] = {
            "sysparm_display_value": "true",
        }
        if query_parts:
            params["sysparm_query"] = "^".join(query_parts)
        
        response = self.get(endpoint, params=params)
        return response.get("result", [])
    
    def get_category_tree(
        self,
        knowledge_base: str,
        max_depth: int = 5,
    ) -> list[dict[str, Any]]:
        """Get hierarchical category tree for a knowledge base.
        
        Args:
            knowledge_base: KB sys_id
            max_depth: Maximum nesting depth
            
        Returns:
            Nested category structure
        """
        # Get root categories
        root_categories = self.get_categories(
            knowledge_base=knowledge_base,
            parent_category=None,
        )
        
        def fetch_children(category: dict, depth: int) -> dict:
            if depth >= max_depth:
                return category
            
            children = self.get_categories(
                knowledge_base=knowledge_base,
                parent_category=category.get("sys_id"),
            )
            
            category["children"] = [
                fetch_children(c, depth + 1) for c in children
            ]
            return category
        
        return [fetch_children(c, 1) for c in root_categories]
    
    # ========== Article Lifecycle ==========
    
    def create_article(
        self,
        title: str,
        body: str,
        knowledge_base: str,
        category: str | None = None,
        article_type: str = "html",
        workflow_state: str = "draft",
        author: str | None = None,
        **extra_fields: Any,
    ) -> dict[str, Any]:
        """Create a new knowledge article.
        
        Args:
            title: Article title
            body: Article content
            knowledge_base: KB sys_id
            category: Category sys_id
            article_type: Content type (text/html/wiki)
            workflow_state: Initial state
            author: Author sys_id
            **extra_fields: Additional fields
            
        Returns:
            Created article record
        """
        data: dict[str, Any] = {
            "short_description": title,
            "kb_knowledge_base": knowledge_base,
            "workflow_state": workflow_state,
            "article_type": article_type,
        }
        
        # Set content field based on type
        if article_type == "wiki":
            data["wiki"] = body
        else:
            data["text"] = body
        
        if category:
            data["kb_category"] = category
        if author:
            data["author"] = author
        
        data.update(extra_fields)
        
        endpoint = f"{self.api_version}/table/kb_knowledge"
        response = self.post(endpoint, json_data=data)
        
        return response.get("result", {})
    
    def update_article(
        self,
        article_sys_id: str,
        updates: dict[str, Any],
    ) -> dict[str, Any]:
        """Update a knowledge article.
        
        Args:
            article_sys_id: Article sys_id
            updates: Fields to update
            
        Returns:
            Updated article record
        """
        endpoint = f"{self.api_version}/table/kb_knowledge/{article_sys_id}"
        response = self.patch(endpoint, json_data=updates)
        
        return response.get("result", {})
    
    def publish_article(self, article_sys_id: str) -> dict[str, Any]:
        """Publish a knowledge article.
        
        Args:
            article_sys_id: Article sys_id
            
        Returns:
            Updated article record
        """
        return self.update_article(article_sys_id, {
            "workflow_state": "published",
            "published": True,
        })
    
    def retire_article(
        self,
        article_sys_id: str,
        reason: str | None = None,
    ) -> dict[str, Any]:
        """Retire a knowledge article.
        
        Args:
            article_sys_id: Article sys_id
            reason: Retirement reason
            
        Returns:
            Updated article record
        """
        updates: dict[str, Any] = {
            "workflow_state": "retired",
        }
        if reason:
            updates["retirement_reason"] = reason
        
        return self.update_article(article_sys_id, updates)
    
    # ========== Article Feedback ==========
    
    def record_article_view(self, article_sys_id: str) -> None:
        """Record an article view (increment view count).
        
        Args:
            article_sys_id: Article sys_id
        """
        # This would typically be handled by ServiceNow automatically
        # but can be triggered via API
        endpoint = f"sn_km_api/knowledge/articles/{article_sys_id}/view"
        try:
            self.post(endpoint, json_data={})
        except Exception:
            pass  # View recording is non-critical
    
    def rate_article(
        self,
        article_sys_id: str,
        rating: int,
        comments: str | None = None,
    ) -> dict[str, Any]:
        """Rate a knowledge article.
        
        Args:
            article_sys_id: Article sys_id
            rating: Rating value (typically 1-5)
            comments: Optional feedback comments
            
        Returns:
            Feedback record
        """
        data: dict[str, Any] = {
            "article": article_sys_id,
            "rating": rating,
        }
        if comments:
            data["comments"] = comments
        
        endpoint = f"{self.api_version}/table/kb_feedback"
        response = self.post(endpoint, json_data=data)
        
        return response.get("result", {})
    
    def flag_article(
        self,
        article_sys_id: str,
        reason: str,
    ) -> dict[str, Any]:
        """Flag an article for review.
        
        Args:
            article_sys_id: Article sys_id
            reason: Flag reason
            
        Returns:
            Flag record
        """
        data = {
            "article": article_sys_id,
            "flagged": True,
            "comments": reason,
        }
        
        endpoint = f"{self.api_version}/table/kb_feedback"
        response = self.post(endpoint, json_data=data)
        
        return response.get("result", {})
