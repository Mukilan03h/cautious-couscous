"""
Cloud Tasks for MyPlatform.
Ported from ee/esa/background/celery/tasks/cloud/tasks.py (112 lines)

Handles cloud-specific beat task generation for multi-tenant deployments.
"""
import time

from celery import shared_task
from celery import Task
from celery.exceptions import SoftTimeLimitExceeded
from redis.lock import Lock as RedisLock

from esa.background.celery.apps.app_base import task_logger
from esa.background.celery.tasks.beat_schedule import BEAT_EXPIRES_DEFAULT
from esa.configs.constants import CELERY_GENERIC_BEAT_LOCK_TIMEOUT
from esa.configs.constants import ONYX_CLOUD_TENANT_ID
from esa.configs.constants import ESACeleryPriority
from esa.configs.constants import ESACeleryTask
from esa.configs.constants import ESARedisLocks
from esa.db.engine.tenant_utils import get_all_tenant_ids
from esa.redis.redis_pool import get_redis_client
from esa.redis.redis_pool import redis_lock_dump
from shared_configs.configs import IGNORED_SYNCING_TENANT_LIST


@shared_task(
    name=ESACeleryTask.CLOUD_BEAT_TASK_GENERATOR,
    ignore_result=True,
    trail=False,
    bind=True,
)
def cloud_beat_task_generator(
    self: Task,
    task_name: str,
    queue: str = ESACeleryTask.DEFAULT,
    priority: int = ESACeleryPriority.MEDIUM,
    expires: int = BEAT_EXPIRES_DEFAULT,
) -> bool | None:
    """a lightweight task used to kick off individual beat tasks per tenant."""
    time_start = time.monotonic()

    redis_client = get_redis_client(tenant_id=ONYX_CLOUD_TENANT_ID)

    lock_beat: RedisLock = redis_client.lock(
        f"{ESARedisLocks.CLOUD_BEAT_TASK_GENERATOR_LOCK}:{task_name}",
        timeout=CELERY_GENERIC_BEAT_LOCK_TIMEOUT,
    )

    # these tasks should never overlap
    if not lock_beat.acquire(blocking=False):
        return None

    last_lock_time = time.monotonic()
    tenant_ids: list[str] = []
    num_processed_tenants = 0

    try:
        tenant_ids = get_all_tenant_ids()

        for tenant_id in tenant_ids:
            current_time = time.monotonic()
            if current_time - last_lock_time >= (CELERY_GENERIC_BEAT_LOCK_TIMEOUT / 4):
                lock_beat.reacquire()
                last_lock_time = current_time

            # needed in the cloud
            if IGNORED_SYNCING_TENANT_LIST and tenant_id in IGNORED_SYNCING_TENANT_LIST:
                continue

            self.app.send_task(
                task_name,
                kwargs=dict(
                    tenant_id=tenant_id,
                ),
                queue=queue,
                priority=priority,
                expires=expires,
                ignore_result=True,
            )

            num_processed_tenants += 1
    except SoftTimeLimitExceeded:
        task_logger.info(
            "Soft time limit exceeded, task is being terminated gracefully."
        )
    except Exception:
        task_logger.exception("Unexpected exception during cloud_beat_task_generator")
    finally:
        if not lock_beat.owned():
            task_logger.error(
                "cloud_beat_task_generator - Lock not owned on completion"
            )
            redis_lock_dump(lock_beat, redis_client)
        else:
            lock_beat.release()

    time_elapsed = time.monotonic() - time_start
    task_logger.info(
        f"cloud_beat_task_generator finished: "
        f"task={task_name} "
        f"num_processed_tenants={num_processed_tenants} "
        f"num_tenants={len(tenant_ids)} "
        f"elapsed={time_elapsed:.2f}"
    )
    return True
