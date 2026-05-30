import time
import requests
from datetime import datetime, timezone
from worker.models import Signal
from worker.ingest.utils import extract_terms

DEFAULT_SUBREDDITS = [
    "MachineLearning", "LocalLLaMA", "technology", "programming",
    "artificial", "SaaS", "startups", "webdev", "Python",
]

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; SEOForecaster/1.0)"}

def fetch_signals(subreddits: list[str] | None = None) -> list[Signal]:
    targets = subreddits or DEFAULT_SUBREDDITS
    signals = []
    for sub_name in targets:
        try:
            url = f"https://www.reddit.com/r/{sub_name}/hot.json?limit=50"
            resp = requests.get(url, headers=HEADERS, timeout=15)
            resp.raise_for_status()
            posts = resp.json().get("data", {}).get("children", [])
            for child in posts:
                post = child.get("data", {})
                title = (post.get("title") or "").strip()
                if not title:
                    continue
                score = post.get("score") or 1
                created = post.get("created_utc") or time.time()
                for term in extract_terms(title):
                    signals.append(Signal(
                        term=term,
                        source="reddit",
                        raw_count=max(score, 1),
                        timestamp=datetime.fromtimestamp(created, tz=timezone.utc),
                        entities=[],
                    ))
            time.sleep(1)  # respeita rate limit do JSON público (~10 req/min)
        except Exception:
            pass  # degraded: skip broken subreddit, don't crash pipeline
    return signals
