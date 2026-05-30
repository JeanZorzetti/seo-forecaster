import logging
from datetime import date
from worker.ingest.hackernews import fetch_signals as fetch_hn_signals
from worker.ingest.reddit import fetch_signals as fetch_reddit_signals
from worker.ingest.gdelt import fetch_signals as fetch_gdelt_signals
from worker.detect.breakout import compute_breakout_score
from worker.filter.relevance import filter_by_relevance
from worker.forecast.chronos import get_forecast
from worker.reason.expand import expand_intent
from worker.persist.db import (
    upsert_term_history, get_term_history, get_all_niches,
    upsert_prediction, start_run, finish_run,
)
from worker.models import BreakoutCandidate
from worker.config import BREAKOUT_THRESHOLD

logger = logging.getLogger(__name__)

def run_pipeline():
    run_id = start_run()
    today = date.today()
    errors = []

    # Stage 1: Ingest
    all_signals = []
    for fetch_fn, name in [
        (fetch_hn_signals, "hn"),
        (fetch_reddit_signals, "reddit"),
        (fetch_gdelt_signals, "gdelt"),
    ]:
        try:
            sigs = fetch_fn()
            all_signals.extend(sigs)
            logger.info(f"[{name}] {len(sigs)} signals")
        except Exception as e:
            errors.append(f"{name}: {str(e)}")
            logger.warning(f"[{name}] failed: {e}")

    if not all_signals:
        finish_run(run_id, 0, 0, "failed", errors)
        return

    # Stage 2: Detect — upsert term_history, compute breakout
    term_counts: dict[str, dict[str, int]] = {}
    for s in all_signals:
        term_counts.setdefault(s.term, {}).setdefault(s.source, 0)
        term_counts[s.term][s.source] += s.raw_count

    candidates = []
    for term, source_counts in term_counts.items():
        for source, count in source_counts.items():
            upsert_term_history(term, source, count, today)
            history = get_term_history(term, source, days=30)
            result = compute_breakout_score(history)
            if result.breakout_score >= BREAKOUT_THRESHOLD:
                entities = next(
                    (s.entities for s in all_signals if s.term == term),
                    []
                )
                candidates.append(BreakoutCandidate(
                    term=term,
                    source=source,
                    breakout_score=result.breakout_score,
                    first_derivative=result.first_derivative,
                    second_derivative=result.second_derivative,
                    entities=entities,
                ))

    # Stage 3: Filter relevance
    niches = get_all_niches()
    try:
        finalists = filter_by_relevance(candidates, niches)
    except RuntimeError as e:
        errors.append(str(e))
        finalists = []

    # Stages 4+5+6: Forecast → Reason → Persist
    for finalist in finalists:
        history = get_term_history(finalist.term, "hn", days=30)
        series = [c for _, c in history]
        forecast = get_forecast(series) if len(series) >= 3 else None

        prediction = expand_intent(finalist)
        prediction.forecast = forecast

        if forecast:
            peak_day = forecast.get("peak_day", 0)
            horizon = len(forecast.get("curve", [1]))
            if peak_day < horizon * 0.4:
                prediction.status = "maturing"
            elif peak_day > horizon * 0.7:
                prediction.status = "saturating"
            else:
                prediction.status = "emerging"

        upsert_prediction(prediction, today)

    finish_run(
        run_id,
        len(all_signals),
        len(finalists),
        "done" if not errors else "partial",
        errors,
    )

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_pipeline()
