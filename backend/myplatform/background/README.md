# MyPlatform Background Tasks

This directory contains Celery background task infrastructure for the custom platform.
Replaces the ee/esa/background/ functionality.

## Structure

```
background/
├── __init__.py
├── celery_utils.py           # Celery utility functions
├── task_name_builders.py     # Task naming conventions
└── celery/
    ├── apps/                  # Celery app configurations
    │   ├── background.py
    │   ├── heavy.py
    │   ├── light.py
    │   ├── monitoring.py
    │   └── primary.py
    └── tasks/                 # Task implementations
        ├── beat_schedule.py   # Periodic task scheduling
        ├── cleanup/
        ├── doc_permission_syncing/
        ├── external_group_syncing/
        ├── query_history/
        ├── tenant_provisioning/
        ├── ttl_management/
        └── usage_reporting/
```
