import json
import pytest
from unittest.mock import patch, MagicMock


def make_mock_response(content: str, tokens: int = 100):
    """Build a mock OpenAI response object."""
    mock = MagicMock()
    mock.choices[0].message.content = content
    mock.usage.total_tokens = tokens
    return mock


@patch("app.services.ai.openai_service.client")
def test_classify_document(mock_client):
    mock_client.chat.completions.create.return_value = make_mock_response("invoice")
    from app.services.ai.openai_service import classify_document
    doc_type, tokens = classify_document("This is an invoice for services rendered...")
    assert doc_type == "invoice"
    assert tokens == 100


@patch("app.services.ai.openai_service.client")
def test_classify_document_unknown_falls_back_to_other(mock_client):
    mock_client.chat.completions.create.return_value = make_mock_response("spreadsheet")
    from app.services.ai.openai_service import classify_document
    doc_type, _ = classify_document("Random content")
    assert doc_type == "other"


@patch("app.services.ai.openai_service.client")
def test_summarize_document(mock_client):
    mock_client.chat.completions.create.return_value = make_mock_response(
        "This document describes a software architecture proposal.", 80
    )
    from app.services.ai.openai_service import summarize_document
    summary, tokens = summarize_document("Long document text here...")
    assert "software architecture" in summary
    assert tokens == 80


@patch("app.services.ai.openai_service.client")
def test_extract_key_points(mock_client):
    payload = json.dumps({"key_points": ["Point A", "Point B", "Point C"]})
    mock_client.chat.completions.create.return_value = make_mock_response(payload, 120)
    from app.services.ai.openai_service import extract_key_points
    points, tokens = extract_key_points("Document text...")
    assert len(points) == 3
    assert "Point A" in points


@patch("app.services.ai.openai_service.client")
def test_extract_key_points_bad_json_returns_empty(mock_client):
    mock_client.chat.completions.create.return_value = make_mock_response("not json at all")
    from app.services.ai.openai_service import extract_key_points
    points, _ = extract_key_points("text")
    assert points == []


@patch("app.services.ai.openai_service.client")
def test_analyze_sentiment_positive(mock_client):
    payload = json.dumps({"sentiment": "positive", "score": 0.85})
    mock_client.chat.completions.create.return_value = make_mock_response(payload, 60)
    from app.services.ai.openai_service import analyze_sentiment
    label, score, tokens = analyze_sentiment("Great results and amazing outcomes!")
    assert label == "positive"
    assert score == 0.85
    assert tokens == 60


@patch("app.services.ai.openai_service.client")
def test_analyze_sentiment_score_clamped(mock_client):
    payload = json.dumps({"sentiment": "positive", "score": 99.0})
    mock_client.chat.completions.create.return_value = make_mock_response(payload)
    from app.services.ai.openai_service import analyze_sentiment
    _, score, _ = analyze_sentiment("text")
    assert score == 1.0  # clamped to max


@patch("app.services.ai.openai_service.client")
def test_generate_qa_pairs(mock_client):
    payload = json.dumps({
        "qa_pairs": [
            {"question": "What is X?", "answer": "X is Y."},
            {"question": "Why does Z matter?", "answer": "Z matters because..."},
        ]
    })
    mock_client.chat.completions.create.return_value = make_mock_response(payload, 200)
    from app.services.ai.openai_service import generate_qa_pairs
    pairs, tokens = generate_qa_pairs("Document content...")
    assert len(pairs) == 2
    assert pairs[0]["question"] == "What is X?"


@patch("app.services.ai.openai_service.client")
def test_extract_entities(mock_client):
    payload = json.dumps({
        "people": ["John Doe"],
        "organizations": ["Acme Corp"],
        "dates": ["2025-01-01"],
        "locations": ["New York"],
    })
    mock_client.chat.completions.create.return_value = make_mock_response(payload, 150)
    from app.services.ai.openai_service import extract_entities
    entities, tokens = extract_entities("John Doe works at Acme Corp in New York.")
    assert "John Doe" in entities["people"]
    assert "Acme Corp" in entities["organizations"]


@patch("app.services.ai.openai_service.client")
def test_answer_question(mock_client):
    mock_client.chat.completions.create.return_value = make_mock_response(
        "The contract expires on December 31, 2025.", 90
    )
    from app.services.ai.openai_service import answer_question
    answer, tokens = answer_question("Contract document text...", "When does it expire?")
    assert "December 31" in answer
    assert tokens == 90
