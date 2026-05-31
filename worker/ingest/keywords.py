"""
LLM-based keyword extraction (batch) with graceful fallback to rule-based n-grams.

Sending one Groq call per title would exhaust the free-tier rate limit, so we
batch many titles into a single call. The Groq free tier caps at 12k tokens per
minute (TPM), so we (a) cap how many titles we send to the LLM, (b) pace batches
with a short sleep, and (c) stop calling Groq for the rest of the run after the
first 429 — falling back to rule-based n-grams. Ingestion never breaks.
"""
import json
import logging
import re
import time

from worker.ingest.utils import extract_terms as _ngram_terms

logger = logging.getLogger(__name__)

# Free-tier guardrails. Each batch of ~15 titles costs roughly 1.5-2.5k tokens
# (prompt + completion). Sleeping ~6s between batches keeps us under the 12k
# tokens-per-minute cap with margin shared with the Groq calls in reason/expand.
LLM_MAX_TITLES = 120        # cap titles sent to the LLM per run; rest use n-grams
BATCH_SLEEP_SECONDS = 6.0   # pace between batches to respect TPM

# Lazy Groq client (avoids import-time env errors and shares the pattern used
# by reason/expand.py).
_groq_client = None


def _get_groq_client():
    global _groq_client
    if _groq_client is None:
        from groq import Groq
        from worker.config import GROQ_API_KEY
        # max_retries=0: we handle 429 ourselves (fall back to n-grams) instead
        # of letting the SDK block for ~9s per retry and stall the pipeline.
        _groq_client = Groq(api_key=GROQ_API_KEY, max_retries=0)
    return _groq_client


_BATCH_PROMPT = """Você é um analista de SEO. Para cada título abaixo, extraia de 1 a 3 KEYWORDS de busca reais — termos que uma pessoa realmente digitaria no Google, não fragmentos de frase.

Regras:
- Keywords concretas: produtos, empresas, tecnologias, conceitos, eventos.
- 2 a 4 palavras cada, em minúsculas.
- Ignore palavras vazias e números soltos.
- Se um título não tiver keyword útil, retorne lista vazia para ele.

Responda APENAS um JSON válido no formato:
{{"results": [["keyword1", "keyword2"], ["keyword1"], ...]}}
A ordem e a quantidade de listas deve bater exatamente com a ordem dos títulos.

Títulos:
{titles}
"""


def _parse_batch(content: str, expected: int) -> list[list[str]] | None:
    # Extract the first JSON object from the response (model may add prose).
    match = re.search(r"\{.*\}", content, re.DOTALL)
    if not match:
        return None
    try:
        data = json.loads(match.group(0))
        results = data.get("results")
    except Exception:
        return None
    if not isinstance(results, list) or len(results) != expected:
        return None
    cleaned = []
    for item in results:
        if not isinstance(item, list):
            cleaned.append([])
            continue
        cleaned.append([str(k).strip().lower() for k in item if str(k).strip()])
    return cleaned


def _is_rate_limit(err: Exception) -> bool:
    msg = str(err).lower()
    return "429" in msg or "rate_limit" in msg or "rate limit" in msg


def extract_keywords_batch(titles: list[str], batch_size: int = 15) -> list[list[str]]:
    """
    Extract SEO keywords for many titles using paced, batched Groq calls.

    Returns a list parallel to `titles`; each element is a list of keyword
    strings. To respect the free-tier TPM cap:
      - only the first LLM_MAX_TITLES titles go to the LLM; the rest use n-grams
      - batches are paced with BATCH_SLEEP_SECONDS between them
      - on the first 429, we stop calling Groq and n-gram the remainder
    """
    if not titles:
        return []

    out: list[list[str]] = [_ngram_terms(t) for t in titles]  # safe default

    llm_titles = titles[:LLM_MAX_TITLES]
    rate_limited = False

    for start in range(0, len(llm_titles), batch_size):
        if rate_limited:
            break  # remaining titles keep their n-gram default

        chunk = llm_titles[start:start + batch_size]
        numbered = "\n".join(f"{i+1}. {t}" for i, t in enumerate(chunk))
        prompt = _BATCH_PROMPT.format(titles=numbered)

        parsed = None
        try:
            client = _get_groq_client()
            resp = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
                max_tokens=1024,
                response_format={"type": "json_object"},
            )
            parsed = _parse_batch(resp.choices[0].message.content, len(chunk))
        except Exception as e:
            if _is_rate_limit(e):
                logger.warning("[keywords] Groq TPM hit — n-gram fallback for the rest of this run")
                rate_limited = True
            else:
                logger.warning(f"[keywords] Groq batch failed, n-gram fallback: {e}")

        if parsed is not None:
            for j in range(len(chunk)):
                if parsed[j]:
                    out[start + j] = parsed[j]
                # else: keep the n-gram default already in `out`

        # Pace the next batch to stay under the TPM cap (skip after the last one).
        if start + batch_size < len(llm_titles) and not rate_limited:
            time.sleep(BATCH_SLEEP_SECONDS)

    return out
