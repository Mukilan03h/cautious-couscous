"""
Beat schedule for MyPlatform Celery periodic tasks.
Ported from ee/esa/background/celery/tasks/beat_schedule.py
"""
from datetime import timedelta
from typing import Any

from esa.background.celery.tasks.beat_schedule import (
    beat_cloud_tasks as base_beat_system_tasks,
)
from esa.background.celery.tasks.beat_schedule import BEAT_EXPIRES_DEFAULT
from esa.background.celery.tasks.beat_schedule import (
    beat_task_templates as base_beat_task_templates,
)
from esa.background.celery.tasks.beat_schedule import generate_cloud_tasks
from esa.background.celery.tasks.beat_schedule import (
    get_tasks_to_schedule as base_get_tasks_to_schedule,
)
from esa.configs.constants import ESACeleryPriority
from esa.configs.constants import ESACeleryQueues
from esa.configs.constants import ESACeleryTask
from shared_configs.configs import MULTI_TENANT


# Default frequency for TTL management checks (in hours)
CHECK_TTL_MANAGEMENT_TASK_FREQUENCY_IN_HOURS = 6


myplatform_beat_system_tasks: list[dict] = []

myplatform_beat_task_templates: list[dict] = [
    {
        "name": "autogenerate-usage-report",
        "task": ESACeleryTask.GENERATE_USAGE_REPORT_TASK,
        "schedule": timedelta(days=30),
        "options": {
            "priority": ESACeleryPriority.MEDIUM,
            "expires": BEAT_EXPIRES_DEFAULT,
        },
    },
    {
        "name": "check-ttl-management",
        "task": ESACeleryTask.CHECK_TTL_MANAGEMENT_TASK,
        "schedule": timedelta(hours=CHECK_TTL_MANAGEMENT_TASK_FREQUENCY_IN_HOURS),
        "options": {
            "priority": ESACeleryPriority.MEDIUM,
            "expires": BEAT_EXPIRES_DEFAULT,
        },
    },
    {
        "name": "export-query-history-cleanup-task",
        "task": ESACeleryTask.EXPORT_QUERY_HISTORY_CLEANUP_TASK,
        "schedule": timedelta(hours=1),
        "options": {
            "priority": ESACeleryPriority.MEDIUM,
            "expires": BEAT_EXPIRES_DEFAULT,
            "queue": ESACeleryQueues.CSV_GENERATION,
        },
    },
    # MyPlatform-specific: Permission sync check
    {
        "name": "check-permission-sync",
        "task": "myplatform.check_permission_sync",
        "schedule": timedelta(hours=1),
        "options": {
            "priority": ESACeleryPriority.MEDIUM,
            "expires": BEAT_EXPIRES_DEFAULT,
        },
    },
    # MyPlatform-specific: External group sync check
    {
        "name": "check-external-group-sync",
        "task": "myplatform.check_external_group_sync",
        "schedule": timedelta(hours=4),
        "options": {
            "priority": ESACeleryPriority.LOW,
            "expires": BEAT_EXPIRES_DEFAULT,
        },
    },
]

myplatform_tasks_to_schedule: list[dict] = []

if not MULTI_TENANT:
    myplatform_tasks_to_schedule = [
        {
            "name": "autogenerate-usage-report",
            "task": ESACeleryTask.GENERATE_USAGE_REPORT_TASK,
            "schedule": timedelta(days=30),
            "options": {
                "priority": ESACeleryPriority.MEDIUM,
                "expires": BEAT_EXPIRES_DEFAULT,
            },
        },
        {
            "name": "check-ttl-management",
            "task": ESACeleryTask.CHECK_TTL_MANAGEMENT_TASK,
            "schedule": timedelta(hours=CHECK_TTL_MANAGEMENT_TASK_FREQUENCY_IN_HOURS),
            "options": {
                "priority": ESACeleryPriority.MEDIUM,
                "expires": BEAT_EXPIRES_DEFAULT,
            },
        },
        {
            "name": "export-query-history-cleanup-task",
            "task": ESACeleryTask.EXPORT_QUERY_HISTORY_CLEANUP_TASK,
            "schedule": timedelta(hours=1),
            "options": {
                "priority": ESACeleryPriority.MEDIUM,
                "expires": BEAT_EXPIRES_DEFAULT,
                "queue": ESACeleryQueues.CSV_GENERATION,
            },
        },
    ]


def get_cloud_tasks_to_schedule(beat_multiplier: float) -> list[dict[str, Any]]:
    """Get all cloud tasks to schedule including myplatform tasks."""
    beat_system_tasks = myplatform_beat_system_tasks + base_beat_system_tasks
    beat_task_templates = myplatform_beat_task_templates + base_beat_task_templates
    cloud_tasks = generate_cloud_tasks(
        beat_system_tasks, beat_task_templates, beat_multiplier
    )
    return cloud_tasks


def get_tasks_to_schedule() -> list[dict[str, Any]]:
    """Get all tasks to schedule including myplatform tasks."""
    return myplatform_tasks_to_schedule + base_get_tasks_to_schedule()
