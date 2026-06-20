import io
import pytest
from unittest.mock import patch, MagicMock

# ── Helpers ──────────────────────────────────────────────────────────────────

def make_pdf_bytes():
    """Minimal valid PDF content for upload testing."""
    return b"%PDF-1.4 test document content for AI processing"


def upload_doc(client, auth_headers, content=None, filename="test.pdf"):
    return client.post(
        "/api/v1/documents/upload",
        files={"file": (filename, content or make_pdf_bytes(), "application/pdf")},
        headers=auth_headers,
    )


# ── Upload tests ─────────────────────────────────────────────────────────────

@patch("app.api.v1.endpoints.documents.process_document_task")
@patch("app.api.v1.endpoints.documents.save_upload_file")
def test_upload_pdf(mock_save, mock_task, client, auth_headers):
    mock_save.return_value = None
    mock_task.delay.return_value = MagicMock(id="mock-task-id")

    res = upload_doc(client, auth_headers)
    assert res.status_code == 202
    data = res.json()
    assert data["file_type"] == "pdf"
    assert data["status"] == "pending"
    assert "celery_task_id" in data


@patch("app.api.v1.endpoints.documents.process_document_task")
@patch("app.api.v1.endpoints.documents.save_upload_file")
def test_upload_docx(mock_save, mock_task, client, auth_headers):
    mock_save.return_value = None
    mock_task.delay.return_value = MagicMock(id="mock-task-id-2")

    res = upload_doc(client, auth_headers, filename="test.docx")
    assert res.status_code == 202
    assert res.json()["file_type"] == "docx"


def test_upload_invalid_extension(client, auth_headers):
    res = client.post(
        "/api/v1/documents/upload",
        files={"file": ("test.exe", b"bad content", "application/octet-stream")},
        headers=auth_headers,
    )
    assert res.status_code == 400


def test_upload_unauthenticated(client):
    res = client.post(
        "/api/v1/documents/upload",
        files={"file": ("test.pdf", make_pdf_bytes(), "application/pdf")},
    )
    assert res.status_code == 401


def test_upload_too_large(client, auth_headers):
    big_content = b"x" * (11 * 1024 * 1024)  # 11MB > 10MB limit
    res = upload_doc(client, auth_headers, content=big_content)
    assert res.status_code == 400


# ── List / Status tests ───────────────────────────────────────────────────────

@patch("app.api.v1.endpoints.documents.process_document_task")
@patch("app.api.v1.endpoints.documents.save_upload_file")
def test_list_documents(mock_save, mock_task, client, auth_headers):
    mock_save.return_value = None
    mock_task.delay.return_value = MagicMock(id="task-1")

    upload_doc(client, auth_headers)
    upload_doc(client, auth_headers)

    res = client.get("/api/v1/documents/", headers=auth_headers)
    assert res.status_code == 200
    assert len(res.json()) == 2


@patch("app.api.v1.endpoints.documents.process_document_task")
@patch("app.api.v1.endpoints.documents.save_upload_file")
def test_get_document_status(mock_save, mock_task, client, auth_headers):
    mock_save.return_value = None
    mock_task.delay.return_value = MagicMock(id="task-99")

    upload_res = upload_doc(client, auth_headers)
    doc_id = upload_res.json()["id"]

    res = client.get(f"/api/v1/documents/{doc_id}/status", headers=auth_headers)
    assert res.status_code == 200
    assert res.json()["id"] == doc_id


@patch("app.api.v1.endpoints.documents.process_document_task")
@patch("app.api.v1.endpoints.documents.save_upload_file")
def test_results_not_ready(mock_save, mock_task, client, auth_headers):
    mock_save.return_value = None
    mock_task.delay.return_value = MagicMock(id="task-x")

    upload_res = upload_doc(client, auth_headers)
    doc_id = upload_res.json()["id"]

    # Still pending — results endpoint should return 400
    res = client.get(f"/api/v1/documents/{doc_id}/results", headers=auth_headers)
    assert res.status_code == 400


def test_document_not_found(client, auth_headers):
    res = client.get("/api/v1/documents/99999/status", headers=auth_headers)
    assert res.status_code == 404


# ── Ask question test ─────────────────────────────────────────────────────────

@patch("app.api.v1.endpoints.documents.openai_service.answer_question")
@patch("app.api.v1.endpoints.documents.extract_text")
@patch("app.api.v1.endpoints.documents.process_document_task")
@patch("app.api.v1.endpoints.documents.save_upload_file")
def test_ask_question_on_completed_doc(
    mock_save, mock_task, mock_extract, mock_answer,
    client, auth_headers, db
):
    from app.models.document import Document, DocumentStatus

    mock_save.return_value = None
    mock_task.delay.return_value = MagicMock(id="task-ask")
    mock_extract.return_value = ("Full document text content here.", 2)
    mock_answer.return_value = ("The answer is 42.", 50)

    upload_res = upload_doc(client, auth_headers)
    doc_id = upload_res.json()["id"]

    # Manually mark as completed
    doc = db.query(Document).filter(Document.id == doc_id).first()
    doc.status = DocumentStatus.COMPLETED
    doc.file_path = "fake/path.pdf"
    db.commit()

    res = client.post(
        f"/api/v1/documents/{doc_id}/ask",
        json={"question": "What is the main topic?"},
        headers=auth_headers,
    )
    assert res.status_code == 200
    data = res.json()
    assert data["answer"] == "The answer is 42."
    assert data["tokens_used"] == 50


# ── Delete test ───────────────────────────────────────────────────────────────

@patch("app.api.v1.endpoints.documents.process_document_task")
@patch("app.api.v1.endpoints.documents.save_upload_file")
@patch("os.path.exists", return_value=False)
def test_delete_document(mock_exists, mock_save, mock_task, client, auth_headers):
    mock_save.return_value = None
    mock_task.delay.return_value = MagicMock(id="task-del")

    upload_res = upload_doc(client, auth_headers)
    doc_id = upload_res.json()["id"]

    res = client.delete(f"/api/v1/documents/{doc_id}", headers=auth_headers)
    assert res.status_code == 204

    # Verify gone
    res = client.get(f"/api/v1/documents/{doc_id}/status", headers=auth_headers)
    assert res.status_code == 404
