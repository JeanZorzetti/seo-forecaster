from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

@dataclass
class Signal:
    term: str
    source: str  # 'gdelt' | 'hn' | 'reddit'
    raw_count: int
    timestamp: datetime
    entities: list[str] = field(default_factory=list)

@dataclass
class BreakoutCandidate:
    term: str
    source: str
    breakout_score: float
    first_derivative: float
    second_derivative: float
    entities: list[str] = field(default_factory=list)

@dataclass
class Finalist:
    term: str
    breakout_score: float
    relevance_score: float
    matched_niche_id: int
    entities: list[str] = field(default_factory=list)

@dataclass
class Prediction:
    term: str
    breakout_score: float
    relevance_score: float
    matched_niche_id: int
    forecast: Optional[dict] = None   # {curve: [...], peak_day: int, confidence: float}
    intents: Optional[list] = None    # list of long-tail strings
    content_gaps: Optional[list] = None
    status: str = "emerging"          # emerging | maturing | saturating
