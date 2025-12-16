"""
Heavy Celery app configuration for MyPlatform.
For resource-intensive tasks.
Ported from ee/esa/background/celery/apps/heavy.py
"""
from esa.background.celery.apps.heavy import celery_app


celery_app.autodiscover_tasks(
    [
        "myplatform.background.celery.tasks.doc_permission_syncing",
        "myplatform.background.celery.tasks.external_group_syncing",
        "myplatform.background.celery.tasks.cleanup",
        "myplatform.background.celery.tasks.query_history",
    ]
)
