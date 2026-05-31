import json
from pathlib import Path
from unittest.mock import patch, MagicMock
from worker.ingest.hackernews import fetch_signals
from worker.models import Signal

FIXTURES = Path(__file__).parent / "fixtures"

def load_fixture(name):
    return json.loads((FIXTURES / name).read_text())

def test_fetch_signals_returns_signals():
    fixture = load_fixture("hn_response.json")
    with patch("worker.ingest.hackernews.requests.get") as mock_get:
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
    # content derived from fixture via local n-gram extraction
    assert any("seo forecaster" in s.term for s in signals)
    assert any(s.raw_count == 342 for s in signals)
    assert all(s.timestamp.tzinfo is not None for s in signals)

def test_fetch_signals_handles_empty_hits():
    with patch("worker.ingest.hackernews.requests.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"hits": []}
        mock_resp.raise_for_status.return_value = None
        mock_get.return_value = mock_resp
        signals = fetch_signals()
    assert signals == []

def test_fetch_signals_skips_empty_titles():
    fixture = {"hits": [{"title": "", "points": 10, "created_at_i": 1748000000}]}
    with patch("worker.ingest.hackernews.requests.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.json.return_value = fixture
        mock_resp.raise_for_status.return_value = None
        mock_get.return_value = mock_resp
        signals = fetch_signals()
    assert signals == []
