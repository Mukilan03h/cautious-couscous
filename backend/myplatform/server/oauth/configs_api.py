"""
OAuth Configurations API for MyPlatform.
Manages OAuth client configurations for connectors.
"""
from datetime import datetime
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from esa.auth.users import current_admin_user
from esa.db.engine.sql_engine import get_session
from esa.db.models import User
from esa.key_value_store.factory import get_kv_store
from myplatform.utils.encryption import encrypt_string, decrypt_string
from esa.utils.logger import setup_logger

logger = setup_logger()
router = APIRouter(prefix="/api/myplatform/admin/oauth-configs", tags=["OAuth Configs"])

KV_OAUTH_CONFIGS_KEY = "myplatform_oauth_configs"


class OAuthConfigInput(BaseModel):
    provider: str
    client_id: str
    client_secret: str
    redirect_uri: str
    enabled: bool = True


class OAuthConfigResponse(BaseModel):
    id: str
    provider: str
    client_id: str
    enabled: bool
    redirect_uri: str
    created_at: str


class ToggleRequest(BaseModel):
    enabled: bool


def _get_all_configs() -> list[dict]:
    """Get all OAuth configs from KV store."""
    kv_store = get_kv_store()
    configs = kv_store.load(KV_OAUTH_CONFIGS_KEY)
    return configs if configs else []


def _save_all_configs(configs: list[dict]) -> None:
    """Save all OAuth configs to KV store."""
    kv_store = get_kv_store()
    kv_store.store(KV_OAUTH_CONFIGS_KEY, configs)


@router.get("", response_model=list[OAuthConfigResponse])
async def list_oauth_configs(
    user: User = Depends(current_admin_user),
):
    """List all OAuth configurations."""
    configs = _get_all_configs()
    return [
        OAuthConfigResponse(
            id=c["id"],
            provider=c["provider"],
            client_id=c["client_id"],
            enabled=c.get("enabled", True),
            redirect_uri=c.get("redirect_uri", ""),
            created_at=c.get("created_at", ""),
        )
        for c in configs
    ]


@router.post("", response_model=OAuthConfigResponse)
async def create_oauth_config(
    config: OAuthConfigInput,
    user: User = Depends(current_admin_user),
):
    """Create a new OAuth configuration."""
    configs = _get_all_configs()
    
    # Check for duplicate provider
    for c in configs:
        if c["provider"] == config.provider:
            raise HTTPException(
                status_code=400,
                detail=f"Configuration for {config.provider} already exists."
            )
    
    new_config = {
        "id": str(uuid4()),
        "provider": config.provider,
        "client_id": config.client_id,
        "client_secret_encrypted": encrypt_string(config.client_secret),
        "redirect_uri": config.redirect_uri,
        "enabled": config.enabled,
        "created_at": datetime.utcnow().isoformat(),
    }
    
    configs.append(new_config)
    _save_all_configs(configs)
    
    return OAuthConfigResponse(
        id=new_config["id"],
        provider=new_config["provider"],
        client_id=new_config["client_id"],
        enabled=new_config["enabled"],
        redirect_uri=new_config["redirect_uri"],
        created_at=new_config["created_at"],
    )


@router.put("/{config_id}", response_model=OAuthConfigResponse)
async def update_oauth_config(
    config_id: str,
    config: OAuthConfigInput,
    user: User = Depends(current_admin_user),
):
    """Update an existing OAuth configuration."""
    configs = _get_all_configs()
    
    for i, c in enumerate(configs):
        if c["id"] == config_id:
            configs[i].update({
                "provider": config.provider,
                "client_id": config.client_id,
                "redirect_uri": config.redirect_uri,
                "enabled": config.enabled,
            })
            
            # Only update secret if provided
            if config.client_secret:
                configs[i]["client_secret_encrypted"] = encrypt_string(config.client_secret)
            
            _save_all_configs(configs)
            
            return OAuthConfigResponse(
                id=configs[i]["id"],
                provider=configs[i]["provider"],
                client_id=configs[i]["client_id"],
                enabled=configs[i]["enabled"],
                redirect_uri=configs[i]["redirect_uri"],
                created_at=configs[i]["created_at"],
            )
    
    raise HTTPException(status_code=404, detail="Configuration not found.")


@router.delete("/{config_id}")
async def delete_oauth_config(
    config_id: str,
    user: User = Depends(current_admin_user),
):
    """Delete an OAuth configuration."""
    configs = _get_all_configs()
    
    for i, c in enumerate(configs):
        if c["id"] == config_id:
            configs.pop(i)
            _save_all_configs(configs)
            return {"message": "Configuration deleted."}
    
    raise HTTPException(status_code=404, detail="Configuration not found.")


@router.post("/{config_id}/toggle")
async def toggle_oauth_config(
    config_id: str,
    toggle: ToggleRequest,
    user: User = Depends(current_admin_user),
):
    """Toggle OAuth configuration enabled status."""
    configs = _get_all_configs()
    
    for i, c in enumerate(configs):
        if c["id"] == config_id:
            configs[i]["enabled"] = toggle.enabled
            _save_all_configs(configs)
            return {"message": f"Configuration {'enabled' if toggle.enabled else 'disabled'}."}
    
    raise HTTPException(status_code=404, detail="Configuration not found.")


def get_oauth_config_for_provider(provider: str) -> Optional[dict]:
    """
    Get OAuth configuration for a specific provider.
    Used by OAuth flow handlers.
    """
    configs = _get_all_configs()
    
    for c in configs:
        if c["provider"] == provider and c.get("enabled", True):
            return {
                "client_id": c["client_id"],
                "client_secret": decrypt_string(c["client_secret_encrypted"]),
                "redirect_uri": c["redirect_uri"],
            }
    
    return None
