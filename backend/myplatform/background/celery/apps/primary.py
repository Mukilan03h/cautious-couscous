"""
Primary Celery app configuration for MyPlatform.
Ported from ee/esa/background/celery/apps/primary.py
"""
from esa.background.celery.apps.primary import celery_app


celery_app.autodiscover_tasks(
    [
        "myplatform.background.celery.tasks.doc_permission_syncing",
        "myplatform.background.celery.tasks.external_group_syncing",
        "myplatform.background.celery.tasks.cloud",
        "myplatform.background.celery.tasks.ttl_management",
        "myplatform.background.celery.tasks.usage_reporting",
    ]
)
