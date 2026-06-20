from datetime import datetime
from typing import Optional, List, Any
from pydantic import BaseModel

from app.models.document import DocumentStatus, DocumentType, SentimentLabel


class QAPair(BaseModel):
    question: str
    answer: str


class ExtractedEntities(BaseModel):
    people: List[str] = []
    organizations: List[str] = []
    dates: List[str] = []
    locations: List[str] = []


class DocumentUploadResponse(BaseModel):
    id: int
    filename: str
    original_filename: str
    file_size: int
    file_type: str
    status: DocumentStatus
    celery_task_id: Optional[str]
    created_at: datetime
    message: str

    model_config = {"from_attributes": True}


class DocumentStatusResponse(BaseModel):
    id: int
    original_filename: str
    status: DocumentStatus
    celery_task_id: Optional[str]
    error_message: Optional[str]
    created_at: datetime
    processed_at: Optional[datetime]

    model_config = {"from_attributes": True}


class DocumentResultResponse(BaseModel):
    id: int
    original_filename: str
    file_type: str
    file_size: int
    word_count: Optional[int]
    page_count: Optional[int]
    status: DocumentStatus

    # AI Results
    document_type: Optional[DocumentType]
    summary: Optional[str]
    key_points: Optional[List[str]]
    sentiment: Optional[SentimentLabel]
    sentiment_score: Optional[float]
    qa_pairs: Optional[List[Any]]
    extracted_entities: Optional[Any]
    ai_tokens_used: Optional[int]

    created_at: datetime
    processed_at: Optional[datetime]

    model_config = {"from_attributes": True}


class AskQuestionRequest(BaseModel):
    question: str


class AskQuestionResponse(BaseModel):
    document_id: int
    question: str
    answer: str
    tokens_used: int
