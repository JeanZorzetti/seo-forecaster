from datetime import date, timedelta
from worker.detect.breakout import compute_breakout_score, BreakoutResult

def make_series(values: list[int]) -> list[tuple[date, int]]:
    base = date(2026, 1, 1)
    return [(base + timedelta(days=i), v) for i, v in enumerate(values)]

def test_flat_series_no_breakout():
    series = make_series([10, 10, 10, 10, 10, 10, 10])
    result = compute_breakout_score(series)
    assert result.second_derivative < 0.1
    assert result.breakout_score < 0.3

def test_linear_growth_moderate_score():
    series = make_series([5, 10, 15, 20, 25, 30, 35])
    result = compute_breakout_score(series)
    assert result.first_derivative > 0
    assert result.second_derivative >= 0  # linear: 2nd deriv ≈ 0
    assert 0.1 < result.breakout_score < 0.5  # above noise floor, below breakout threshold

def test_accelerating_series_high_score():
    # exponential: 2nd derivative clearly > 0
    series = make_series([1, 2, 4, 8, 16, 32, 64])
    result = compute_breakout_score(series)
    assert result.second_derivative > 1.0
    assert result.breakout_score > 0.7

def test_noise_series_low_score():
    series = make_series([5, 8, 3, 9, 4, 7, 6])
    result = compute_breakout_score(series)
    assert result.breakout_score < 0.35  # noise: EWMA suppresses, scores near flat-series range

def test_too_short_series_returns_zero():
    series = make_series([10, 20])
    result = compute_breakout_score(series)
    assert result.breakout_score == 0.0

def test_declining_series_penalized():
    series = make_series([64, 32, 16, 8, 4, 2, 1])
    result = compute_breakout_score(series)
    assert result.first_derivative < 0
    # penalty (×0.3) must suppress score even if 2nd deriv is positive
    assert result.breakout_score < 0.3
