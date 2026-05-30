import json
from unittest.mock import patch, MagicMock
from worker.ingest.gdelt import fetch_signals
from worker.models import Signal

def load_fixture(name):
    with open(f"worker/tests/fixtures/{name}") as f:
        return json.load(f)

def test_fetch_signals_returns_signals():
    fixture = load_fixture("gdelt_response.json")
    with patch("worker.ingest.gdelt.bigquery.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_row = MagicMock()
        mock_row.theme = fixture[0]["theme"]
        mock_row.mention_count = fixture[0]["mention_count"]
        mock_row.avg_tone = fixture[0]["avg_tone"]
        mock_row.entities = json.dumps(fixture[0]["entities"])
        mock_client.query.return_value.__iter__ = MagicMock(return_value=iter([mock_row]))
        signals = fetch_signals()
    assert len(signals) > 0
    assert all(isinstance(s, Signal) for s in signals)
    assert all(s.source == "gdelt" for s in signals)

def test_fetch_signals_returns_empty_on_bq_error():
    with patch("worker.ingest.gdelt.bigquery.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.query.side_effect = Exception("BQ unavailable")
        signals = fetch_signals()
    assert signals == []

def test_fetch_signals_skips_empty_theme():
    with patch("worker.ingest.gdelt.bigquery.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_row = MagicMock()
        mock_row.theme = ""
        mock_row.mention_count = 50
        mock_row.avg_tone = 1.0
        mock_row.entities = "[]"
        mock_client.query.return_value.__iter__ = MagicMock(return_value=iter([mock_row]))
        signals = fetch_signals()
    assert signals == []
