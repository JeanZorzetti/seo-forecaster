import praw
from datetime import datetime, timezone
from worker.config import REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET, REDDIT_USER_AGENT
from worker.models import Signal

DEFAULT_SUBREDDITS = [
    "MachineLearning", "LocalLLaMA", "technology", "programming",
    "artificial", "SaaS", "startups", "webdev", "Python",
]

def _make_reddit():
    return praw.Reddit(
        client_id=REDDIT_CLIENT_ID,
        client_secret=REDDIT_CLIENT_SECRET,
        user_agent=REDDIT_USER_AGENT,
    )

def fetch_signals(subreddits: list[str] | None = None) -> list[Signal]:
    reddit = _make_reddit()
    targets = subreddits or DEFAULT_SUBREDDITS
    signals = []
    for sub_name in targets:
        try:
            sub = reddit.subreddit(sub_name)
            for post in sub.hot(limit=50):
                title = (post.title or "").strip()
                if not title:
                    continue
                for term in _extract_terms(title):
                    signals.append(Signal(
                        term=term,
                        source="reddit",
                        raw_count=max(post.score, 1),
                        timestamp=datetime.fromtimestamp(post.created_utc, tz=timezone.utc),
                        entities=[],
                    ))
        except Exception:
            pass  # degraded: skip broken subreddit, don't crash pipeline
    return signals

def _extract_terms(title: str) -> list[str]:
    terms = [title.lower()]
    words = [w for w in title.lower().split() if len(w) > 3]
    for i in range(len(words) - 1):
        terms.append(f"{words[i]} {words[i+1]}")
    return terms[:5]
