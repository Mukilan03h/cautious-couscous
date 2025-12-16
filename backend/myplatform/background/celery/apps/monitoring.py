"""
Monitoring Celery app configuration for MyPlatform.
For monitoring and health check tasks.
Ported from ee/esa/background/celery/apps/monitoring.py
"""
from esa.background.celery.apps.monitoring import celery_app

celery_app.autodiscover_tasks(
    [
        "myplatform.background.celery.tasks.tenant_provisioning",
    ]
)
