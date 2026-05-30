CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE niches (
  id SERIAL PRIMARY KEY,
  name TEXT NOT NULL,
  description TEXT NOT NULL,
  embedding vector(768),
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE term_history (
  id SERIAL PRIMARY KEY,
  term TEXT NOT NULL,
  source TEXT NOT NULL,
  count INTEGER NOT NULL,
  observed_date DATE NOT NULL,
  UNIQUE(term, source, observed_date)
);

CREATE TABLE signals (
  id SERIAL PRIMARY KEY,
  term TEXT NOT NULL,
  source TEXT NOT NULL,
  raw_count INTEGER NOT NULL,
  entities JSONB DEFAULT '[]',
  first_derivative FLOAT,
  second_derivative FLOAT,
  breakout_score FLOAT,
  run_date DATE NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE predictions (
  id SERIAL PRIMARY KEY,
  term TEXT NOT NULL,
  breakout_score FLOAT NOT NULL,
  relevance_score FLOAT NOT NULL,
  matched_niche_id INTEGER REFERENCES niches(id),
  forecast JSONB,
  intents JSONB DEFAULT '[]',
  content_gaps JSONB DEFAULT '[]',
  status TEXT NOT NULL DEFAULT 'emerging',
  run_date DATE NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(term, matched_niche_id)
);

CREATE TABLE runs (
  id SERIAL PRIMARY KEY,
  started_at TIMESTAMPTZ NOT NULL,
  finished_at TIMESTAMPTZ,
  signals_count INTEGER DEFAULT 0,
  finalists_count INTEGER DEFAULT 0,
  status TEXT NOT NULL DEFAULT 'running',
  error_log JSONB DEFAULT '[]'
);

CREATE UNIQUE INDEX predictions_term_no_niche ON predictions(term) WHERE matched_niche_id IS NULL;
