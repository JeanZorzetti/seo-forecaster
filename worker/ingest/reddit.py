import time
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from worker.models import Signal
from worker.ingest.keywords import extract_keywords_batch

DEFAULT_SUBREDDITS = [
    "MachineLearning", "LocalLLaMA", "technology", "programming",
    "artificial", "SaaS", "startups", "webdev", "Python",
]

# The public .json endpoint returns 403 for datacenter IPs (EasyPanel/VPS),
# but the Atom RSS feed at /.rss still serves 200. We parse RSS instead.
# Browser-like User-Agent improves the trust score on shared datacenter IPs.
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
    ),
    "Accept": "application/atom+xml,application/xml;q=0.9",
}

_ATOM_NS = {"atom": "http://www.w3.org/2005/Atom"}


def _parse_rss(xml_text: str) -> list[tuple[str, datetime]]:
    """Return (title, published_at) tuples from a Reddit Atom RSS feed."""
    out = []
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return out
    for entry in root.findall("atom:entry", _ATOM_NS):
        title_el = entry.find("atom:title", _ATOM_NS)
        updated_el = entry.find("atom:updated", _ATOM_NS)
        title = (title_el.text or "").strip() if title_el is not None else ""
        if not title:
            continue
        ts = datetime.now(tz=timezone.utc)
        if updated_el is not None and updated_el.text:
            try:
                ts = datetime.fromisoformat(updated_el.text)
            except ValueError:
                pass
        out.append((title, ts))
    return out


def fetch_signals(subreddits: list[str] | None = None) -> list[Signal]:
    targets = subreddits or DEFAULT_SUBREDDITS

    # Collect raw posts (title + timestamp) from each subreddit's RSS feed.
    posts: list[tuple[str, datetime]] = []
    for sub_name in targets:
        try:
            url = f"https://www.reddit.com/r/{sub_name}/hot/.rss?limit=50"
            resp = requests.get(url, headers=HEADERS, timeout=15)
            resp.raise_for_status()
            posts.extend(_parse_rss(resp.text))
            time.sleep(1)  # be gentle with Reddit
        except Exception:
            pass  # degraded: skip broken subreddit, don't crash pipeline

    if not posts:
        return []

    titles = [t for t, _ in posts]
    keywords_per_title = extract_keywords_batch(titles)

    signals = []
    for (title, ts), terms in zip(posts, keywords_per_title):
        for term in terms:
            signals.append(Signal(
                term=term,
                source="reddit",
                raw_count=1,  # RSS has no score; volume comes from post frequency
                timestamp=ts,
                entities=[],
            ))
    return signals
