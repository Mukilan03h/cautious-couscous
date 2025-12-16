"""
External Group Syncing Celery tasks for MyPlatform.
Ported from ee/esa/background/celery/tasks/external_group_syncing/tasks.py - FULL VERSION (732 lines)

Handles syncing user groups from external identity providers (Azure AD, Okta, Google Workspace, LDAP).
"""
import time
from datetime import datetime
from datetime import timedelta
from datetime import timezone
from typing import Any
from typing import cast
from uuid import uuid4

from celery import Celery
from celery import shared_task
from celery import Task
from celery.exceptions import SoftTimeLimitExceeded
from pydantic import ValidationError
from redis import Redis
from redis.lock import Lock as RedisLock

from myplatform.background.celery.tasks.external_group_syncing.group_sync_utils import (
    mark_all_relevant_cc_pairs_as_external_group_synced,
)
from myplatform.db.connector_credential_pair import get_all_auto_sync_cc_pairs
from myplatform.db.connector_credential_pair import get_cc_pairs_by_source
from myplatform.db.external_perm import ExternalUserGroup
from myplatform.db.external_perm import mark_old_external_groups_as_stale
from myplatform.db.external_perm import remove_stale_external_groups
from myplatform.db.external_perm import upsert_external_groups
from myplatform.external_permissions.sync_params import (
    get_all_cc_pair_agnostic_group_sync_sources,
)
from myplatform.external_permissions.sync_params import get_source_perm_sync_config
from esa.background.celery.apps.app_base import task_logger
from esa.background.celery.celery_redis import celery_find_task
from esa.background.celery.celery_redis import celery_get_unacked_task_ids
from esa.background.celery.tasks.beat_schedule import CLOUD_BEAT_MULTIPLIER_DEFAULT
from esa.background.error_logging import emit_background_error
from esa.configs.app_configs import JOB_TIMEOUT
from esa.configs.constants import CELERY_EXTERNAL_GROUP_SYNC_LOCK_TIMEOUT
from esa.configs.constants import CELERY_GENERIC_BEAT_LOCK_TIMEOUT
from esa.configs.constants import CELERY_TASK_WAIT_FOR_FENCE_TIMEOUT
from esa.configs.constants import ESACeleryPriority
from esa.configs.constants import ESACeleryQueues
from esa.configs.constants import ESACeleryTask
from esa.configs.constants import ESARedisConstants
from esa.configs.constants import ESARedisLocks
from esa.configs.constants import ESARedisSignals
from esa.db.connector_credential_pair import get_connector_credential_pair_from_id
from esa.db.engine.sql_engine import get_session_with_current_tenant
from esa.db.enums import AccessType
from esa.db.enums import ConnectorCredentialPairStatus
from esa.db.enums import SyncStatus
from esa.db.enums import SyncType
from esa.db.models import ConnectorCredentialPair
from esa.db.permission_sync_attempt import complete_external_group_sync_attempt
from esa.db.permission_sync_attempt import (
    create_external_group_sync_attempt,
)
from esa.db.permission_sync_attempt import (
    mark_external_group_sync_attempt_failed,
)
from esa.db.permission_sync_attempt import (
    mark_external_group_sync_attempt_in_progress,
)
from esa.db.sync_record import insert_sync_record
from esa.db.sync_record import update_sync_record_status
from esa.redis.redis_connector import RedisConnector
from esa.redis.redis_connector_ext_group_sync import RedisConnectorExternalGroupSync
from esa.redis.redis_connector_ext_group_sync import (
    RedisConnectorExternalGroupSyncPayload,
)
from esa.redis.redis_pool import get_redis_client
from esa.redis.redis_pool import get_redis_replica_client
from esa.server.runtime.esa_runtime import ESARuntime
from esa.server.utils import make_short_id
from esa.utils.logger import format_error_for_logging
from esa.utils.logger import setup_logger
from shared_configs.configs import MULTI_TENANT

logger = setup_logger()


_EXTERNAL_GROUP_BATCH_SIZE = 100


