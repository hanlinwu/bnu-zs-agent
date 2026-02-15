"""Celery task: document parsing."""

import logging
from app.tasks.celery_app import celery

logger = logging.getLogger(__name__)


@celery.task(name="app.tasks.parse_task.parse_document")
def parse_document(document_id: str, file_path: str, file_type: str):
    """Parse an uploaded document and update its status."""
    from app.services.file_parser_service import parse_file, chunk_text

    logger.info("Parsing document %s (%s)", document_id, file_type)

    try:
        text = parse_file(file_path, file_type)
        chunks = chunk_text(text)
        logger.info("Document %s parsed: %d chunks", document_id, len(chunks))
        return {"document_id": document_id, "chunks": chunks, "status": "parsed"}
    except Exception as e:
        logger.error("Failed to parse document %s: %s", document_id, e)
        return {"document_id": document_id, "error": str(e), "status": "failed"}
