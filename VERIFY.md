# Verification Guide

## Automated (CI-safe)

```bash
# Python tests (30 tests, no real APIs needed)
cd seo-forecaster
export DATABASE_URL="postgresql://test/test"
export GROQ_API_KEY="x"
export REDDIT_CLIENT_ID="x"
export REDDIT_CLIENT_SECRET="x"
export REDDIT_USER_AGENT="x"
python -m pytest worker/tests/ -v

# Dashboard TypeScript
cd dashboard && npx tsc --noEmit
```

## Manual (requires Docker + real credentials)

### 1. Start containers
```bash
docker-compose up -d
docker exec -it seo-forecaster-ollama-1 ollama pull nomic-embed-text
```

### 2. Apply DB migration
```bash
python -c "from worker.persist.db import run_migration; run_migration('worker/migrations/001_initial.sql')"
```

### 3. Seed niches (requires Ollama running)
```bash
python -m worker.tools.seed_niches
```

### 4. Run pipeline once
```bash
python -m worker.pipeline
```
Expected: logs show `[hn] N signals`, `[reddit] N signals`, candidates found, finalists filtered, predictions upserted.

### 5. Verify DB
```bash
psql postgresql://seouser:seopass@localhost:5432/seoforecaster \
  -c "SELECT term, status, breakout_score FROM predictions LIMIT 10;"
psql postgresql://seouser:seopass@localhost:5432/seoforecaster \
  -c "SELECT id, status, signals_count, finalists_count, error_log FROM runs;"
```

### 6. Open dashboard
```bash
cd dashboard && npm run dev
```
Open http://localhost:3000. Verify:
- Predictions table populated
- Filter by status works
- Click a term → detail page shows chart/intents/gaps
- Badge "previsão preliminar" appears for new terms
- Confidence badge shows correctly

### 7. Test resilience
Set `REDDIT_CLIENT_ID=invalid` and re-run pipeline. Verify:
- Pipeline completes (doesn't crash)
- `runs.error_log` contains Reddit error
- `runs.status = 'partial'`
- Predictions still populated from HN + GDELT