def _fail_external_group_sync_attempt(attempt_id: int, error_msg: str) -> None:
    """Helper to mark an external group sync attempt as failed with an error message."""
    with get_session_with_current_tenant() as db_session:
        mark_external_group_sync_attempt_failed(
            attempt_id, db_session, error_message=error_msg
        )


def _get_fence_validation_block_expiration() -> int:
    """
    Compute the expiration time for the fence validation block signal.
    Base expiration is 300 seconds, multiplied by the beat multiplier only in MULTI_TENANT mode.
    """
    base_expiration = 300  # seconds

    if not MULTI_TENANT:
        return base_expiration

    try:
        beat_multiplier = ESARuntime.get_beat_multiplier()
    except Exception:
        beat_multiplier = CLOUD_BEAT_MULTIPLIER_DEFAULT

    return int(base_expiration * beat_multiplier)


def _is_external_group_sync_due(cc_pair: ConnectorCredentialPair) -> bool:
    """Returns boolean indicating if external group sync is due."""

    if cc_pair.access_type != AccessType.SYNC:
        task_logger.error(
            f"Received non-sync CC Pair {cc_pair.id} for external "
            f"group sync. Actual access type: {cc_pair.access_type}"
        )
        return False

    if cc_pair.status == ConnectorCredentialPairStatus.DELETING:
        task_logger.debug(
            f"Skipping group sync for CC Pair {cc_pair.id} - "
            f"CC Pair is being deleted"
        )
        return False

    sync_config = get_source_perm_sync_config(cc_pair.connector.source)
    if sync_config is None:
        task_logger.debug(
            f"Skipping group sync for CC Pair {cc_pair.id} - "
            f"no sync config found for {cc_pair.connector.source}"
        )
        return False

    if sync_config.group_sync_config is None:
        task_logger.debug(
            f"Skipping group sync for CC Pair {cc_pair.id} - "
            f"no group sync config found for {cc_pair.connector.source}"
        )
        return False

    # If the last sync is None, it has never been run so we run the sync
    last_ext_group_sync = cc_pair.last_time_external_group_sync
    if last_ext_group_sync is None:
        return True

    source_sync_period = sync_config.group_sync_config.group_sync_frequency

    # If the last sync is greater than the full fetch period, we run the sync
    next_sync = last_ext_group_sync + timedelta(seconds=source_sync_period)
    if datetime.now(timezone.utc) >= next_sync:
        return True

    return False


