import json
from unittest.mock import patch, MagicMock
from worker.ingest.gdelt import fetch_signals, _clean_theme
from worker.models import Signal


def test_clean_theme_strips_offset_and_prefix():
    assert _clean_theme("TAX_FNCACT_DEMONSTRATORS,293") == "demonstrators"
    assert _clean_theme("NATURAL_DISASTER_POWERFUL_STORM,16") == "natural disaster powerful storm"
    assert _clean_theme("MEDIA_MSM,58") == "msm"
    assert _clean_theme("") == ""


def _make_row(theme, mention_count, avg_tone, entities):
    row = MagicMock()
    row.theme = theme
    row.mention_count = mention_count
    row.avg_tone = avg_tone
    row.entities = entities
    return row


def test_fetch_signals_returns_signals():
    # Raw GDELT-format row (theme with offset suffix, entities with offsets)
    row = _make_row(
        "NATURAL_DISASTER_POWERFUL_STORM,16",
        342,
        -4.0,
        json.dumps(["Luke Huntington,657", "Luke Huntington,1804", "Jane Doe,12"]),
    )
    with patch("worker.ingest.gdelt.bigquery.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.query.return_value = [row]
        signals = fetch_signals()
    assert len(signals) > 0
    assert all(isinstance(s, Signal) for s in signals)
    assert all(s.source == "gdelt" for s in signals)
    # theme cleaned
    assert any("natural disaster powerful storm" in s.term for s in signals)
    assert any(s.raw_count == 342 for s in signals)
    # entities cleaned (offset stripped) and deduped
    sig = signals[0]
    assert "Luke Huntington" in sig.entities
    assert "Luke Huntington,657" not in sig.entities  # offset stripped
    assert sig.entities.count("Luke Huntington") == 1  # deduped


def test_fetch_signals_returns_empty_on_bq_error():
    with patch("worker.ingest.gdelt.bigquery.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.query.side_effect = Exception("BQ unavailable")
        signals = fetch_signals()
    assert signals == []


def test_fetch_signals_skips_empty_theme():
    row = _make_row("", 50, 1.0, "[]")
    with patch("worker.ingest.gdelt.bigquery.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.query.return_value = [row]
        signals = fetch_signals()
    assert signals == []
