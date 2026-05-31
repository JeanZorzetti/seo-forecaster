from unittest.mock import patch, MagicMock
from worker.ingest.reddit import fetch_signals
from worker.models import Signal

FIXTURE_RESPONSE = {
    "data": {
        "children": [
            {"data": {"title": "LLM agents are replacing junior devs", "score": 450, "created_utc": 1748000000}},
            {"data": {"title": "Groq just added 10x rate limits on free tier", "score": 210, "created_utc": 1748000100}},
        ]
    }
}

# Deterministic keyword extraction so tests don't hit Groq.
def _fake_extract(titles, batch_size=30):
    return [[t.lower()] if t.strip() else [] for t in titles]

def test_fetch_signals_returns_signals():
    with patch("worker.ingest.reddit.requests.get") as mock_get, \
         patch("worker.ingest.reddit.time.sleep"), \
         patch("worker.ingest.reddit.extract_keywords_batch", side_effect=_fake_extract):
        mock_resp = MagicMock()
        mock_resp.json.return_value = FIXTURE_RESPONSE
        mock_resp.raise_for_status.return_value = None
        mock_get.return_value = mock_resp
        signals = fetch_signals(subreddits=["MachineLearning"])
    assert len(signals) > 0
    assert all(isinstance(s, Signal) for s in signals)
    assert all(s.source == "reddit" for s in signals)
    assert any("llm agents" in s.term for s in signals)
    assert any(s.raw_count == 450 for s in signals)
    assert all(s.timestamp.tzinfo is not None for s in signals)

def test_fetch_signals_handles_empty():
    with patch("worker.ingest.reddit.requests.get") as mock_get, \
         patch("worker.ingest.reddit.time.sleep"), \
         patch("worker.ingest.reddit.extract_keywords_batch", side_effect=_fake_extract):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"data": {"children": []}}
        mock_resp.raise_for_status.return_value = None
        mock_get.return_value = mock_resp
        signals = fetch_signals(subreddits=["empty_sub"])
    assert signals == []

def test_fetch_signals_continues_on_error():
    with patch("worker.ingest.reddit.requests.get") as mock_get, \
         patch("worker.ingest.reddit.time.sleep"), \
         patch("worker.ingest.reddit.extract_keywords_batch", side_effect=_fake_extract):
        mock_get.side_effect = Exception("connection refused")
        signals = fetch_signals(subreddits=["banned_sub"])
    assert signals == []
