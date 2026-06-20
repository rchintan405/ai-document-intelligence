import asyncio
import json
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

from app.core.security import decode_token
from app.db.session import SessionLocal
from app.models.document import Document, DocumentStatus

logger = logging.getLogger(__name__)
router = APIRouter(tags=["WebSocket"])

POLL_INTERVAL = 2  # seconds between DB polls


@router.websocket("/ws/documents/{document_id}/status")
async def document_status_ws(websocket: WebSocket, document_id: int):
    """
    WebSocket endpoint for real-time document processing updates.

    Client connects and receives status updates every 2 seconds
    until processing is complete or fails.

    Protocol:
      - Send JWT token as first message after connecting
      - Receive JSON status frames until terminal state
      - Connection closes automatically on completion/failure

    Example frame:
      {"document_id": 1, "status": "processing", "progress": "Analyzing sentiment..."}
    """
    await websocket.accept()
    db: Session = SessionLocal()

    try:
        # ── Auth: receive token as first message ─────────────────
        try:
            auth_message = await asyncio.wait_for(websocket.receive_text(), timeout=10.0)
        except asyncio.TimeoutError:
            await websocket.send_json({"error": "Authentication timeout"})
            await websocket.close(code=1008)
            return

        payload = decode_token(auth_message.strip())
        if not payload:
            await websocket.send_json({"error": "Invalid or expired token"})
            await websocket.close(code=1008)
            return

        user_id = int(payload.get("sub", 0))

        # ── Verify document ownership ─────────────────────────────
        doc = db.query(Document).filter(
            Document.id == document_id,
            Document.owner_id == user_id,
        ).first()

        if not doc:
            await websocket.send_json({"error": "Document not found or access denied"})
            await websocket.close(code=1008)
            return

        await websocket.send_json({
            "document_id": document_id,
            "status": doc.status,
            "message": "Connected. Listening for processing updates...",
        })

        # ── Poll loop ─────────────────────────────────────────────
        terminal_states = {DocumentStatus.COMPLETED, DocumentStatus.FAILED}

        while True:
            db.refresh(doc)

            frame = {
                "document_id": document_id,
                "status": doc.status,
                "filename": doc.original_filename,
            }

            if doc.status == DocumentStatus.PENDING:
                frame["message"] = "Queued for processing..."

            elif doc.status == DocumentStatus.PROCESSING:
                frame["message"] = "AI is analyzing your document..."
                if doc.word_count:
                    frame["word_count"] = doc.word_count
                if doc.page_count:
                    frame["page_count"] = doc.page_count

            elif doc.status == DocumentStatus.COMPLETED:
                frame["message"] = "Processing complete!"
                frame["document_type"] = doc.document_type
                frame["sentiment"] = doc.sentiment
                frame["ai_tokens_used"] = doc.ai_tokens_used
                frame["processed_at"] = doc.processed_at.isoformat() if doc.processed_at else None

            elif doc.status == DocumentStatus.FAILED:
                frame["message"] = "Processing failed."
                frame["error"] = doc.error_message

            await websocket.send_json(frame)

            if doc.status in terminal_states:
                logger.info(f"WS: document {document_id} reached terminal state {doc.status}")
                break

            await asyncio.sleep(POLL_INTERVAL)

    except WebSocketDisconnect:
        logger.info(f"WS: client disconnected from document {document_id}")
    except Exception as e:
        logger.error(f"WS error for document {document_id}: {e}", exc_info=True)
        try:
            await websocket.send_json({"error": "Internal server error"})
        except Exception:
            pass
    finally:
        db.close()
        try:
            await websocket.close()
        except Exception:
            pass