@shared_task(
    name=ESACeleryTask.CHECK_FOR_EXTERNAL_GROUP_SYNC,
    ignore_result=True,
    soft_time_limit=JOB_TIMEOUT,
    bind=True,
)
def check_for_external_group_sync(self: Task, *, tenant_id: str) -> bool | None:
    r = get_redis_client()
    r_replica = get_redis_replica_client()
    r_celery: Redis = self.app.broker_connection().channel().client  # type: ignore

    lock_beat: RedisLock = r.lock(
        ESARedisLocks.CHECK_CONNECTOR_EXTERNAL_GROUP_SYNC_BEAT_LOCK,
        timeout=CELERY_GENERIC_BEAT_LOCK_TIMEOUT,
    )

    if not lock_beat.acquire(blocking=False):
        task_logger.warning(
            f"Failed to acquire beat lock for external group sync: {tenant_id}"
        )
        return None

    try:
        cc_pair_ids_to_sync: list[int] = []
        with get_session_with_current_tenant() as db_session:
            cc_pairs = get_all_auto_sync_cc_pairs(db_session)

            # For some sources, we only want to sync one cc_pair per source type
            for source in get_all_cc_pair_agnostic_group_sync_sources():
                cc_pairs_to_dedupe = get_cc_pairs_by_source(
                    db_session,
                    source,
                    access_type=AccessType.SYNC,
                    status=ConnectorCredentialPairStatus.ACTIVE,
                )
                # dedupe cc_pairs to only keep the first one
                for cc_pair_to_remove in cc_pairs_to_dedupe[1:]:
                    cc_pairs = [
                        cc_pair
                        for cc_pair in cc_pairs
                        if cc_pair.id != cc_pair_to_remove.id
                    ]

            for cc_pair in cc_pairs:
                if _is_external_group_sync_due(cc_pair):
                    cc_pair_ids_to_sync.append(cc_pair.id)

        lock_beat.reacquire()
        for cc_pair_id in cc_pair_ids_to_sync:
            payload_id = try_creating_external_group_sync_task(
                self.app, cc_pair_id, r, tenant_id
            )
            if not payload_id:
                continue

            task_logger.info(
                f"External group sync queued: cc_pair={cc_pair_id} id={payload_id}"
            )

        lock_beat.reacquire()
        if not r.exists(ESARedisSignals.BLOCK_VALIDATE_EXTERNAL_GROUP_SYNC_FENCES):
            try:
                validate_external_group_sync_fences(
                    tenant_id, self.app, r, r_replica, r_celery, lock_beat
                )
            except Exception:
                task_logger.exception(
                    "Exception while validating external group sync fences"
                )

            r.set(
                ESARedisSignals.BLOCK_VALIDATE_EXTERNAL_GROUP_SYNC_FENCES,
                1,
                ex=_get_fence_validation_block_expiration(),
            )
    except SoftTimeLimitExceeded:
        task_logger.info(
            "Soft time limit exceeded, task is being terminated gracefully."
        )
    except Exception as e:
        error_msg = format_error_for_logging(e)
        task_logger.warning(
            f"Unexpected check_for_external_group_sync exception: tenant={tenant_id} {error_msg}"
        )
        task_logger.exception(f"Unexpected exception: tenant={tenant_id}")
    finally:
        if lock_beat.owned():
            lock_beat.release()

    task_logger.info(f"check_for_external_group_sync finished: tenant={tenant_id}")
    return True


def try_creating_external_group_sync_task(
    app: Celery,
    cc_pair_id: int,
    r: Redis,
    tenant_id: str,
) -> str | None:
    """Returns an int if syncing is needed. The int represents the number of sync tasks generated.
    Returns None if no syncing is required."""
    payload_id: str | None = None

    redis_connector = RedisConnector(tenant_id, cc_pair_id)

    try:
        if redis_connector.external_group_sync.fenced:
            logger.warning(
                f"Skipping external group sync for CC Pair {cc_pair_id} - already running."
            )
            return None

        redis_connector.external_group_sync.generator_clear()
        redis_connector.external_group_sync.taskset_clear()

        try:
            with get_session_with_current_tenant() as db_session:
                insert_sync_record(
                    db_session=db_session,
                    entity_id=cc_pair_id,
                    sync_type=SyncType.EXTERNAL_GROUP,
                )
        except Exception:
            task_logger.exception("insert_sync_record exceptioned.")

        redis_connector.external_group_sync.set_active()

        payload = RedisConnectorExternalGroupSyncPayload(
            id=make_short_id(),
            submitted=datetime.now(timezone.utc),
            started=None,
            celery_task_id=None,
        )
        redis_connector.external_group_sync.set_fence(payload)

        custom_task_id = f"{redis_connector.external_group_sync.taskset_key}_{uuid4()}"

        result = app.send_task(
            ESACeleryTask.CONNECTOR_EXTERNAL_GROUP_SYNC_GENERATOR_TASK,
            kwargs=dict(
                cc_pair_id=cc_pair_id,
                tenant_id=tenant_id,
            ),
            queue=ESACeleryQueues.CONNECTOR_EXTERNAL_GROUP_SYNC,
            task_id=custom_task_id,
            priority=ESACeleryPriority.MEDIUM,
        )

        payload.celery_task_id = result.id
        redis_connector.external_group_sync.set_fence(payload)

        payload_id = payload.id
    except Exception as e:
        error_msg = format_error_for_logging(e)
        task_logger.warning(
            f"Unexpected try_creating_external_group_sync_task exception: cc_pair={cc_pair_id} {error_msg}"
        )
        task_logger.exception(
            f"Unexpected exception while trying to create external group sync task: cc_pair={cc_pair_id}"
        )
        return None

    task_logger.info(
        f"try_creating_external_group_sync_task finished: cc_pair={cc_pair_id} payload_id={payload_id}"
    )
    return payload_id


