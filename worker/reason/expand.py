import json
import re
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


# Ask for JSON directly — far more robust than parsing markdown headings, which
# small models format inconsistently. qwen2.5 and llama-3.3 both follow this well.
PROMPT_TEMPLATE = """Estamos em {current_date}. O ANO ATUAL é {current_year}. Nunca use anos passados como {prev_year} ou anteriores — se citar um ano, use {current_year} ou {next_year}.

Você é um especialista em SEO. O termo "{term}" está acelerando em volume agora (fontes: {sources}). Entidades detectadas: {entities}.

Faça engenharia reversa da intenção de busca. Responda APENAS um objeto JSON válido, sem texto antes ou depois, exatamente neste formato:
{{
  "long_tail": ["busca 1", "busca 2", "busca 3", "busca 4", "busca 5"],
  "content_gaps": ["dor informacional sem resposta", "dor comercial sem resposta"]
}}

As buscas devem ser termos exatos que as pessoas digitarão em 2 semanas. Seja técnico e específico."""


def _parse_response(content: str) -> tuple[list[str], list[str]]:
    """Extract long_tail + content_gaps from a JSON response (tolerant of prose)."""
    match = re.search(r"\{.*\}", content, re.DOTALL)
    if not match:
        return [], []
    try:
        data = json.loads(match.group(0))
    except Exception:
        return [], []

    def _clean_list(v) -> list[str]:
        if not isinstance(v, list):
            return []
        out = []
        for item in v:
            s = str(item).strip().strip('"').strip()
            if s:
                out.append(s)
        return out

    intents = _clean_list(data.get("long_tail"))
    gaps = _clean_list(data.get("content_gaps"))
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
            content = chat(prompt, max_tokens=700)
            intents, gaps = _parse_response(content)
            # Empty parse on a 200 response → retry once (model formatting hiccup)
            if not intents and not gaps and attempt < retries - 1:
                continue
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
                    "of this run. Tip: set LLM_PROVIDER=ollama to avoid rate limits."
                )
                rate_limited = True
            predictions.append(_empty_prediction(finalist))

        if EXPAND_SLEEP_SECONDS and i < len(finalists) - 1 and not rate_limited:
            time.sleep(EXPAND_SLEEP_SECONDS)

    return predictions
