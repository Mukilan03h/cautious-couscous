"""
Background Celery app configuration for MyPlatform.
For general background processing tasks.
Ported from ee/esa/background/celery/apps/background.py
"""
from esa.background.celery.apps.background import celery_app


celery_app.autodiscover_tasks(
    [
        "myplatform.background.celery.tasks.doc_permission_syncing",
        "myplatform.background.celery.tasks.external_group_syncing",
        "myplatform.background.celery.tasks.cleanup",
        "myplatform.background.celery.tasks.tenant_provisioning",
        "myplatform.background.celery.tasks.query_history",
    ]
)
