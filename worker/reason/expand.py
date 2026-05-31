import time
import logging
from datetime import date
from worker.config import LLM_PROVIDER
from worker.llm import chat, is_rate_limited
from worker.models import Finalist, Prediction

logger = logging.getLogger(__name__)

# Pacing between calls. Only needed for Groq's per-minute token cap; Ollama is
# local and unlimited, so we don't sleep there.
EXPAND_SLEEP_SECONDS = 4.0 if LLM_PROVIDER == "groq" else 0.0


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
            content = chat(prompt, max_tokens=512)
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
            if is_rate_limited(e):
                raise  # let the batch driver stop calling the provider
            if attempt < retries - 1:
                time.sleep(2 ** attempt)

    # Fallback: save without expansion rather than lose the pauta
    return _empty_prediction(finalist)


def expand_intents(finalists: list[Finalist]) -> list[Prediction]:
    """
    Expand many finalists. With Ollama (default) this runs unthrottled. With
    Groq, calls are paced and we stop after the first rate-limit error.
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
            if is_rate_limited(e):
                logger.warning(
                    "[expand] Groq rate limit hit — empty expansion for the rest "
                    "of this run; pautas still saved with score + status. "
                    "Tip: set LLM_PROVIDER=ollama to avoid rate limits."
                )
                rate_limited = True
            predictions.append(_empty_prediction(finalist))

        if EXPAND_SLEEP_SECONDS and i < len(finalists) - 1 and not rate_limited:
            time.sleep(EXPAND_SLEEP_SECONDS)

    return predictions
