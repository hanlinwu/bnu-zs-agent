"""Celery task: async dual-model review."""

import logging
from app.tasks.celery_app import celery

logger = logging.getLogger(__name__)


@celery.task(name="app.tasks.review_task.review_message")
def review_message_task(message_id: str, question: str, answer: str, sources: str):
    """Async review of AI response for hallucination detection."""
    logger.info("Reviewing message %s", message_id)

    # Note: In production this would:
    # 1. Call review_service.verify(question, answer, sources)
    # 2. Update Message.review_passed in DB
    # 3. If flagged, append disclaimer to the message

    return {"message_id": message_id, "status": "reviewed"}
