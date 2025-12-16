from typing import Any

from celery import shared_task
from celery import Task

from esa.configs.app_configs import JOB_TIMEOUT
from esa.configs.constants import ESACeleryTask
from esa.evals.eval import run_eval
from esa.evals.models import EvalConfigurationOptions
from esa.utils.logger import setup_logger

logger = setup_logger()


@shared_task(
    name=ESACeleryTask.EVAL_RUN_TASK,
    ignore_result=True,
    soft_time_limit=JOB_TIMEOUT,
    bind=True,
    trail=False,
)
def eval_run_task(
    self: Task,
    *,
    configuration_dict: dict[str, Any],
) -> None:
    """Background task to run an evaluation with the given configuration"""
    try:
        configuration = EvalConfigurationOptions.model_validate(configuration_dict)
        run_eval(configuration, remote_dataset_name=configuration.dataset_name)
        logger.info("Successfully completed eval run task")

    except Exception:
        logger.error("Failed to run eval task")
        raise
