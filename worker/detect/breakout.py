import numpy as np
from dataclasses import dataclass
from datetime import date

EWMA_ALPHA = 0.3      # Higher values react faster to recent data; lower values smooth more
SIGMOID_SHIFT = 1.0   # Score exceeds 0.5 only when second_deriv > 1.0 — avoids false positives on mild acceleration

@dataclass
class BreakoutResult:
    first_derivative: float
    second_derivative: float
    breakout_score: float  # 0.0–1.0

def compute_breakout_score(series: list[tuple[date, int]]) -> BreakoutResult:
    if len(series) < 3:
        return BreakoutResult(0.0, 0.0, 0.0)

    counts = np.array([v for _, v in series], dtype=float)

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
    )