@shared_task(
    name=ESACeleryTask.CONNECTOR_EXTERNAL_GROUP_SYNC_GENERATOR_TASK,
    acks_late=False,
    soft_time_limit=JOB_TIMEOUT,
    track_started=True,
    trail=False,
    bind=True,
)
def connector_external_group_sync_generator_task(
    self: Task,
    cc_pair_id: int,
    tenant_id: str,
) -> None:
    """
    External group sync task for a given connector credential pair
    This task assumes that the task has already been properly fenced
    """

    redis_connector = RedisConnector(tenant_id, cc_pair_id)

    r = get_redis_client()

    start = time.monotonic()
    while True:
        if time.monotonic() - start > CELERY_TASK_WAIT_FOR_FENCE_TIMEOUT:
            msg = (
                f"connector_external_group_sync_generator_task - timed out waiting for fence: "
                f"fence={redis_connector.external_group_sync.fence_key}"
            )
            emit_background_error(msg, cc_pair_id=cc_pair_id)
            raise ValueError(msg)

        if not redis_connector.external_group_sync.fenced:
            msg = (
                f"connector_external_group_sync_generator_task - fence not found: "
                f"fence={redis_connector.external_group_sync.fence_key}"
            )
            emit_background_error(msg, cc_pair_id=cc_pair_id)
            raise ValueError(msg)

        payload = redis_connector.external_group_sync.payload
        if not payload:
            msg = "connector_external_group_sync_generator_task: payload invalid or not found"
            emit_background_error(msg, cc_pair_id=cc_pair_id)
            raise ValueError(msg)

        if payload.celery_task_id is None:
            logger.info(
                f"connector_external_group_sync_generator_task - Waiting for fence: "
                f"fence={redis_connector.external_group_sync.fence_key}"
            )
            time.sleep(1)
            continue

        logger.info(
            f"connector_external_group_sync_generator_task - Fence found, continuing...: "
            f"fence={redis_connector.external_group_sync.fence_key} "
            f"payload_id={payload.id}"
        )
        break

    lock: RedisLock = r.lock(
        ESARedisLocks.CONNECTOR_EXTERNAL_GROUP_SYNC_LOCK_PREFIX
        + f"_{redis_connector.cc_pair_id}",
        timeout=CELERY_EXTERNAL_GROUP_SYNC_LOCK_TIMEOUT,
    )

    acquired = lock.acquire(blocking=False)
    if not acquired:
        msg = f"External group sync task already running, exiting...: cc_pair={cc_pair_id}"
        emit_background_error(msg, cc_pair_id=cc_pair_id)
        task_logger.error(msg)
        return None

    try:
        payload.started = datetime.now(timezone.utc)
        redis_connector.external_group_sync.set_fence(payload)

        _perform_external_group_sync(
            cc_pair_id=cc_pair_id,
            tenant_id=tenant_id,
        )

        with get_session_with_current_tenant() as db_session:
            update_sync_record_status(
                db_session=db_session,
                entity_id=cc_pair_id,
                sync_type=SyncType.EXTERNAL_GROUP,
                sync_status=SyncStatus.SUCCESS,
            )
    except Exception as e:
        error_msg = format_error_for_logging(e)
        task_logger.warning(
            f"External group sync exceptioned: cc_pair={cc_pair_id} payload_id={payload.id} {error_msg}"
        )
        task_logger.exception(
            f"External group sync exceptioned: cc_pair={cc_pair_id} payload_id={payload.id}"
        )

        msg = f"External group sync exceptioned: cc_pair={cc_pair_id} payload_id={payload.id}"
        task_logger.exception(msg)
        emit_background_error(msg + f"\n\n{e}", cc_pair_id=cc_pair_id)

        with get_session_with_current_tenant() as db_session:
            update_sync_record_status(
                db_session=db_session,
                entity_id=cc_pair_id,
                sync_type=SyncType.EXTERNAL_GROUP,
                sync_status=SyncStatus.FAILED,
            )

        redis_connector.external_group_sync.generator_clear()
        redis_connector.external_group_sync.taskset_clear()
        raise e
    finally:
        redis_connector.external_group_sync.set_fence(None)
        if lock.owned():
            lock.release()

    task_logger.info(
        f"External group sync finished: cc_pair={cc_pair_id} payload_id={payload.id}"
    )


