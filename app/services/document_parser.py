import os
from pathlib import Path

import aiofiles


async def save_upload_file(file_content: bytes, destination: str) -> None:
    """Save uploaded file bytes to disk."""
    os.makedirs(os.path.dirname(destination), exist_ok=True)
    async with aiofiles.open(destination, "wb") as f:
        await f.write(file_content)


def extract_text_from_pdf(file_path: str) -> tuple[str, int]:
    """Extract text and page count from a PDF file."""
    from pypdf import PdfReader
    reader = PdfReader(file_path)
    pages = len(reader.pages)
    text = "\n\n".join(
        page.extract_text() or "" for page in reader.pages
    )
    return text.strip(), pages


def extract_text_from_docx(file_path: str) -> tuple[str, int]:
    """Extract text and estimated page count from a DOCX file."""
    from docx import Document
    doc = Document(file_path)
    paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
    text = "\n\n".join(paragraphs)
    # Estimate pages: ~500 words per page
    word_count = len(text.split())
    estimated_pages = max(1, round(word_count / 500))
    return text.strip(), estimated_pages


def extract_text(file_path: str, file_type: str) -> tuple[str, int]:
    """Route to the correct extractor based on file type."""
    if file_type == "pdf":
        return extract_text_from_pdf(file_path)
    elif file_type == "docx":
        return extract_text_from_docx(file_path)
    else:
        raise ValueError(f"Unsupported file type: {file_type}")


def truncate_text_for_ai(text: str, max_tokens: int = 6000) -> str:
    """
    Truncate text to stay within token budget.
    Rough estimate: 1 token ≈ 4 characters.
    """
    max_chars = max_tokens * 4
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "\n\n[... document truncated for processing ...]"
