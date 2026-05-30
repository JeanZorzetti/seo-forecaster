import json
from datetime import datetime, timezone
from google.cloud import bigquery
from worker.models import Signal

GKG_QUERY = """
SELECT
  SPLIT(V2Themes, ';')[OFFSET(0)] AS theme,
  COUNT(*) AS mention_count,
  AVG(V2Tone_1) AS avg_tone,
  ARRAY_AGG(DISTINCT SPLIT(V2Persons, ';')[OFFSET(0)] IGNORE NULLS LIMIT 5) AS entities
FROM `gdelt-bq.gdeltv2.gkg`
WHERE DATE(_PARTITIONTIME) = DATE_SUB(CURRENT_DATE(), INTERVAL 1 DAY)
  AND V2Themes IS NOT NULL
GROUP BY theme
HAVING mention_count > 20
ORDER BY mention_count DESC
LIMIT 200
"""

def fetch_signals() -> list[Signal]:
    try:
        client = bigquery.Client()
        rows = list(client.query(GKG_QUERY))
    except Exception:
        return []  # degraded: GDELT failure doesn't break pipeline

    signals = []
    now = datetime.now(tz=timezone.utc)
    for row in rows:
        theme = (row.theme or "").strip()
        if not theme:
            continue
        entities = []
        try:
            entities = json.loads(row.entities) if isinstance(row.entities, str) else list(row.entities or [])
        except Exception:
            pass
        signals.append(Signal(
            term=theme.lower().replace("_", " "),
            source="gdelt",
            raw_count=int(row.mention_count),
            timestamp=now,
            entities=[e for e in entities if e],
        ))
    return signals
