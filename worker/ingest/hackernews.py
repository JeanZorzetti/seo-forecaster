import time
import requests
from datetime import datetime, timezone
from worker.models import Signal
from worker.ingest.keywords import extract_keywords_batch

HN_API = "https://hn.algolia.com/api/v1/search_by_date"

def fetch_signals(lookback_hours: int = 24) -> list[Signal]:
    since = int(time.time()) - lookback_hours * 3600
    params = {
        "tags": "story",
        "hitsPerPage": 100,
        "numericFilters": f"created_at_i>{since}",
    }
    try:
        resp = requests.get(HN_API, params=params, timeout=15)
        resp.raise_for_status()
        hits = resp.json().get("hits", [])
    except Exception:
        return []

    # Collect raw hits first, then extract keywords for all titles in one batch.
    valid = [h for h in hits if (h.get("title") or "").strip()]
    titles = [h["title"].strip() for h in valid]
    keywords_per_title = extract_keywords_batch(titles)

    signals = []
    for hit, terms in zip(valid, keywords_per_title):
        for term in terms:
            signals.append(Signal(
                term=term,
                source="hn",
                raw_count=hit.get("points", 1) or 1,
                timestamp=datetime.fromtimestamp(hit.get("created_at_i", 0), tz=timezone.utc),
                entities=[],
            ))
    return signals
