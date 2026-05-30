import math
import json
import httpx
from worker.config import OLLAMA_URL, TOP_N_FINALISTS
from worker.models import BreakoutCandidate, Finalist

def get_embedding(text: str) -> list[float]:
    resp = httpx.post(
        f"{OLLAMA_URL}/api/embeddings",
        json={"model": "nomic-embed-text", "prompt": text},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()["embedding"]

def cosine_similarity(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x ** 2 for x in a))
    norm_b = math.sqrt(sum(x ** 2 for x in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)

def filter_by_relevance(
    candidates: list[BreakoutCandidate],
    niches: list[dict],
    top_n: int = TOP_N_FINALISTS,
) -> list[Finalist]:
    if not niches or not candidates:
        return []

    scored = []
    for candidate in candidates:
        try:
            term_emb = get_embedding(candidate.term)
        except Exception:
            continue  # skip if Ollama unavailable for this term

        best_score = 0.0
        best_niche_id = niches[0]["id"]
        for niche in niches:
            niche_emb = niche["embedding"]
            if isinstance(niche_emb, str):
                niche_emb = json.loads(niche_emb)
            sim = cosine_similarity(term_emb, niche_emb)
            if sim > best_score:
                best_score = sim
                best_niche_id = niche["id"]

        scored.append(Finalist(
            term=candidate.term,
            breakout_score=candidate.breakout_score,
            relevance_score=round(best_score, 4),
            matched_niche_id=best_niche_id,
            entities=candidate.entities,
        ))

    scored.sort(key=lambda f: f.relevance_score * f.breakout_score, reverse=True)
    return scored[:top_n]