def _perform_external_group_sync(
    cc_pair_id: int,
    tenant_id: str,
) -> None:
    # Create attempt record at the start
    with get_session_with_current_tenant() as db_session:
        attempt_id = create_external_group_sync_attempt(
            connector_credential_pair_id=cc_pair_id,
            db_session=db_session,
        )
        logger.info(
            f"Created external group sync attempt: {attempt_id} for cc_pair={cc_pair_id}"
        )

    with get_session_with_current_tenant() as db_session:
        cc_pair = get_connector_credential_pair_from_id(
            db_session=db_session,
            cc_pair_id=cc_pair_id,
            eager_load_credential=True,
        )
        if cc_pair is None:
            raise ValueError(f"No connector credential pair found for id: {cc_pair_id}")

        source_type = cc_pair.connector.source
        sync_config = get_source_perm_sync_config(source_type)
        if sync_config is None:
            msg = f"No sync config found for {source_type} for cc_pair: {cc_pair_id}"
            emit_background_error(msg, cc_pair_id=cc_pair_id)
            _fail_external_group_sync_attempt(attempt_id, msg)
            raise ValueError(msg)

        if sync_config.group_sync_config is None:
            msg = f"No group sync config found for {source_type} for cc_pair: {cc_pair_id}"
            emit_background_error(msg, cc_pair_id=cc_pair_id)
            _fail_external_group_sync_attempt(attempt_id, msg)
            raise ValueError(msg)

        ext_group_sync_func = sync_config.group_sync_config.group_sync_func

        logger.info(
            f"Marking old external groups as stale for {source_type} for cc_pair: {cc_pair_id}"
        )
        mark_old_external_groups_as_stale(db_session, cc_pair_id)

        # Mark attempt as in progress
        mark_external_group_sync_attempt_in_progress(attempt_id, db_session)
        logger.info(f"Marked external group sync attempt {attempt_id} as in progress")

        logger.info(
            f"Syncing external groups for {source_type} for cc_pair: {cc_pair_id}"
        )
        external_user_group_batch: list[ExternalUserGroup] = []
        seen_users: set[str] = set()
        total_groups_processed = 0
        total_group_memberships_synced = 0
        try:
            external_user_group_generator = ext_group_sync_func(tenant_id, cc_pair)
            for external_user_group in external_user_group_generator:
                external_user_group_batch.append(external_user_group)

                total_groups_processed += 1
                total_group_memberships_synced += len(external_user_group.user_emails)
                seen_users = seen_users.union(external_user_group.user_emails)

                if len(external_user_group_batch) >= _EXTERNAL_GROUP_BATCH_SIZE:
                    logger.debug(
                        f"New external user groups: {external_user_group_batch}"
                    )
                    upsert_external_groups(
                        db_session=db_session,
                        cc_pair_id=cc_pair_id,
                        external_groups=external_user_group_batch,
                        source=cc_pair.connector.source,
                    )
                    external_user_group_batch = []

            if external_user_group_batch:
                logger.debug(f"New external user groups: {external_user_group_batch}")
                upsert_external_groups(
                    db_session=db_session,
                    cc_pair_id=cc_pair_id,
                    external_groups=external_user_group_batch,
                    source=cc_pair.connector.source,
                )
        except Exception as e:
            format_error_for_logging(e)

            mark_external_group_sync_attempt_failed(
                attempt_id, db_session, error_message=str(e)
            )

            logger.exception(
                f"Error syncing external groups for {source_type} for cc_pair: {cc_pair_id} {e}"
            )
            raise e

        logger.info(
            f"Removing stale external groups for {source_type} for cc_pair: {cc_pair_id}"
        )
        remove_stale_external_groups(db_session, cc_pair_id)

        total_users_processed = len(seen_users)

        complete_external_group_sync_attempt(
            db_session=db_session,
            attempt_id=attempt_id,
            total_users_processed=total_users_processed,
            total_groups_processed=total_groups_processed,
            total_group_memberships_synced=total_group_memberships_synced,
            errors_encountered=0,
        )
        logger.info(
            f"Completed external group sync attempt {attempt_id}: "
            f"{total_groups_processed} groups, {total_users_processed} users, "
            f"{total_group_memberships_synced} memberships"
        )

        mark_all_relevant_cc_pairs_as_external_group_synced(db_session, cc_pair)


