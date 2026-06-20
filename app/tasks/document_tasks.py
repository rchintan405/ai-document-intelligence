import logging
from datetime import datetime, timezone

from celery import Task
from sqlalchemy.orm import Session

from app.workers.celery_app import celery_app
from app.db.session import SessionLocal
from app.models.document import Document, DocumentStatus
from app.services.document_parser import extract_text, truncate_text_for_ai
from app.services.ai import openai_service

logger = logging.getLogger(__name__)


class DatabaseTask(Task):
    """Base task class that provides a database session."""
    _db: Session = None

    @property
    def db(self) -> Session:
        if self._db is None:
            self._db = SessionLocal()
        return self._db

    def after_return(self, *args, **kwargs):
        if self._db is not None:
            self._db.close()
            self._db = None


@celery_app.task(
    bind=True,
    base=DatabaseTask,
    name="process_document",
    max_retries=3,
    default_retry_delay=10,
    soft_time_limit=120,
    time_limit=150,
)
def process_document_task(self, document_id: int) -> dict:
    """
    Full AI processing pipeline for an uploaded document.

    Pipeline steps:
      1. Extract text from PDF/DOCX
      2. Classify document type
      3. Generate summary
      4. Extract key points
      5. Analyze sentiment
      6. Generate Q&A pairs
      7. Extract named entities
      8. Save all results to DB
    """
    logger.info(f"Starting AI processing for document_id={document_id}")

    # ── Load document ───────────────────────────────────────────
    doc: Document = self.db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        logger.error(f"Document {document_id} not found")
        return {"status": "error", "message": "Document not found"}

    # Mark as processing
    doc.status = DocumentStatus.PROCESSING
    self.db.commit()

    try:
        # ── Step 1: Extract text ─────────────────────────────────
        logger.info(f"[{document_id}] Extracting text from {doc.file_type}")
        raw_text, page_count = extract_text(doc.file_path, doc.file_type)
        word_count = len(raw_text.split())
        doc.word_count = word_count
        doc.page_count = page_count
        self.db.commit()

        # Truncate for AI to avoid token overflows
        ai_text = truncate_text_for_ai(raw_text)
        total_tokens = 0

        # ── Step 2: Classify document type ──────────────────────
        logger.info(f"[{document_id}] Classifying document type")
        doc_type, tokens = openai_service.classify_document(ai_text)
        doc.document_type = doc_type
        total_tokens += tokens

        # ── Step 3: Summarize ────────────────────────────────────
        logger.info(f"[{document_id}] Generating summary")
        summary, tokens = openai_service.summarize_document(ai_text)
        doc.summary = summary
        total_tokens += tokens

        # ── Step 4: Key points ───────────────────────────────────
        logger.info(f"[{document_id}] Extracting key points")
        key_points, tokens = openai_service.extract_key_points(ai_text)
        doc.key_points = key_points
        total_tokens += tokens

        # ── Step 5: Sentiment analysis ───────────────────────────
        logger.info(f"[{document_id}] Analyzing sentiment")
        sentiment, sentiment_score, tokens = openai_service.analyze_sentiment(ai_text)
        doc.sentiment = sentiment
        doc.sentiment_score = sentiment_score
        total_tokens += tokens

        # ── Step 6: Q&A pairs ────────────────────────────────────
        logger.info(f"[{document_id}] Generating Q&A pairs")
        qa_pairs, tokens = openai_service.generate_qa_pairs(ai_text)
        doc.qa_pairs = qa_pairs
        total_tokens += tokens

        # ── Step 7: Named entity extraction ─────────────────────
        logger.info(f"[{document_id}] Extracting entities")
        entities, tokens = openai_service.extract_entities(ai_text)
        doc.extracted_entities = entities
        total_tokens += tokens

        # ── Finalize ─────────────────────────────────────────────
        doc.status = DocumentStatus.COMPLETED
        doc.ai_tokens_used = total_tokens
        doc.processed_at = datetime.now(timezone.utc)
        self.db.commit()

        logger.info(f"[{document_id}] Processing complete. Total tokens: {total_tokens}")
        return {
            "status": "completed",
            "document_id": document_id,
            "tokens_used": total_tokens,
        }

    except Exception as exc:
        logger.error(f"[{document_id}] Processing failed: {exc}", exc_info=True)
        doc.status = DocumentStatus.FAILED
        doc.error_message = str(exc)
        self.db.commit()

        # Retry on transient errors
        raise self.retry(exc=exc)
