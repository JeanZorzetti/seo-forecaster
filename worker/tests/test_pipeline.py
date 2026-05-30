from datetime import date
from unittest.mock import patch, MagicMock
from worker.pipeline import run_pipeline
from worker.models import Signal, BreakoutCandidate, Finalist, Prediction
from worker.detect.breakout import BreakoutResult

def make_signal(term="llm agents", source="hn"):
    from datetime import datetime, timezone
    return Signal(
        term=term,
        source=source,
        raw_count=100,
        timestamp=datetime.now(tz=timezone.utc),
        entities=[],
    )

def test_run_pipeline_populates_predictions():
    history = [(date(2026, 1, i), i * 10) for i in range(1, 8)]
    forecast_data = {"curve": [10.0] * 90, "peak_day": 30, "confidence": 0.6}
    prediction_obj = Prediction(
        term="llm agents",
        breakout_score=0.9,
        relevance_score=0.8,
        matched_niche_id=1,
        intents=["how to use llm agents"],
        content_gaps=["no guide in PT-BR"],
        status="emerging",
    )

    with patch("worker.pipeline.fetch_hn_signals", return_value=[make_signal()]), \
         patch("worker.pipeline.fetch_reddit_signals", return_value=[]), \
         patch("worker.pipeline.fetch_gdelt_signals", return_value=[]), \
         patch("worker.pipeline.upsert_term_history"), \
         patch("worker.pipeline.get_term_history", return_value=history), \
         patch("worker.pipeline.compute_breakout_score", return_value=BreakoutResult(5.0, 2.0, 0.9)), \
         patch("worker.pipeline.get_all_niches", return_value=[{"id": 1, "name": "AI", "description": "ai", "embedding": [1.0, 0.0]}]), \
         patch("worker.pipeline.filter_by_relevance", return_value=[Finalist("llm agents", 0.9, 0.8, 1)]), \
         patch("worker.pipeline.get_forecast", return_value=forecast_data), \
         patch("worker.pipeline.expand_intent", return_value=prediction_obj), \
         patch("worker.pipeline.upsert_prediction") as mock_upsert, \
         patch("worker.pipeline.start_run", return_value=1), \
         patch("worker.pipeline.finish_run") as mock_finish:
        run_pipeline()

    mock_upsert.assert_called_once()
    prediction = mock_upsert.call_args[0][0]
    assert prediction.term == "llm agents"
    assert prediction.intents == ["how to use llm agents"]
    assert prediction.forecast == forecast_data

    mock_finish.assert_called_once()
    finish_args = mock_finish.call_args[0]
    assert finish_args[3] == "done"  # status
    assert finish_args[4] == []      # no errors

def test_run_pipeline_handles_all_sources_failing():
    with patch("worker.pipeline.fetch_hn_signals", side_effect=Exception("HN down")), \
         patch("worker.pipeline.fetch_reddit_signals", side_effect=Exception("Reddit down")), \
         patch("worker.pipeline.fetch_gdelt_signals", side_effect=Exception("GDELT down")), \
         patch("worker.pipeline.start_run", return_value=1), \
         patch("worker.pipeline.finish_run") as mock_finish:
        run_pipeline()

    finish_args = mock_finish.call_args[0]
    assert finish_args[3] == "failed"
    assert len(finish_args[4]) == 3  # 3 errors logged

def test_run_pipeline_partial_on_source_failure():
    history = [(date(2026, 1, i), i * 10) for i in range(1, 8)]
    prediction_obj = Prediction("llm agents", 0.9, 0.8, 1, intents=[], content_gaps=[], status="emerging")

    with patch("worker.pipeline.fetch_hn_signals", return_value=[make_signal()]), \
         patch("worker.pipeline.fetch_reddit_signals", side_effect=Exception("Reddit down")), \
         patch("worker.pipeline.fetch_gdelt_signals", return_value=[]), \
         patch("worker.pipeline.upsert_term_history"), \
         patch("worker.pipeline.get_term_history", return_value=history), \
         patch("worker.pipeline.compute_breakout_score", return_value=BreakoutResult(5.0, 2.0, 0.9)), \
         patch("worker.pipeline.get_all_niches", return_value=[{"id": 1, "name": "AI", "description": "ai", "embedding": [1.0]}]), \
         patch("worker.pipeline.filter_by_relevance", return_value=[Finalist("llm agents", 0.9, 0.8, 1)]), \
         patch("worker.pipeline.get_forecast", return_value=None), \
         patch("worker.pipeline.expand_intent", return_value=prediction_obj), \
         patch("worker.pipeline.upsert_prediction"), \
         patch("worker.pipeline.start_run", return_value=1), \
         patch("worker.pipeline.finish_run") as mock_finish:
        run_pipeline()

    finish_args = mock_finish.call_args[0]
    assert finish_args[3] == "partial"
    assert any("Reddit" in e for e in finish_args[4])
