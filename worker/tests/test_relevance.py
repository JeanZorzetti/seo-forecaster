from unittest.mock import patch, MagicMock
from worker.filter.relevance import cosine_similarity, filter_by_relevance
from worker.models import BreakoutCandidate, Finalist

def test_cosine_similarity_identical():
    v = [1.0, 0.0, 0.0]
    assert abs(cosine_similarity(v, v) - 1.0) < 0.001

def test_cosine_similarity_orthogonal():
    a = [1.0, 0.0]
    b = [0.0, 1.0]
    assert abs(cosine_similarity(a, b)) < 0.001

def test_filter_returns_top_n():
    candidates = [
        BreakoutCandidate("llm agents", "hn", 0.9, 1.0, 2.0),
        BreakoutCandidate("flood brazil", "gdelt", 0.8, 1.0, 1.5),
        BreakoutCandidate("groq rate limit", "reddit", 0.7, 1.0, 1.2),
    ]
    niches = [
        {"id": 1, "name": "AI/Dev tools", "embedding": [1.0, 0.0, 0.0]},
    ]
    with patch("worker.filter.relevance.get_embedding") as mock_embed:
        def side_effect(text):
            if "flood" in text:
                return [0.0, 1.0, 0.0]
            return [0.9, 0.1, 0.0]
        mock_embed.side_effect = side_effect
        finalists = filter_by_relevance(candidates, niches, top_n=2)
    assert len(finalists) == 2
    terms = [f.term for f in finalists]
    assert "flood brazil" not in terms

def test_filter_returns_finalist_type():
    candidates = [BreakoutCandidate("llm agents", "hn", 0.9, 1.0, 2.0)]
    niches = [{"id": 1, "name": "AI", "embedding": [1.0, 0.0]}]
    with patch("worker.filter.relevance.get_embedding", return_value=[1.0, 0.0]):
        finalists = filter_by_relevance(candidates, niches)
    assert len(finalists) == 1
    f = finalists[0]
    assert isinstance(f, Finalist)
    assert f.term == "llm agents"
    assert f.matched_niche_id == 1
    assert 0.0 <= f.relevance_score <= 1.0

def test_filter_empty_inputs():
    assert filter_by_relevance([], []) == []
    assert filter_by_relevance([], [{"id": 1, "name": "AI", "embedding": [1.0]}]) == []

def test_filter_raises_when_all_embeddings_fail():
    candidates = [BreakoutCandidate("llm agents", "hn", 0.9, 1.0, 2.0)]
    niches = [{"id": 1, "name": "AI", "embedding": [1.0, 0.0]}]
    with patch("worker.filter.relevance.get_embedding", side_effect=Exception("Ollama down")):
        try:
            filter_by_relevance(candidates, niches)
            assert False, "Should have raised RuntimeError"
        except RuntimeError as e:
            assert "Ollama unavailable" in str(e)
