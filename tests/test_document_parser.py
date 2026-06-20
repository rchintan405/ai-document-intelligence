from app.services.document_parser import truncate_text_for_ai


def test_truncate_short_text_unchanged():
    text = "Short text"
    result = truncate_text_for_ai(text, max_tokens=100)
    assert result == text


def test_truncate_long_text():
    # 100 tokens * 4 chars = 400 chars max
    text = "a" * 500
    result = truncate_text_for_ai(text, max_tokens=100)
    assert len(result) < 500
    assert "[... document truncated" in result


def test_truncate_exact_boundary():
    text = "b" * 400  # exactly 100 tokens worth
    result = truncate_text_for_ai(text, max_tokens=100)
    assert result == text  # not truncated
