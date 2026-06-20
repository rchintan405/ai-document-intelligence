import json
import logging
from typing import Optional

from openai import OpenAI

from app.core.config import settings

logger = logging.getLogger(__name__)
client = OpenAI(api_key=settings.OPENAI_API_KEY)


def _chat(system: str, user: str, json_mode: bool = False) -> tuple[str, int]:
    """Base OpenAI chat call. Returns (content, tokens_used)."""
    kwargs = {
        "model": settings.OPENAI_MODEL,
        "max_tokens": settings.OPENAI_MAX_TOKENS,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    }
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}

    response = client.chat.completions.create(**kwargs)
    content = response.choices[0].message.content or ""
    tokens = response.usage.total_tokens
    return content, tokens


def classify_document(text: str) -> tuple[str, int]:
    """Classify document type: invoice, contract, resume, report, article, legal, other."""
    system = (
        "You are a document classification expert. "
        "Classify the document into exactly one of these types: "
        "invoice, contract, resume, report, article, legal, other. "
        "Respond with ONLY the type word, nothing else."
    )
    result, tokens = _chat(system, f"Document content:\n\n{text[:3000]}")
    doc_type = result.strip().lower()
    valid = {"invoice", "contract", "resume", "report", "article", "legal", "other"}
    return doc_type if doc_type in valid else "other", tokens


def summarize_document(text: str) -> tuple[str, int]:
    """Generate a concise, professional summary of the document."""
    system = (
        "You are an expert document analyst. "
        "Write a clear, professional summary of the document in 3-5 sentences. "
        "Focus on the main purpose, key findings, and important conclusions."
    )
    return _chat(system, f"Document:\n\n{text}")


def extract_key_points(text: str) -> tuple[list[str], int]:
    """Extract 5-8 key bullet points from the document."""
    system = (
        "You are an expert document analyst. "
        "Extract the 5-8 most important key points from this document. "
        'Respond ONLY with a JSON object: {"key_points": ["point 1", "point 2", ...]}'
    )
    result, tokens = _chat(system, f"Document:\n\n{text}", json_mode=True)
    try:
        data = json.loads(result)
        return data.get("key_points", []), tokens
    except Exception:
        return [], tokens


def analyze_sentiment(text: str) -> tuple[str, float, int]:
    """
    Analyze document sentiment.
    Returns (label, score, tokens_used).
    Label: positive | neutral | negative
    Score: -1.0 (very negative) to 1.0 (very positive)
    """
    system = (
        "You are a sentiment analysis expert. "
        "Analyze the overall sentiment of this document. "
        'Respond ONLY with a JSON object: {"sentiment": "positive|neutral|negative", "score": <float between -1.0 and 1.0>}'
    )
    result, tokens = _chat(system, f"Document:\n\n{text[:4000]}", json_mode=True)
    try:
        data = json.loads(result)
        label = data.get("sentiment", "neutral")
        score = float(data.get("score", 0.0))
        score = max(-1.0, min(1.0, score))
        return label, score, tokens
    except Exception:
        return "neutral", 0.0, tokens


def generate_qa_pairs(text: str) -> tuple[list[dict], int]:
    """Generate 5 insightful Q&A pairs from the document content."""
    system = (
        "You are an expert at creating educational Q&A pairs from documents. "
        "Generate exactly 5 meaningful question and answer pairs based on the document. "
        "Questions should test understanding of key concepts. "
        'Respond ONLY with a JSON object: {"qa_pairs": [{"question": "...", "answer": "..."}, ...]}'
    )
    result, tokens = _chat(system, f"Document:\n\n{text}", json_mode=True)
    try:
        data = json.loads(result)
        return data.get("qa_pairs", []), tokens
    except Exception:
        return [], tokens


def extract_entities(text: str) -> tuple[dict, int]:
    """Extract named entities: people, organizations, dates, locations."""
    system = (
        "You are a named entity recognition expert. "
        "Extract all named entities from this document. "
        'Respond ONLY with a JSON object: '
        '{"people": [...], "organizations": [...], "dates": [...], "locations": [...]}'
    )
    result, tokens = _chat(system, f"Document:\n\n{text[:4000]}", json_mode=True)
    try:
        data = json.loads(result)
        return {
            "people": data.get("people", []),
            "organizations": data.get("organizations", []),
            "dates": data.get("dates", []),
            "locations": data.get("locations", []),
        }, tokens
    except Exception:
        return {"people": [], "organizations": [], "dates": [], "locations": []}, tokens


def answer_question(document_text: str, question: str) -> tuple[str, int]:
    """Answer a free-form question about the document content (RAG-lite)."""
    system = (
        "You are a document Q&A assistant. "
        "Answer the user's question based ONLY on the provided document content. "
        "If the answer is not in the document, say so clearly. "
        "Be concise and accurate."
    )
    user_prompt = f"Document:\n\n{document_text}\n\n---\n\nQuestion: {question}"
    return _chat(system, user_prompt)
