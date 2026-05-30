import json
import os
import tempfile
from datetime import datetime, timezone
from google.cloud import bigquery
from google.oauth2 import service_account
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

def _make_client():
    # Opção 1: JSON inline via env var GCP_SERVICE_ACCOUNT_JSON (preferido no EasyPanel)
    sa_json = os.environ.get("GCP_SERVICE_ACCOUNT_JSON")
    if sa_json:
        info = json.loads(sa_json)
        creds = service_account.Credentials.from_service_account_info(
            info, scopes=["https://www.googleapis.com/auth/bigquery"]
        )
        return bigquery.Client(credentials=creds, project=info["project_id"])

    # Opção 2: caminho para arquivo JSON (GOOGLE_APPLICATION_CREDENTIALS)
    return bigquery.Client()

def fetch_signals() -> list[Signal]:
    try:
        client = _make_client()
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
