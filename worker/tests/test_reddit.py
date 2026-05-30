import json
from unittest.mock import patch, MagicMock
from worker.ingest.reddit import fetch_signals
from worker.models import Signal

def test_fetch_signals_returns_signals():
    with patch("worker.ingest.reddit.praw.Reddit") as mock_reddit_cls:
        mock_reddit = MagicMock()
        mock_reddit_cls.return_value = mock_reddit
        mock_post = MagicMock()
        mock_post.title = "LLM agents are replacing junior devs"
        mock_post.score = 450
        mock_post.created_utc = 1748000000
        mock_reddit.subreddit.return_value.hot.return_value = [mock_post]
        signals = fetch_signals(subreddits=["MachineLearning"])
    assert len(signals) > 0
    assert all(isinstance(s, Signal) for s in signals)
    assert all(s.source == "reddit" for s in signals)
    assert any("llm agents" in s.term for s in signals)
    assert any(s.raw_count == 450 for s in signals)
    assert all(s.timestamp.tzinfo is not None for s in signals)

def test_fetch_signals_handles_empty():
    with patch("worker.ingest.reddit.praw.Reddit") as mock_reddit_cls:
        mock_reddit = MagicMock()
        mock_reddit_cls.return_value = mock_reddit
        mock_reddit.subreddit.return_value.hot.return_value = []
        signals = fetch_signals(subreddits=["empty_sub"])
    assert signals == []

def test_fetch_signals_continues_on_subreddit_error():
    with patch("worker.ingest.reddit.praw.Reddit") as mock_reddit_cls:
        mock_reddit = MagicMock()
        mock_reddit_cls.return_value = mock_reddit
        mock_reddit.subreddit.return_value.hot.side_effect = Exception("403 Forbidden")
        signals = fetch_signals(subreddits=["banned_sub"])
    assert signals == []
