from unittest.mock import patch
from worker.reason.expand import expand_intent, expand_intents
from worker.models import Finalist, Prediction

def make_finalist(term="llm agents replacing devs"):
    return Finalist(
        term=term,
        breakout_score=0.9,
        relevance_score=0.85,
        matched_niche_id=1,
        entities=["OpenAI", "Anthropic"],
    )

FULL_RESPONSE = """
## Long-tail searches
1. como usar agentes llm no trabalho
2. llm agents tutorial em português
3. ferramentas de agentes ia para devs
4. llm agents vs copilot diferença
5. como criar agente llm com python

## Content gaps
- Nenhum guia em PT-BR explica como criar um agente do zero
- Comparativos de ferramentas ainda sem benchmark local
"""

def test_expand_returns_prediction():
    with patch("worker.reason.expand.chat", return_value=FULL_RESPONSE):
        prediction = expand_intent(make_finalist())
    assert isinstance(prediction, Prediction)
    assert prediction.term == "llm agents replacing devs"
    assert len(prediction.intents) > 0
    assert len(prediction.content_gaps) > 0

@patch("worker.reason.expand.time.sleep")
def test_expand_fallback_on_generic_error(mock_sleep):
    # Non-rate-limit errors exhaust retries then return an empty prediction.
    with patch("worker.reason.expand.chat", side_effect=Exception("server error 500")), \
         patch("worker.reason.expand.is_rate_limited", return_value=False):
        prediction = expand_intent(make_finalist())
    assert isinstance(prediction, Prediction)
    assert prediction.intents == []
    assert prediction.content_gaps == []
    assert mock_sleep.called

def test_expand_reraises_rate_limit():
    # Rate-limit errors propagate so the batch driver can stop calling the provider.
    with patch("worker.reason.expand.chat", side_effect=Exception("429 rate_limit_exceeded")), \
         patch("worker.reason.expand.is_rate_limited", return_value=True):
        try:
            expand_intent(make_finalist())
            assert False, "should have re-raised the rate-limit error"
        except Exception as e:
            assert "429" in str(e)

def test_expand_preserves_scores():
    with patch("worker.reason.expand.chat", return_value="## Long-tail searches\n1. test\n## Content gaps\n- gap"):
        prediction = expand_intent(make_finalist())
    assert prediction.breakout_score == 0.9
    assert prediction.relevance_score == 0.85
    assert prediction.matched_niche_id == 1


# ── expand_intents (batch) ────────────────────────────────────────────────

def test_expand_intents_all_succeed():
    finalists = [make_finalist(f"term {i}") for i in range(3)]
    with patch("worker.reason.expand.chat", return_value="## Long-tail searches\n1. a\n## Content gaps\n- b"):
        preds = expand_intents(finalists)
    assert len(preds) == 3
    assert all(len(p.intents) > 0 for p in preds)

def test_expand_intents_stops_on_rate_limit():
    # First call rate-limits → remaining get empty expansion, provider called once.
    finalists = [make_finalist(f"term {i}") for i in range(4)]
    with patch("worker.reason.expand.chat", side_effect=Exception("429 rate_limit_exceeded")) as mock_chat, \
         patch("worker.reason.expand.is_rate_limited", return_value=True):
        preds = expand_intents(finalists)
    assert len(preds) == 4
    assert all(p.intents == [] for p in preds)
    assert mock_chat.call_count == 1
