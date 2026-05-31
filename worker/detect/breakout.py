import numpy as np
from dataclasses import dataclass
from datetime import date

EWMA_ALPHA = 0.3      # Higher values react faster to recent data; lower values smooth more
SIGMOID_SHIFT = 1.0   # Score exceeds 0.5 only when second_deriv > 1.0 — avoids false positives on mild acceleration

# Bootstrap (cold-start): until we have enough history to measure acceleration,
# rank terms by raw volume so the dashboard is never empty on day 1.
# Calibrated for LLM-extracted keywords, whose per-day volume is low (median ~2,
# max ~8) because keywords are diverse and don't accumulate like raw bigrams did.
# midpoint=3 → a term seen ~3+ times in a day scores >= 0.5 (top ~20% surface).
BOOTSTRAP_VOLUME_MIDPOINT = 3.0  # raw count that maps to a 0.5 bootstrap score


@dataclass
class BreakoutResult:
    first_derivative: float
    second_derivative: float
    breakout_score: float  # 0.0–1.0
    bootstrap: bool = False  # True when score came from volume fallback, not acceleration


def _bootstrap_score(series: list[tuple[date, int]]) -> BreakoutResult:
    """Cold-start: no acceleration measurable yet — rank by latest raw volume."""
    latest_count = float(series[-1][1]) if series else 0.0
    # Log-scaled sigmoid: high-volume terms score high, low-volume terms score low.
    score = float(1 / (1 + np.exp(-(np.log1p(latest_count) - np.log1p(BOOTSTRAP_VOLUME_MIDPOINT)))))
    return BreakoutResult(
        first_derivative=0.0,
        second_derivative=0.0,
        breakout_score=round(score, 4),
        bootstrap=True,
    )


def compute_breakout_score(series: list[tuple[date, int]]) -> BreakoutResult:
    # Cold-start: fewer than 3 history points means acceleration can't be measured.
    # Fall back to raw-volume ranking so emerging terms still surface on day 1.
    if len(series) < 3:
        return _bootstrap_score(series)

    counts = np.array([v for _, v in series], dtype=float)

    # EWMA to smooth noise (recent values weighted more heavily)
    smoothed = np.zeros_like(counts)
    smoothed[0] = counts[0]
    for i in range(1, len(counts)):
        smoothed[i] = EWMA_ALPHA * counts[i] + (1 - EWMA_ALPHA) * smoothed[i - 1]

    diffs1 = np.diff(smoothed)
    first_deriv = float(np.mean(diffs1[-3:]))

    diffs2 = np.diff(diffs1)
    second_deriv = float(np.mean(diffs2[-2:])) if len(diffs2) >= 2 else 0.0

    score = float(1 / (1 + np.exp(-(second_deriv - SIGMOID_SHIFT))))

    if first_deriv < 0:
        score *= 0.3

    return BreakoutResult(
        first_derivative=first_deriv,
        second_derivative=second_deriv,
        breakout_score=round(score, 4),
        bootstrap=False,
    )
