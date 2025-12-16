"""
Tenant Provisioning Celery tasks for MyPlatform.
Handles provisioning and deprovisioning of tenants in multi-tenant setups.
Ported from ee/esa/background/celery/tasks/tenant_provisioning/tasks.py
"""
from celery import shared_task
from celery import Task

from esa.configs.app_configs import JOB_TIMEOUT
from esa.db.engine.sql_engine import get_session_with_current_tenant
from esa.utils.logger import setup_logger

logger = setup_logger()


@shared_task(
    name="myplatform.provision_tenant",
    ignore_result=True,
    soft_time_limit=JOB_TIMEOUT,
    bind=True,
    trail=False,
)
def provision_tenant_task(
    self: Task,
    *,
    tenant_id: str,
    tenant_name: str,
    admin_email: str,
) -> None:
    """
    Provision a new tenant in the system.
    
    This creates all necessary resources for a new tenant:
    - Database schema
    - Default settings
    - Admin user
    - Default assistants
    
    Args:
        tenant_id: Unique identifier for the tenant
        tenant_name: Display name for the tenant
        admin_email: Email of the tenant administrator
    """
    # Import here to avoid circular dependencies
    from myplatform.server.tenants.provisioning import provision_new_tenant
    
    logger.info(f"Provisioning new tenant: {tenant_id} ({tenant_name})")
    
    try:
        provision_new_tenant(
            tenant_id=tenant_id,
            tenant_name=tenant_name,
            admin_email=admin_email,
        )
        logger.info(f"Successfully provisioned tenant: {tenant_id}")
    except Exception:
        logger.exception(f"Failed to provision tenant: {tenant_id}")
        raise


@shared_task(
    name="myplatform.deprovision_tenant",
    ignore_result=True,
    soft_time_limit=JOB_TIMEOUT,
    bind=True,
    trail=False,
)
def deprovision_tenant_task(
    self: Task,
    *,
    tenant_id: str,
    hard_delete: bool = False,
) -> None:
    """
    Deprovision a tenant from the system.
    
    Args:
        tenant_id: Unique identifier for the tenant
        hard_delete: If True, permanently delete all data. If False, soft delete.
    """
    # Import here to avoid circular dependencies
    from myplatform.server.tenants.provisioning import deprovision_tenant
    
    logger.info(f"Deprovisioning tenant: {tenant_id} (hard_delete={hard_delete})")
    
    try:
        deprovision_tenant(
            tenant_id=tenant_id,
            hard_delete=hard_delete,
        )
        logger.info(f"Successfully deprovisioned tenant: {tenant_id}")
    except Exception:
        logger.exception(f"Failed to deprovision tenant: {tenant_id}")
        raise


@shared_task(
    name="myplatform.check_tenant_health",
    ignore_result=True,
    soft_time_limit=JOB_TIMEOUT,
)
def check_tenant_health_task(*, tenant_id: str) -> dict:
    """
    Check the health status of a tenant.
    
    Returns a dictionary with health status information.
    
    Args:
        tenant_id: Tenant ID to check
        
    Returns:
        Dictionary with health status
    """
    # Import here to avoid circular dependencies
    from myplatform.server.tenants.health import check_tenant_health
    
    logger.debug(f"Checking health for tenant: {tenant_id}")
    
    with get_session_with_current_tenant() as db_session:
        health_status = check_tenant_health(db_session)
    
    return health_status
