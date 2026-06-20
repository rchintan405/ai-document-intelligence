import os
import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Request, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.limiter import limiter
from app.db.session import get_db
from app.models.document import Document, DocumentStatus
from app.models.user import User
from app.schemas.document import (
    DocumentUploadResponse,
    DocumentStatusResponse,
    DocumentResultResponse,
    AskQuestionRequest,
    AskQuestionResponse,
)
from app.services.document_parser import save_upload_file, extract_text, truncate_text_for_ai
from app.services.ai import openai_service
from app.tasks.document_tasks import process_document_task
from app.api.v1.dependencies import get_current_user

router = APIRouter(prefix="/documents", tags=["Documents"])


@router.post("/upload", response_model=DocumentUploadResponse, status_code=status.HTTP_202_ACCEPTED)
@limiter.limit(f"{settings.RATE_LIMIT_PER_MINUTE}/minute")
async def upload_document(
    request: Request,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Upload a PDF or DOCX document for AI processing.

    - File is saved to disk
    - A Celery background task is queued immediately
    - Returns document ID and task ID for polling
    """
    # Validate file extension
    ext = file.filename.split(".")[-1].lower() if "." in file.filename else ""
    if ext not in settings.allowed_extensions_list:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type. Allowed: {', '.join(settings.allowed_extensions_list)}",
        )

    # Read and validate file size
    content = await file.read()
    if len(content) > settings.max_file_size_bytes:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Maximum allowed size: {settings.MAX_FILE_SIZE_MB}MB",
        )

    # Save file with unique name to avoid collisions
    unique_name = f"{uuid.uuid4().hex}.{ext}"
    upload_path = os.path.join(settings.UPLOAD_DIR, str(current_user.id), unique_name)
    await save_upload_file(content, upload_path)

    # Create DB record
    doc = Document(
        filename=unique_name,
        original_filename=file.filename,
        file_path=upload_path,
        file_size=len(content),
        file_type=ext,
        status=DocumentStatus.PENDING,
        owner_id=current_user.id,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    # Dispatch Celery task
    task = process_document_task.delay(doc.id)
    doc.celery_task_id = task.id
    db.commit()
    db.refresh(doc)

    return DocumentUploadResponse(
        **{c.name: getattr(doc, c.name) for c in doc.__table__.columns},
        message="Document uploaded successfully. AI processing has started.",
    )


@router.get("/", response_model=List[DocumentResultResponse])
def list_documents(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    skip: int = 0,
    limit: int = 20,
):
    """List all documents uploaded by the current user."""
    return (
        db.query(Document)
        .filter(Document.owner_id == current_user.id)
        .order_by(Document.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


@router.get("/{document_id}/status", response_model=DocumentStatusResponse)
def get_document_status(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Poll the processing status of a document."""
    doc = db.query(Document).filter(
        Document.id == document_id,
        Document.owner_id == current_user.id,
    ).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc


@router.get("/{document_id}/results", response_model=DocumentResultResponse)
def get_document_results(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get the full AI analysis results for a completed document."""
    doc = db.query(Document).filter(
        Document.id == document_id,
        Document.owner_id == current_user.id,
    ).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    if doc.status != DocumentStatus.COMPLETED:
        raise HTTPException(
            status_code=400,
            detail=f"Document is not ready. Current status: {doc.status}",
        )
    return doc


@router.post("/{document_id}/ask", response_model=AskQuestionResponse)
@limiter.limit("10/minute")
async def ask_question(
    request: Request,
    document_id: int,
    body: AskQuestionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Ask a free-form question about a processed document.

    Uses RAG-lite: the document text is sent as context to GPT,
    which answers based only on the document content.
    """
    doc = db.query(Document).filter(
        Document.id == document_id,
        Document.owner_id == current_user.id,
    ).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    if doc.status != DocumentStatus.COMPLETED:
        raise HTTPException(status_code=400, detail="Document must be fully processed first")

    # Re-extract text for Q&A context
    raw_text, _ = extract_text(doc.file_path, doc.file_type)
    ai_text = truncate_text_for_ai(raw_text)

    answer, tokens_used = openai_service.answer_question(ai_text, body.question)

    return AskQuestionResponse(
        document_id=doc.id,
        question=body.question,
        answer=answer,
        tokens_used=tokens_used,
    )


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a document and its file from disk."""
    doc = db.query(Document).filter(
        Document.id == document_id,
        Document.owner_id == current_user.id,
    ).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    # Remove file from disk
    if os.path.exists(doc.file_path):
        os.remove(doc.file_path)

    db.delete(doc)
    db.commit()
