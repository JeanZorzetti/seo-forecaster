import time
import logging
from datetime import date
from groq import Groq
from worker.config import GROQ_API_KEY
from worker.models import Finalist, Prediction

logger = logging.getLogger(__name__)

# Each expansion call costs ~700-900 tokens. The Groq free tier caps at 12k
# tokens/minute, so we pace calls (~4s apart → ~15/min) and, on the first 429,
# stop calling Groq for the rest of the run (remaining finalists get empty
# expansion rather than blocking on slow retries).
EXPAND_SLEEP_SECONDS = 4.0

_groq_client = None


def _get_groq_client() -> Groq:
    global _groq_client
    if _groq_client is None:
        # max_retries=0: we handle 429 ourselves instead of blocking ~9s/retry.
        _groq_client = Groq(api_key=GROQ_API_KEY, max_retries=0)
    return _groq_client


def _is_rate_limit(err: Exception) -> bool:
    msg = str(err).lower()
    return "429" in msg or "rate_limit" in msg or "rate limit" in msg


def _rate_limit_kind(err: Exception) -> str:
    """Distinguish a per-day cap (resets in 24h) from a per-minute cap."""
    msg = str(err).lower()
    if "per day" in msg or "rpd" in msg or "requests per day" in msg:
        return "daily quota (RPD) exhausted — resets in ~24h"
    if "per minute" in msg or "tpm" in msg or "tokens per minute" in msg:
        return "per-minute quota (TPM) — resets within a minute"
    return "rate limit"


PROMPT_TEMPLATE = """
Estamos em {current_date}. O ANO ATUAL é {current_year}. Nunca use anos passados como {prev_year} ou anteriores nas buscas — se citar um ano, use {current_year} ou {next_year}.

Você é um especialista em SEO e comportamento de busca. O termo "{term}" está acelerando em volume agora (fontes: {sources}).
Entidades relacionadas detectadas: {entities}.

Faça engenharia reversa da intenção de busca e responda EXATAMENTE neste formato:

## Long-tail searches
1. [busca exata que as pessoas farão em 2 semanas]
2. [busca exata]
3. [busca exata]
4. [busca exata]
5. [busca exata]

## Content gaps
- [dor informacional ainda sem resposta nas grandes mídias]
- [dor comercial ainda sem resposta]

Seja direto e técnico. Sem introduções.
"""


def _parse_response(content: str) -> tuple[list[str], list[str]]:
    intents, gaps = [], []
    section = None
    for line in content.splitlines():
        line = line.strip()
        if "Long-tail" in line:
            section = "intents"
        elif "Content gaps" in line:
            section = "gaps"
        elif section == "intents" and line and line[0].isdigit():
            intents.append(line.split(".", 1)[-1].strip())
        elif section == "gaps" and line.startswith("-"):
            gaps.append(line[1:].strip())
    return intents, gaps


def _empty_prediction(finalist: Finalist) -> Prediction:
    return Prediction(
        term=finalist.term,
        breakout_score=finalist.breakout_score,
        relevance_score=finalist.relevance_score,
        matched_niche_id=finalist.matched_niche_id,
        intents=[],
        content_gaps=[],
        status="emerging",
    )


def expand_intent(finalist: Finalist, retries: int = 3) -> Prediction:
    today = date.today()
    prompt = PROMPT_TEMPLATE.format(
        term=finalist.term,
        sources="gdelt/hn/reddit",
        entities=", ".join(finalist.entities or []) or "N/A",
        current_date=today.strftime("%d/%m/%Y"),
        current_year=today.year,
        prev_year=today.year - 1,
        next_year=today.year + 1,
    )
    for attempt in range(retries):
        try:
            client = _get_groq_client()
            resp = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=512,
            )
            content = resp.choices[0].message.content
            intents, gaps = _parse_response(content)
            return Prediction(
                term=finalist.term,
                breakout_score=finalist.breakout_score,
                relevance_score=finalist.relevance_score,
                matched_niche_id=finalist.matched_niche_id,
                intents=intents,
                content_gaps=gaps,
                status="emerging",
            )
        except Exception as e:
            if _is_rate_limit(e):
                raise  # let the batch driver stop calling Groq
            if attempt < retries - 1:
                time.sleep(2 ** attempt)

    # Fallback: save without expansion rather than lose the pauta
    return _empty_prediction(finalist)


def expand_intents(finalists: list[Finalist]) -> list[Prediction]:
    """
    Expand many finalists with pacing to respect the Groq free-tier TPM cap.

    Calls are spaced EXPAND_SLEEP_SECONDS apart. On the first rate-limit error,
    we stop calling Groq and return empty expansions for the rest of the run.
    """
    predictions: list[Prediction] = []
    rate_limited = False

    for i, finalist in enumerate(finalists):
        if rate_limited:
            predictions.append(_empty_prediction(finalist))
            continue

        try:
            predictions.append(expand_intent(finalist))
        except Exception as e:
            if _is_rate_limit(e):
                logger.warning(
                    f"[expand] Groq rate limit — {_rate_limit_kind(e)}. "
                    "Empty expansion (intents/gaps) for the rest of this run; "
                    "pautas still saved with score + status."
                )
                rate_limited = True
                predictions.append(_empty_prediction(finalist))
            else:
                predictions.append(_empty_prediction(finalist))

        # Pace the next call to stay under the TPM cap (skip after the last one).
        if i < len(finalists) - 1 and not rate_limited:
            time.sleep(EXPAND_SLEEP_SECONDS)

    return predictions
