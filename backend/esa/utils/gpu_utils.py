import os
from functools import lru_cache

import requests
from retry import retry

from esa.utils.logger import setup_logger
from shared_configs.configs import INDEXING_MODEL_SERVER_HOST
from shared_configs.configs import INDEXING_MODEL_SERVER_PORT
from shared_configs.configs import MODEL_SERVER_HOST
from shared_configs.configs import MODEL_SERVER_PORT

logger = setup_logger()


def _get_gpu_status_from_model_server(indexing: bool) -> bool:
    if os.environ.get("DISABLE_MODEL_SERVER", "").lower() == "true":
        logger.info("DISABLE_MODEL_SERVER is set, assuming no GPU available")
        return False
    if indexing:
        model_server_url = f"{INDEXING_MODEL_SERVER_HOST}:{INDEXING_MODEL_SERVER_PORT}"
    else:
        model_server_url = f"{MODEL_SERVER_HOST}:{MODEL_SERVER_PORT}"

    if "http" not in model_server_url:
        model_server_url = f"http://{model_server_url}"

    try:
        response = requests.get(f"{model_server_url}/api/gpu-status", timeout=10)
        response.raise_for_status()
        gpu_status = response.json()
        return gpu_status["gpu_available"]
    except requests.RequestException as e:
        logger.error(f"Error: Unable to fetch GPU status. Error: {str(e)}")
        raise  # Re-raise exception to trigger a retry


def gpu_status_request(indexing: bool) -> bool:
    """Request GPU status with retries. Returns False if model server unavailable."""
    try:
        # Try a few times with backoff
        for attempt in range(3):
            try:
                return _get_gpu_status_from_model_server(indexing)
            except requests.RequestException:
                if attempt < 2:
                    import time
                    time.sleep(3)  # Wait 3 seconds between retries
                    continue
                raise
    except requests.RequestException:
        # Model server is not available - gracefully return False instead of crashing
        logger.warning("Model server not available, assuming no GPU. Backend will continue without AI features.")
        return False


@lru_cache(maxsize=1)
def fast_gpu_status_request(indexing: bool) -> bool:
    """For use in sync flows, where we don't want to retry / we want to cache this."""
    return gpu_status_request(indexing=indexing)

