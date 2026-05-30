from unittest.mock import patch, MagicMock
from worker.reason.expand import expand_intent
from worker.models import Finalist, Prediction

def make_finalist():
    return Finalist(
        term="llm agents replacing devs",
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
def test_expand_fallback_on_groq_error(mock_sleep):
    with patch("worker.reason.expand._get_groq_client") as mock_factory:
        mock_client = MagicMock()
        mock_factory.return_value = mock_client
        mock_client.chat.completions.create.side_effect = Exception("rate limit")
        prediction = expand_intent(make_finalist())
    assert isinstance(prediction, Prediction)
    assert prediction.intents == []
    assert prediction.content_gaps == []
    assert mock_sleep.called  # verify retry backoff was attempted

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
