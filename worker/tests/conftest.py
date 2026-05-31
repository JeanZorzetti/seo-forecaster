import pytest

@pytest.fixture(autouse=True)
def _set_env(monkeypatch):
    # Only DATABASE_URL is strictly required at import time. GROQ_API_KEY is
    # optional (only needed when LLM_PROVIDER=groq); set it so tests can patch
    # either provider freely.
    monkeypatch.setenv("DATABASE_URL", "postgresql://test/test")
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
