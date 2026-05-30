import json
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock
from worker.ingest.hackernews import fetch_signals
from worker.models import Signal

def load_fixture(name):
    with open(f"worker/tests/fixtures/{name}") as f:
        return json.load(f)

def test_fetch_signals_returns_signals():
    fixture = load_fixture("hn_response.json")
    with patch("worker.ingest.hackernews.requests.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.json.return_value = fixture
        mock_resp.raise_for_status.return_value = None
        mock_get.return_value = mock_resp
        signals = fetch_signals()
    assert isinstance(signals, list)
    assert len(signals) > 0
    for s in signals:
        assert isinstance(s, Signal)
        assert s.source == "hn"
        assert s.term != ""

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
