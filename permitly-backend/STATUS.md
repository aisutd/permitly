# Backend task status (risk classifier + LLM part)

| ID | Task | Status | Where |
|---|---|---|---|
| B1 | Setup: config, CORS, health | DONE | config.py, main.py, .env.example, README.md |
| B2 | Load models once at startup | DONE (classifier). Embedding model for RAG: hook ready, not built yet | main.py lifespan, risk_model.py |
| B3 | POST /classify | DONE | main.py, risk_model.py, tests/test_classify.py |
| B4 | GET /states, /states/{code} | NOT STARTED (needs the extraction data in Supabase) | - |
| B5 | POST /ask (RAG) | NOT STARTED | - |
| B6 | Citation verification | NOT STARTED (needs B5) | - |
| B7 | LLM timeouts + error handling | DONE for the profile LLM call. /ask must reuse llm.chat() | llm.py, errors.py, main.py |
| B8 | Rate limiting + request logging | DONE for current endpoints. Add Depends(rate_limit) to /ask | ratelimit.py, main.py, db.py |
| B9 | Evaluation set + script | NOT STARTED (needs B5) | - |
| B10 | Spot-check extraction data | NOT STARTED (needs B4) | - |
| B11 | Re-ingestion script | NOT STARTED | - |
| B12 | Deploy backend + database | PARTLY: Supabase schema + deploy steps written; not deployed yet | supabase/schema.sql, README.md |
