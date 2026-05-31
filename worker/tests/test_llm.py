from unittest.mock import patch, MagicMock
import worker.llm as llm


def test_chat_ollama_default():
    # Default provider is ollama → hits /api/generate and returns "response"
    with patch("worker.llm.LLM_PROVIDER", "ollama"), \
         patch("worker.llm.httpx.post") as mock_post:
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"response": "## Long-tail searches\n1. test"}
        mock_resp.raise_for_status.return_value = None
        mock_post.return_value = mock_resp
        out = llm.chat("hello", max_tokens=100)
    assert "Long-tail" in out
    # called the Ollama generate endpoint
    called_url = mock_post.call_args[0][0]
    assert called_url.endswith("/api/generate")


def test_chat_groq_when_selected():
    with patch("worker.llm.LLM_PROVIDER", "groq"), \
         patch("worker.llm._groq") as mock_groq_factory:
        mock_client = MagicMock()
        mock_groq_factory.return_value = mock_client
        mock_resp = MagicMock()
        mock_resp.choices[0].message.content = "groq output"
        mock_client.chat.completions.create.return_value = mock_resp
        out = llm.chat("hello")
    assert out == "groq output"


def test_is_rate_limited_only_for_groq():
    err = Exception("429 rate_limit_exceeded")
    with patch("worker.llm.LLM_PROVIDER", "groq"):
        assert llm.is_rate_limited(err) is True
    with patch("worker.llm.LLM_PROVIDER", "ollama"):
        # Ollama has no rate limit — never treated as one
        assert llm.is_rate_limited(err) is False


def test_chat_ollama_strips_trailing_slash():
    with patch("worker.llm.LLM_PROVIDER", "ollama"), \
         patch("worker.llm.OLLAMA_URL", "http://ollama:11434/"), \
         patch("worker.llm.httpx.post") as mock_post:
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"response": "x"}
        mock_resp.raise_for_status.return_value = None
        mock_post.return_value = mock_resp
        llm.chat("hi")
    called_url = mock_post.call_args[0][0]
    assert called_url == "http://ollama:11434/api/generate"  # no double slash
