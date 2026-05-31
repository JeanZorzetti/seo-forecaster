import json
from unittest.mock import patch, MagicMock
from worker.ingest.keywords import extract_keywords_batch, _parse_batch


def _mock_groq_response(payload: dict):
    resp = MagicMock()
    resp.choices[0].message.content = json.dumps(payload)
    return resp


def test_parse_batch_valid():
    content = '{"results": [["openrouter funding"], ["zig linker", "elf"]]}'
    result = _parse_batch(content, expected=2)
    assert result == [["openrouter funding"], ["zig linker", "elf"]]


def test_parse_batch_wrong_count_returns_none():
    content = '{"results": [["only one"]]}'
    assert _parse_batch(content, expected=3) is None


def test_parse_batch_extracts_json_from_prose():
    content = 'Aqui está: {"results": [["keyword"]]} pronto.'
    assert _parse_batch(content, expected=1) == [["keyword"]]


def test_parse_batch_invalid_json_returns_none():
    assert _parse_batch("not json at all", expected=1) is None


def test_extract_keywords_batch_uses_groq():
    titles = ["OpenRouter raises $113M Series B", "Zig ELF linker improvements"]
    payload = {"results": [["openrouter funding"], ["zig linker"]]}
    with patch("worker.ingest.keywords._get_groq_client") as mock_factory:
        mock_client = MagicMock()
        mock_factory.return_value = mock_client
        mock_client.chat.completions.create.return_value = _mock_groq_response(payload)
        result = extract_keywords_batch(titles)
    assert result == [["openrouter funding"], ["zig linker"]]


def test_extract_keywords_batch_falls_back_on_groq_error():
    titles = ["EY Canada published a cybersecurity report"]
    with patch("worker.ingest.keywords._get_groq_client") as mock_factory:
        mock_factory.side_effect = Exception("rate limit")
        result = extract_keywords_batch(titles)
    # Fallback must produce non-empty n-gram terms (not crash, not empty)
    assert len(result) == 1
    assert len(result[0]) > 0
    # n-gram fallback yields clean terms (no stopwords)
    flat = " ".join(result[0])
    assert "cybersecurity" in flat


def test_extract_keywords_batch_empty_input():
    assert extract_keywords_batch([]) == []


def test_extract_keywords_batch_per_title_fallback_on_empty_result():
    # Groq returns valid JSON but an empty list for a title → fall back for that one
    titles = ["Some interesting cybersecurity article here"]
    payload = {"results": [[]]}
    with patch("worker.ingest.keywords._get_groq_client") as mock_factory:
        mock_client = MagicMock()
        mock_factory.return_value = mock_client
        mock_client.chat.completions.create.return_value = _mock_groq_response(payload)
        result = extract_keywords_batch(titles)
    assert len(result[0]) > 0  # fell back to n-grams
