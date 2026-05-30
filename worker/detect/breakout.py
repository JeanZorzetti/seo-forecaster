import numpy as np
from dataclasses import dataclass
from datetime import date

@dataclass
class BreakoutResult:
    first_derivative: float
    second_derivative: float
    breakout_score: float  # 0.0–1.0

def compute_breakout_score(series: list[tuple[date, int]]) -> BreakoutResult:
    if len(series) < 3:
        return BreakoutResult(0.0, 0.0, 0.0)

    counts = np.array([v for _, v in series], dtype=float)

    # EWMA to smooth noise (alpha=0.3 weights recent more)
    alpha = 0.3
    smoothed = np.zeros_like(counts)
    smoothed[0] = counts[0]
    for i in range(1, len(counts)):
        smoothed[i] = alpha * counts[i] + (1 - alpha) * smoothed[i - 1]

    # 1st derivative: average daily change (last 3 points)
    diffs1 = np.diff(smoothed)
    first_deriv = float(np.mean(diffs1[-3:]))

    # 2nd derivative: rate of change of the rate of change
    diffs2 = np.diff(diffs1)
    second_deriv = float(np.mean(diffs2[-2:])) if len(diffs2) >= 2 else 0.0

    # Normalize to [0,1] — shifted sigmoid so zero acceleration scores ~0.27
    # shift by -1 so flat series (2nd_deriv=0) → sigmoid(-1) ≈ 0.27, below 0.3 threshold
    score = float(1 / (1 + np.exp(-(second_deriv - 1.0))))

    # Penalize if first derivative is negative (declining)
    if first_deriv < 0:
        score *= 0.3

    return BreakoutResult(
        first_derivative=first_deriv,
        second_derivative=second_deriv,
        breakout_score=round(score, 4),
    )
