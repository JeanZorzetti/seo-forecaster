import time
from datetime import date
from groq import Groq
from worker.config import GROQ_API_KEY
from worker.models import Finalist, Prediction

_groq_client = None

def _get_groq_client() -> Groq:
    global _groq_client
    if _groq_client is None:
        _groq_client = Groq(api_key=GROQ_API_KEY)
    return _groq_client

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
        except Exception:
            if attempt < retries - 1:
                time.sleep(2 ** attempt)

    # Fallback: save without expansion rather than lose the pauta
    return Prediction(
        term=finalist.term,
        breakout_score=finalist.breakout_score,
        relevance_score=finalist.relevance_score,
        matched_niche_id=finalist.matched_niche_id,
        intents=[],
        content_gaps=[],
        status="emerging",
    )
