from unittest.mock import patch, MagicMock
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

def test_expand_returns_prediction():
    mock_content = """
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
    with patch("worker.reason.expand._get_groq_client") as mock_factory:
        mock_client = MagicMock()
        mock_factory.return_value = mock_client
        mock_resp = MagicMock()
        mock_resp.choices[0].message.content = mock_content
        mock_client.chat.completions.create.return_value = mock_resp
        prediction = expand_intent(make_finalist())

    assert isinstance(prediction, Prediction)
    assert prediction.term == "llm agents replacing devs"
    assert len(prediction.intents) > 0
    assert len(prediction.content_gaps) > 0

@patch("worker.reason.expand.time.sleep")
def test_expand_fallback_on_non_rate_limit_error(mock_sleep):
    # Non-rate-limit errors exhaust retries then return an empty prediction.
    with patch("worker.reason.expand._get_groq_client") as mock_factory:
        mock_client = MagicMock()
        mock_factory.return_value = mock_client
        mock_client.chat.completions.create.side_effect = Exception("server error 500")
        prediction = expand_intent(make_finalist())
    assert isinstance(prediction, Prediction)
    assert prediction.intents == []
    assert prediction.content_gaps == []
    assert mock_sleep.called  # retry backoff attempted

def test_expand_reraises_rate_limit():
    # Rate-limit errors propagate so the batch driver can stop calling Groq.
    with patch("worker.reason.expand._get_groq_client") as mock_factory:
        mock_client = MagicMock()
        mock_factory.return_value = mock_client
        mock_client.chat.completions.create.side_effect = Exception("429 rate_limit_exceeded")
        try:
            expand_intent(make_finalist())
            assert False, "should have re-raised the rate-limit error"
        except Exception as e:
            assert "429" in str(e)

def test_expand_preserves_scores():
    with patch("worker.reason.expand._get_groq_client") as mock_factory:
        mock_client = MagicMock()
        mock_factory.return_value = mock_client
        mock_resp = MagicMock()
        mock_resp.choices[0].message.content = "## Long-tail searches\n1. test\n## Content gaps\n- gap"
        mock_client.chat.completions.create.return_value = mock_resp
        prediction = expand_intent(make_finalist())
    assert prediction.breakout_score == 0.9
    assert prediction.relevance_score == 0.85
    assert prediction.matched_niche_id == 1


# ── expand_intents (batch with throttle) ──────────────────────────────────

@patch("worker.reason.expand.time.sleep")
def test_expand_intents_all_succeed(mock_sleep):
    finalists = [make_finalist(f"term {i}") for i in range(3)]
    with patch("worker.reason.expand._get_groq_client") as mock_factory:
        mock_client = MagicMock()
        mock_factory.return_value = mock_client
        mock_resp = MagicMock()
        mock_resp.choices[0].message.content = "## Long-tail searches\n1. a\n## Content gaps\n- b"
        mock_client.chat.completions.create.return_value = mock_resp
        preds = expand_intents(finalists)
    assert len(preds) == 3
    assert all(len(p.intents) > 0 for p in preds)

@patch("worker.reason.expand.time.sleep")
def test_expand_intents_stops_on_rate_limit(mock_sleep):
    # 4 finalists; first call 429s → remaining get empty expansion, Groq called once.
    finalists = [make_finalist(f"term {i}") for i in range(4)]
    with patch("worker.reason.expand._get_groq_client") as mock_factory:
        mock_client = MagicMock()
        mock_factory.return_value = mock_client
        mock_client.chat.completions.create.side_effect = Exception("429 rate_limit_exceeded")
        preds = expand_intents(finalists)
    assert len(preds) == 4
    assert all(p.intents == [] for p in preds)
    # Only one Groq call attempted (stopped after the first 429)
    assert mock_client.chat.completions.create.call_count == 1
