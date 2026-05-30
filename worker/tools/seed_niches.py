"""Run once: python -m worker.tools.seed_niches"""
import json
from worker.filter.relevance import get_embedding
from worker.persist.db import get_conn

NICHES = [
    {"name": "AI & Dev Tools", "description": "artificial intelligence, LLMs, developer tools, coding assistants, machine learning frameworks"},
    {"name": "SaaS & Startups", "description": "software as a service, micro-saas, startups, product market fit, indie hacking"},
    {"name": "SEO & Content Marketing", "description": "search engine optimization, content strategy, keyword research, Google ranking, organic traffic"},
    {"name": "Imobiliário Digital", "description": "mercado imobiliário, crm imobiliário, aluguel, compra e venda de imóveis, gestão de corretores"},
    {"name": "Clínicas & Saúde", "description": "clínicas de estética, dermato, procedimentos estéticos, gestão de pacientes, TISS"},
]

if __name__ == "__main__":
    conn = get_conn()
    for niche in NICHES:
        emb = get_embedding(niche["description"])
        with conn, conn.cursor() as cur:
            cur.execute(
                "INSERT INTO niches (name, description, embedding) VALUES (%s, %s, %s) ON CONFLICT (name) DO NOTHING",
                (niche["name"], niche["description"], json.dumps(emb))
            )
    print(f"Seeded {len(NICHES)} niches.")
