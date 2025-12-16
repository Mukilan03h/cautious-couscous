"""
Enterprise settings storage for MyPlatform.
Ported from ee/esa/server/enterprise_settings/store.py
"""
import json
from typing import cast

from fastapi import UploadFile

from myplatform.server.enterprise_settings.models import AnalyticsScriptUpload
from myplatform.server.enterprise_settings.models import EnterpriseSettings
from esa.db.engine.sql_engine import get_session_with_current_tenant
from esa.file_store.file_store import get_default_file_store
from esa.key_value_store.factory import get_kv_store
from esa.utils.logger import setup_logger

logger = setup_logger()

# Key-value store keys
ENTERPRISE_SETTINGS_KEY = "enterprise_settings"
ANALYTICS_SCRIPT_KEY = "analytics_script"
LOGO_FILENAME = "custom_logo"
LOGOTYPE_FILENAME = "custom_logotype"


def get_logo_filename() -> str:
    """Get the filename for the custom logo."""
    return LOGO_FILENAME


def get_logotype_filename() -> str:
    """Get the filename for the custom logotype."""
    return LOGOTYPE_FILENAME


def load_settings() -> EnterpriseSettings:
    """Load enterprise settings from the key-value store."""
    kv_store = get_kv_store()
    settings_json = kv_store.get(ENTERPRISE_SETTINGS_KEY)
    
    if settings_json is None:
        return EnterpriseSettings()
    
    try:
        return EnterpriseSettings(**json.loads(settings_json))
    except Exception as e:
        logger.error(f"Failed to load enterprise settings: {e}")
        return EnterpriseSettings()


def store_settings(settings: EnterpriseSettings) -> None:
    """Store enterprise settings in the key-value store."""
    kv_store = get_kv_store()
    kv_store.set(ENTERPRISE_SETTINGS_KEY, settings.model_dump_json())
    logger.info("Enterprise settings updated")


def upload_logo(file: UploadFile, is_logotype: bool = False) -> None:
    """Upload a custom logo or logotype."""
    file_store = get_default_file_store()
    filename = get_logotype_filename() if is_logotype else get_logo_filename()
    
    content = file.file.read()
    content_type = file.content_type or "image/png"
    
    file_store.save_file_from_bytes(
        file_id=filename,
        content=content,
        content_type=content_type,
    )
    
    # Update settings to indicate custom logo is set
    settings = load_settings()
    if is_logotype:
        settings.custom_logotype = True
    else:
        settings.custom_logo = True
    store_settings(settings)
    
    logger.info(f"Custom {'logotype' if is_logotype else 'logo'} uploaded")


def store_analytics_script(script_upload: AnalyticsScriptUpload) -> None:
    """Store a custom analytics script."""
    if not script_upload.script:
        raise ValueError("Analytics script cannot be empty")
    
    # Basic validation - check for obvious issues
    if len(script_upload.script) > 50000:  # 50KB limit
        raise ValueError("Analytics script is too large")
    
    kv_store = get_kv_store()
    kv_store.set(ANALYTICS_SCRIPT_KEY, script_upload.script)
    logger.info("Custom analytics script stored")


def load_analytics_script() -> str | None:
    """Load the custom analytics script."""
    kv_store = get_kv_store()
    return cast(str | None, kv_store.get(ANALYTICS_SCRIPT_KEY))
