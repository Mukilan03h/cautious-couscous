"""
Light Celery app configuration for MyPlatform.
For lightweight, quick tasks.
Ported from ee/esa/background/celery/apps/light.py
"""
from esa.background.celery.apps.light import celery_app

celery_app.autodiscover_tasks(
    [
        "myplatform.background.celery.tasks.doc_permission_syncing",
        "myplatform.background.celery.tasks.external_group_syncing",
    ]
)
