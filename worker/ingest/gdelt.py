import json
import os
import re
from datetime import datetime, timezone
from google.cloud import bigquery
from google.oauth2 import service_account
from worker.models import Signal

# Uses the PARTITIONED gkg table so _PARTITIONTIME limits the scan to ~0.1 GB/day
# instead of a 400+ GB full-table scan that blows the BigQuery free tier.
GKG_QUERY = """
SELECT
  SPLIT(V2Themes, ';')[OFFSET(0)] AS theme,
  COUNT(*) AS mention_count,
  AVG(CAST(SPLIT(V2Tone, ',')[OFFSET(0)] AS FLOAT64)) AS avg_tone,
  ARRAY_AGG(DISTINCT SPLIT(V2Persons, ';')[OFFSET(0)] IGNORE NULLS LIMIT 5) AS entities
FROM `gdelt-bq.gdeltv2.gkg_partitioned`
WHERE _PARTITIONTIME >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 1 DAY)
  AND V2Themes IS NOT NULL AND V2Themes != ''
GROUP BY theme
HAVING mention_count > 20
ORDER BY mention_count DESC
LIMIT 200
"""


def _make_client():
    # Option 1: inline JSON via env var GCP_SERVICE_ACCOUNT_JSON (EasyPanel-friendly)
    sa_json = os.environ.get("GCP_SERVICE_ACCOUNT_JSON")
    if sa_json:
        info = json.loads(sa_json)
        creds = service_account.Credentials.from_service_account_info(
            info, scopes=["https://www.googleapis.com/auth/bigquery"]
        )
        return bigquery.Client(credentials=creds, project=info["project_id"])

    # Option 2: path to a JSON key file (GOOGLE_APPLICATION_CREDENTIALS)
    return bigquery.Client()


def _clean_theme(raw: str) -> str:
    """
    GDELT themes look like 'TAX_FNCACT_DEMONSTRATORS,293' or
    'NATURAL_DISASTER_POWERFUL_STORM,16'. Strip the trailing ',<offset>' and
    the GKG taxonomy prefixes, then turn it into a readable search phrase.
    """
    theme = raw.split(",")[0]  # drop ',293' char-offset suffix
    # Remove common GKG taxonomy prefixes that aren't search-meaningful
    theme = re.sub(r"^(TAX_FNCACT_|TAX_WORLDBIRDS_|TAX_|WB_\d+_|EPU_|CRISISLEX_|SOC_|ECON_|MEDIA_)", "", theme)
    return theme.lower().replace("_", " ").strip()


def fetch_signals() -> list[Signal]:
    try:
        client = _make_client()
        rows = list(client.query(GKG_QUERY))
    except Exception:
        return []  # degraded: GDELT failure doesn't break pipeline

    signals = []
    now = datetime.now(tz=timezone.utc)
    for row in rows:
        theme = _clean_theme(row.theme or "")
        if not theme or len(theme) < 3:
            continue
        entities = []
        try:
            raw_ents = json.loads(row.entities) if isinstance(row.entities, str) else list(row.entities or [])
            # Strip ',<offset>' suffixes and dedupe person names
            seen = set()
            for e in raw_ents:
                name = str(e).split(",")[0].strip()
                if name and name not in seen:
                    seen.add(name)
                    entities.append(name)
        except Exception:
            pass
        signals.append(Signal(
            term=theme,
            source="gdelt",
            raw_count=int(row.mention_count),
            timestamp=now,
            entities=entities,
        ))
    return signals
