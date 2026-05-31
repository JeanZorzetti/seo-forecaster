from unittest.mock import patch, MagicMock
from worker.ingest.reddit import fetch_signals, _parse_rss
from worker.models import Signal

# Minimal Reddit Atom RSS sample (two entries).
RSS_SAMPLE = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <entry>
    <title>LLM agents are replacing junior devs</title>
    <updated>2026-05-31T12:14:13+00:00</updated>
  </entry>
  <entry>
    <title>Groq just added 10x rate limits on free tier</title>
    <updated>2026-05-31T10:00:00+00:00</updated>
  </entry>
</feed>"""

# Deterministic keyword extraction so tests don't hit Groq.
def _fake_extract(titles, batch_size=30):
    return [[t.lower()] if t.strip() else [] for t in titles]


def test_parse_rss_extracts_entries():
    entries = _parse_rss(RSS_SAMPLE)
    assert len(entries) == 2
    title, ts = entries[0]
    assert title == "LLM agents are replacing junior devs"
    assert ts.tzinfo is not None
    assert ts.year == 2026


def test_parse_rss_handles_malformed():
    assert _parse_rss("not xml at all <broken>") == []


def test_fetch_signals_returns_signals():
    with patch("worker.ingest.reddit.requests.get") as mock_get, \
         patch("worker.ingest.reddit.time.sleep"), \
         patch("worker.ingest.reddit.extract_keywords_batch", side_effect=_fake_extract):
        mock_resp = MagicMock()
        mock_resp.text = RSS_SAMPLE
        mock_resp.raise_for_status.return_value = None
        mock_get.return_value = mock_resp
        signals = fetch_signals(subreddits=["MachineLearning"])
    assert len(signals) > 0
    assert all(isinstance(s, Signal) for s in signals)
    assert all(s.source == "reddit" for s in signals)
    assert any("llm agents" in s.term for s in signals)
    assert all(s.raw_count == 1 for s in signals)
    assert all(s.timestamp.tzinfo is not None for s in signals)


def test_fetch_signals_handles_empty():
    with patch("worker.ingest.reddit.requests.get") as mock_get, \
         patch("worker.ingest.reddit.time.sleep"), \
         patch("worker.ingest.reddit.extract_keywords_batch", side_effect=_fake_extract):
        mock_resp = MagicMock()
        mock_resp.text = '<feed xmlns="http://www.w3.org/2005/Atom"></feed>'
        mock_resp.raise_for_status.return_value = None
        mock_get.return_value = mock_resp
        signals = fetch_signals(subreddits=["empty_sub"])
    assert signals == []


def test_fetch_signals_continues_on_error():
    with patch("worker.ingest.reddit.requests.get") as mock_get, \
         patch("worker.ingest.reddit.time.sleep"), \
         patch("worker.ingest.reddit.extract_keywords_batch", side_effect=_fake_extract):
        mock_get.side_effect = Exception("403 Forbidden")
        signals = fetch_signals(subreddits=["banned_sub"])
    assert signals == []
