import json
from pathlib import Path
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock
from worker.ingest.hackernews import fetch_signals
from worker.models import Signal

FIXTURES = Path(__file__).parent / "fixtures"

def load_fixture(name):
    return json.loads((FIXTURES / name).read_text())

# Deterministic keyword extraction so tests don't hit Groq. Returns the full
# lowercased title as a single keyword so content assertions remain meaningful.
def _fake_extract(titles, batch_size=30):
    return [[t.lower()] if t.strip() else [] for t in titles]

def test_fetch_signals_returns_signals():
    fixture = load_fixture("hn_response.json")
    with patch("worker.ingest.hackernews.requests.get") as mock_get, \
         patch("worker.ingest.hackernews.extract_keywords_batch", side_effect=_fake_extract):
        mock_resp = MagicMock()
        mock_resp.json.return_value = fixture
        mock_resp.raise_for_status.return_value = None
        mock_get.return_value = mock_resp
        signals = fetch_signals()
    assert len(signals) > 0
    for s in signals:
        assert isinstance(s, Signal)
        assert s.source == "hn"
        assert s.term != ""
    # verify content derived from fixture
    assert any("seo forecaster" in s.term for s in signals)
    assert any(s.raw_count == 342 for s in signals)
    assert all(s.timestamp.tzinfo is not None for s in signals)

def test_fetch_signals_handles_empty_hits():
    with patch("worker.ingest.hackernews.requests.get") as mock_get, \
         patch("worker.ingest.hackernews.extract_keywords_batch", side_effect=_fake_extract):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"hits": []}
        mock_resp.raise_for_status.return_value = None
        mock_get.return_value = mock_resp
        signals = fetch_signals()
    assert signals == []

def test_fetch_signals_skips_empty_titles():
    fixture = {"hits": [{"title": "", "points": 10, "created_at_i": 1748000000}]}
    with patch("worker.ingest.hackernews.requests.get") as mock_get, \
         patch("worker.ingest.hackernews.extract_keywords_batch", side_effect=_fake_extract):
        mock_resp = MagicMock()
        mock_resp.json.return_value = fixture
        mock_resp.raise_for_status.return_value = None
        mock_get.return_value = mock_resp
        signals = fetch_signals()
    assert signals == []