def validate_external_group_sync_fences(
    tenant_id: str,
    celery_app: Celery,
    r: Redis,
    r_replica: Redis,
    r_celery: Redis,
    lock_beat: RedisLock,
) -> None:
    reserved_tasks = celery_get_unacked_task_ids(
        ESACeleryQueues.CONNECTOR_EXTERNAL_GROUP_SYNC, r_celery
    )

    lock_beat.reacquire()
    keys = cast(set[Any], r_replica.smembers(ESARedisConstants.ACTIVE_FENCES))
    for key in keys:
        key_bytes = cast(bytes, key)
        key_str = key_bytes.decode("utf-8")
        if not key_str.startswith(RedisConnectorExternalGroupSync.FENCE_PREFIX):
            continue

        validate_external_group_sync_fence(
            tenant_id,
            key_bytes,
            reserved_tasks,
            r_celery,
        )

        lock_beat.reacquire()
    return


def validate_external_group_sync_fence(
    tenant_id: str,
    key_bytes: bytes,
    reserved_tasks: set[str],
    r_celery: Redis,
) -> None:
    """Checks for the error condition where a fence is set but celery tasks don't exist."""
    fence_key = key_bytes.decode("utf-8")
    cc_pair_id_str = RedisConnector.get_id_from_fence_key(fence_key)
    if cc_pair_id_str is None:
        msg = (
            f"validate_external_group_sync_fence - could not parse id from {fence_key}"
        )
        emit_background_error(msg)
        task_logger.error(msg)
        return

    cc_pair_id = int(cc_pair_id_str)

    redis_connector = RedisConnector(tenant_id, int(cc_pair_id))

    if not redis_connector.external_group_sync.fenced:
        return

    try:
        payload = redis_connector.external_group_sync.payload
    except ValidationError:
        msg = (
            "validate_external_group_sync_fence - "
            "Resetting fence because fence schema is out of date: "
            f"cc_pair={cc_pair_id} "
            f"fence={fence_key}"
        )
        task_logger.exception(msg)
        emit_background_error(msg, cc_pair_id=cc_pair_id)

        redis_connector.external_group_sync.reset()
        return

    if not payload:
        return

    if not payload.celery_task_id:
        return

    # OK, there's actually something for us to validate
    found = celery_find_task(
        payload.celery_task_id, ESACeleryQueues.CONNECTOR_EXTERNAL_GROUP_SYNC, r_celery
    )
    if found:
        return

    if payload.celery_task_id in reserved_tasks:
        return

    # Clean up orphaned fence
    emit_background_error(
        message=(
            "validate_external_group_sync_fence - "
            "Resetting fence because no associated celery tasks were found: "
            f"cc_pair={cc_pair_id} "
            f"fence={fence_key} "
            f"payload_id={payload.id}"
        ),
        cc_pair_id=cc_pair_id,
    )

    redis_connector.external_group_sync.reset()
    return
