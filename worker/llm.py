"""
Pluggable LLM provider for the reasoning/expansion step.

Switch providers with the LLM_PROVIDER env var:
  - "ollama" (default): local, unlimited, runs on CPU (qwen2.5:3b-instruct).
    Ideal for iterating fast during the test phase — no rate limits.
  - "groq": cloud llama-3.3-70b — smarter but capped by the free tier
    (1000 req/day, ~6k tokens/min).

Both expose the same `chat(prompt) -> str` interface so callers don't care
which backend is active.
"""
import httpx
from worker.config import (
    LLM_PROVIDER, OLLAMA_URL, OLLAMA_EXPAND_MODEL, GROQ_API_KEY,
)

_groq_client = None


def _groq():
    global _groq_client
    if _groq_client is None:
        from groq import Groq
        if not GROQ_API_KEY:
            raise RuntimeError("LLM_PROVIDER=groq but GROQ_API_KEY is not set")
        # max_retries=0: callers handle 429s (fall back / stop) themselves.
        _groq_client = Groq(api_key=GROQ_API_KEY, max_retries=0)
    return _groq_client


def _chat_groq(prompt: str, max_tokens: int) -> str:
    resp = _groq().chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
        max_tokens=max_tokens,
    )
    return resp.choices[0].message.content or ""


def _chat_ollama(prompt: str, max_tokens: int) -> str:
    base = OLLAMA_URL.rstrip("/")
    resp = httpx.post(
        f"{base}/api/generate",
        json={
            "model": OLLAMA_EXPAND_MODEL,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.3, "num_predict": max_tokens},
        },
        timeout=120,  # CPU inference of a 3B model can take a while
        follow_redirects=True,
    )
    resp.raise_for_status()
    return resp.json().get("response", "")


def chat(prompt: str, max_tokens: int = 512) -> str:
    """Run a single completion against the configured provider. Raises on failure."""
    if LLM_PROVIDER == "groq":
        return _chat_groq(prompt, max_tokens)
    return _chat_ollama(prompt, max_tokens)


def is_rate_limited(err: Exception) -> bool:
    """True only for Groq rate limits — Ollama has none."""
    if LLM_PROVIDER != "groq":
        return False
    msg = str(err).lower()
    return "429" in msg or "rate_limit" in msg or "rate limit" in msg
