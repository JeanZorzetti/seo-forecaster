"""
LLM-based keyword extraction (batch) with graceful fallback to rule-based n-grams.

Sending one Groq call per title would exhaust the free-tier rate limit, so we
batch many titles into a single call. If Groq is unavailable (no key, rate
limit, parse error), we fall back to the stopword-filtered n-gram extractor in
`utils.extract_terms`, so ingestion never breaks.
"""
import json
import logging
import re

from worker.ingest.utils import extract_terms as _ngram_terms

logger = logging.getLogger(__name__)

# Lazy Groq client (avoids import-time env errors and shares the pattern used
# by reason/expand.py).
_groq_client = None


def _get_groq_client():
    global _groq_client
    if _groq_client is None:
        from groq import Groq
        from worker.config import GROQ_API_KEY
        _groq_client = Groq(api_key=GROQ_API_KEY)
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


def extract_keywords_batch(titles: list[str], batch_size: int = 30) -> list[list[str]]:
    """
    Extract SEO keywords for many titles using batched Groq calls.

    Returns a list parallel to `titles`; each element is a list of keyword
    strings. Falls back to rule-based n-grams for any title whose batch fails.
    """
    if not titles:
        return []

    out: list[list[str]] = [None] * len(titles)  # type: ignore

    for start in range(0, len(titles), batch_size):
        chunk = titles[start:start + batch_size]
        numbered = "\n".join(f"{i+1}. {t}" for i, t in enumerate(chunk))
        prompt = _BATCH_PROMPT.format(titles=numbered)

        parsed = None
        try:
            client = _get_groq_client()
            resp = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
                max_tokens=2048,
                response_format={"type": "json_object"},
            )
            parsed = _parse_batch(resp.choices[0].message.content, len(chunk))
        except Exception as e:
            logger.warning(f"[keywords] Groq batch failed, using n-gram fallback: {e}")

        for j, title in enumerate(chunk):
            idx = start + j
            if parsed is not None and parsed[j]:
                out[idx] = parsed[j]
            else:
                # Fallback: rule-based n-grams for this specific title
                out[idx] = _ngram_terms(title)

    return out
