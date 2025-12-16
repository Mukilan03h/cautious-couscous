"""
Telemetry utilities for MyPlatform.
Ported from ee/esa/utils/telemetry.py

Provides event tracking and analytics via PostHog.
"""
from myplatform.utils.posthog_client import posthog, capture_event, flush
from esa.utils.logger import setup_logger

logger = setup_logger()


def event_telemetry(
    distinct_id: str, event: str, properties: dict | None = None
) -> None:
    """Capture and send an event to PostHog, flushing immediately."""
    logger.info(f"Capturing PostHog event: {distinct_id} {event} {properties}")
    try:
        posthog.capture(distinct_id, event, properties)
        posthog.flush()
    except Exception as e:
        logger.error(f"Error capturing PostHog event: {e}")


def track_feature_usage(
    user_id: str,
    feature_name: str,
    metadata: dict | None = None,
) -> None:
    """
    Track usage of a specific feature.
    
    Args:
        user_id: User identifier
        feature_name: Name of the feature being used
        metadata: Additional metadata about the usage
    """
    props = {"feature": feature_name}
    if metadata:
        props.update(metadata)
    capture_event(user_id, "feature_used", props)


def track_error(
    user_id: str | None,
    error_type: str,
    error_message: str,
    context: dict | None = None,
) -> None:
    """
    Track an error occurrence.
    
    Args:
        user_id: User identifier (optional for anonymous users)
        error_type: Type/category of error
        error_message: Error message
        context: Additional error context
    """
    props = {
        "error_type": error_type,
        "error_message": error_message,
    }
    if context:
        props.update(context)
    capture_event(user_id or "anonymous", "error_occurred", props)
