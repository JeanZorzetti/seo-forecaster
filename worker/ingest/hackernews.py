import time
import requests
from datetime import datetime, timezone
from worker.models import Signal
from worker.ingest.utils import extract_terms

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

    signals = []
    for hit in hits:
        title = (hit.get("title") or "").strip()
        if not title:
            continue
        for term in extract_terms(title):
            signals.append(Signal(
                term=term,
                source="hn",
                raw_count=hit.get("points", 1) or 1,
                timestamp=datetime.fromtimestamp(hit.get("created_at_i", 0), tz=timezone.utc),
                entities=[],
            ))
    return signals
