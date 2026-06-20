import enum
from sqlalchemy import Column, Integer, String, Text, Float, DateTime, ForeignKey, Enum, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.session import Base


class DocumentStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class DocumentType(str, enum.Enum):
    INVOICE = "invoice"
    CONTRACT = "contract"
    RESUME = "resume"
    REPORT = "report"
    ARTICLE = "article"
    LEGAL = "legal"
    OTHER = "other"


class SentimentLabel(str, enum.Enum):
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"


class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(255), nullable=False)
    original_filename = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_size = Column(Integer, nullable=False)           # bytes
    file_type = Column(String(10), nullable=False)        # pdf / docx
    word_count = Column(Integer, nullable=True)
    page_count = Column(Integer, nullable=True)

    # Job tracking
    status = Column(Enum(DocumentStatus), default=DocumentStatus.PENDING, nullable=False)
    celery_task_id = Column(String(255), nullable=True, index=True)
    error_message = Column(Text, nullable=True)

    # AI Results
    document_type = Column(Enum(DocumentType), nullable=True)
    summary = Column(Text, nullable=True)
    key_points = Column(JSON, nullable=True)              # list of strings
    sentiment = Column(Enum(SentimentLabel), nullable=True)
    sentiment_score = Column(Float, nullable=True)        # -1.0 to 1.0
    qa_pairs = Column(JSON, nullable=True)                # list of {q, a}
    extracted_entities = Column(JSON, nullable=True)      # {people, orgs, dates}
    ai_tokens_used = Column(Integer, nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    processed_at = Column(DateTime(timezone=True), nullable=True)

    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    owner = relationship("User", back_populates="documents")

    def __repr__(self):
        return f"<Document {self.original_filename} [{self.status}]>"
