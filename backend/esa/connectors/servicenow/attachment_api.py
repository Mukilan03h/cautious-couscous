"""ServiceNow Attachment API Client.

Implements the ServiceNow Attachment API for file operations.
Supports uploading, downloading, and managing file attachments.

Reference: ServiceNow Zurich REST API - Attachment API
Endpoint: /api/now/attachment
"""

import base64
import mimetypes
from pathlib import Path
from typing import Any, BinaryIO

from esa.connectors.servicenow.base_client import BaseServiceNowClient
from esa.utils.logger import setup_logger

logger = setup_logger()


class AttachmentAPIClient(BaseServiceNowClient):
    """ServiceNow Attachment API Client.
    
    Provides comprehensive attachment management:
    - Upload files (binary and base64)
    - Download files
    - Query attachments by table/record
    - Delete attachments
    - Get attachment metadata
    """

    def get_attachments(
        self,
        table_name: str | None = None,
        table_sys_id: str | None = None,
        query: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """Get attachment metadata.
        
        Args:
            table_name: Filter by table name
            table_sys_id: Filter by record sys_id
            query: Custom encoded query
            limit: Maximum records
            offset: Starting offset
            
        Returns:
            List of attachment metadata records
        """
        params: dict[str, Any] = {
            "sysparm_limit": limit,
            "sysparm_offset": offset,
        }
        
        # Build query
        query_parts = []
        if table_name:
            query_parts.append(f"table_name={table_name}")
        if table_sys_id:
            query_parts.append(f"table_sys_id={table_sys_id}")
        if query:
            query_parts.append(query)
        
        if query_parts:
            params["sysparm_query"] = "^".join(query_parts)
        
        endpoint = f"{self.api_version}/attachment"
        response = self.get(endpoint, params=params)
        
        return response.get("result", [])
    
    def get_attachment_metadata(self, attachment_sys_id: str) -> dict[str, Any]:
        """Get metadata for a specific attachment.
        
        Args:
            attachment_sys_id: Attachment sys_id
            
        Returns:
            Attachment metadata
        """
        endpoint = f"{self.api_version}/attachment/{attachment_sys_id}"
        response = self.get(endpoint)
        
        return response.get("result", {})
    
    def download_attachment(self, attachment_sys_id: str) -> bytes:
        """Download attachment file content.
        
        Args:
            attachment_sys_id: Attachment sys_id
            
        Returns:
            Binary file content
        """
        endpoint = f"{self.api_version}/attachment/{attachment_sys_id}/file"
        
        # Need to handle binary response
        url = f"{self.base_url}/{endpoint}"
        headers = self._get_auth_headers()
        headers["Accept"] = "*/*"
        
        response = self._session.get(
            url,
            headers=headers,
            auth=self._get_auth(),
            timeout=self.timeout,
        )
        
        if not response.ok:
            self._handle_error_response(response)
        
        return response.content
    
    def download_attachment_to_file(
        self,
        attachment_sys_id: str,
        output_path: str | Path,
    ) -> Path:
        """Download attachment to a local file.
        
        Args:
            attachment_sys_id: Attachment sys_id
            output_path: Local file path to save to
            
        Returns:
            Path to saved file
        """
        content = self.download_attachment(attachment_sys_id)
        
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(content)
        
        return output_path
    
    def upload_attachment_binary(
        self,
        table_name: str,
        table_sys_id: str,
        file_name: str,
        file_content: bytes | BinaryIO,
        content_type: str | None = None,
        encryption_context: str | None = None,
    ) -> dict[str, Any]:
        """Upload an attachment using binary/multipart upload.
        
        Args:
            table_name: Target table name
            table_sys_id: Target record sys_id
            file_name: Name for the attachment
            file_content: Binary content or file-like object
            content_type: MIME type (auto-detected if not provided)
            encryption_context: Optional encryption context sys_id
            
        Returns:
            Created attachment metadata
        """
        # Auto-detect content type if not provided
        if not content_type:
            content_type, _ = mimetypes.guess_type(file_name)
            content_type = content_type or "application/octet-stream"
        
        # Get content as bytes
        if hasattr(file_content, 'read'):
            data = file_content.read()
        else:
            data = file_content
        
        params: dict[str, Any] = {
            "table_name": table_name,
            "table_sys_id": table_sys_id,
            "file_name": file_name,
        }
        
        if encryption_context:
            params["encryption_context"] = encryption_context
        
        endpoint = f"{self.api_version}/attachment/file"
        url = f"{self.base_url}/{endpoint}"
        
        headers = self._get_auth_headers()
        headers["Content-Type"] = content_type
        headers["Accept"] = "application/json"
        
        response = self._session.post(
            url,
            params=params,
            data=data,
            headers=headers,
            auth=self._get_auth(),
            timeout=self.timeout,
        )
        
        if not response.ok:
            self._handle_error_response(response)
        
        return response.json().get("result", {})
    
    def upload_attachment_multipart(
        self,
        table_name: str,
        table_sys_id: str,
        file_path: str | Path,
        file_name: str | None = None,
    ) -> dict[str, Any]:
        """Upload an attachment using multipart form data.
        
        Args:
            table_name: Target table name
            table_sys_id: Target record sys_id
            file_path: Path to local file
            file_name: Override file name (uses path basename if not provided)
            
        Returns:
            Created attachment metadata
        """
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        if not file_name:
            file_name = file_path.name
        
        content_type, _ = mimetypes.guess_type(str(file_path))
        content_type = content_type or "application/octet-stream"
        
        files = {
            "file": (file_name, file_path.read_bytes(), content_type),
        }
        
        params: dict[str, Any] = {
            "table_name": table_name,
            "table_sys_id": table_sys_id,
        }
        
        endpoint = f"{self.api_version}/attachment/file"
        
        # For multipart, we use the request method with files
        response = self.request(
            "POST",
            endpoint,
            params=params,
            files=files,
        )
        
        return response.get("result", {})
    
    def upload_attachment_base64(
        self,
        table_name: str,
        table_sys_id: str,
        file_name: str,
        base64_content: str,
        content_type: str | None = None,
    ) -> dict[str, Any]:
        """Upload an attachment using base64 encoded content.
        
        Useful for smaller files or when binary upload is not convenient.
        
        Args:
            table_name: Target table name
            table_sys_id: Target record sys_id
            file_name: Name for the attachment
            base64_content: Base64 encoded file content
            content_type: MIME type
            
        Returns:
            Created attachment metadata
        """
        # Decode and upload as binary
        binary_content = base64.b64decode(base64_content)
        
        return self.upload_attachment_binary(
            table_name=table_name,
            table_sys_id=table_sys_id,
            file_name=file_name,
            file_content=binary_content,
            content_type=content_type,
        )
    
    def delete_attachment(self, attachment_sys_id: str) -> bool:
        """Delete an attachment.
        
        Args:
            attachment_sys_id: Attachment sys_id
            
        Returns:
            True if deleted successfully
        """
        endpoint = f"{self.api_version}/attachment/{attachment_sys_id}"
        self.delete(endpoint)
        return True
    
    def get_record_attachments(
        self,
        table_name: str,
        record_sys_id: str,
    ) -> list[dict[str, Any]]:
        """Get all attachments for a specific record.
        
        Args:
            table_name: Table name
            record_sys_id: Record sys_id
            
        Returns:
            List of attachment metadata
        """
        return self.get_attachments(
            table_name=table_name,
            table_sys_id=record_sys_id,
        )
    
    def copy_attachment(
        self,
        attachment_sys_id: str,
        target_table: str,
        target_sys_id: str,
    ) -> dict[str, Any]:
        """Copy an attachment to another record.
        
        Args:
            attachment_sys_id: Source attachment sys_id
            target_table: Target table name
            target_sys_id: Target record sys_id
            
        Returns:
            New attachment metadata
        """
        # Get source attachment metadata
        source = self.get_attachment_metadata(attachment_sys_id)
        
        # Download content
        content = self.download_attachment(attachment_sys_id)
        
        # Upload to target
        return self.upload_attachment_binary(
            table_name=target_table,
            table_sys_id=target_sys_id,
            file_name=source.get("file_name", "attachment"),
            file_content=content,
            content_type=source.get("content_type"),
        )
    
    def get_attachment_content_as_text(
        self,
        attachment_sys_id: str,
        encoding: str = "utf-8",
    ) -> str:
        """Download attachment and return as text.
        
        Args:
            attachment_sys_id: Attachment sys_id
            encoding: Text encoding
            
        Returns:
            File content as string
        """
        content = self.download_attachment(attachment_sys_id)
        return content.decode(encoding)
    
    def get_attachment_content_as_base64(
        self,
        attachment_sys_id: str,
    ) -> str:
        """Download attachment and return as base64.
        
        Args:
            attachment_sys_id: Attachment sys_id
            
        Returns:
            Base64 encoded content
        """
        content = self.download_attachment(attachment_sys_id)
        return base64.b64encode(content).decode("ascii")
