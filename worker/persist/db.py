import json
from datetime import date, datetime
from typing import Optional
import psycopg2
import psycopg2.extras
from worker.config import DATABASE_URL
from worker.models import Prediction

def get_conn():
    return psycopg2.connect(DATABASE_URL)

def run_migration(sql_path: str):
    conn = get_conn()
    with conn, conn.cursor() as cur:
        cur.execute(open(sql_path).read())

def upsert_term_history(term: str, source: str, count: int, observed_date: date):
    conn = get_conn()
    with conn, conn.cursor() as cur:
        cur.execute("""
            INSERT INTO term_history (term, source, count, observed_date)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (term, source, observed_date)
            DO UPDATE SET count = EXCLUDED.count
        """, (term, source, count, observed_date))

def get_term_history(term: str, source: str, days: int = 30) -> list[tuple[date, int]]:
    conn = get_conn()
    with conn.cursor() as cur:
        cur.execute("""
            SELECT observed_date, count FROM term_history
            WHERE term = %s AND source = %s
            ORDER BY observed_date ASC
            LIMIT %s
        """, (term, source, days))
        return cur.fetchall()

def get_all_niches() -> list[dict]:
    conn = get_conn()
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute("SELECT id, name, description, embedding FROM niches")
        return [dict(r) for r in cur.fetchall()]

def upsert_prediction(p: Prediction, run_date: date):
    conn = get_conn()
    with conn, conn.cursor() as cur:
        cur.execute("""
            INSERT INTO predictions
              (term, breakout_score, relevance_score, matched_niche_id,
               forecast, intents, content_gaps, status, run_date, updated_at)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s, NOW())
            ON CONFLICT (term, matched_niche_id)
            DO UPDATE SET
              breakout_score = EXCLUDED.breakout_score,
              relevance_score = EXCLUDED.relevance_score,
              forecast = EXCLUDED.forecast,
              intents = EXCLUDED.intents,
              content_gaps = EXCLUDED.content_gaps,
              status = EXCLUDED.status,
              run_date = EXCLUDED.run_date,
              updated_at = NOW()
        """, (
            p.term, p.breakout_score, p.relevance_score, p.matched_niche_id,
            json.dumps(p.forecast) if p.forecast else None,
            json.dumps(p.intents or []),
            json.dumps(p.content_gaps or []),
            p.status, run_date
        ))

def start_run() -> int:
    conn = get_conn()
    with conn, conn.cursor() as cur:
        cur.execute(
            "INSERT INTO runs (started_at, status) VALUES (NOW(), 'running') RETURNING id"
        )
        return cur.fetchone()[0]

def finish_run(run_id: int, signals_count: int, finalists_count: int,
               status: str, errors: list[str]):
    conn = get_conn()
    with conn, conn.cursor() as cur:
        cur.execute("""
            UPDATE runs SET
              finished_at = NOW(),
              signals_count = %s,
              finalists_count = %s,
              status = %s,
              error_log = %s
            WHERE id = %s
        """, (signals_count, finalists_count, status, json.dumps(errors), run_id))
