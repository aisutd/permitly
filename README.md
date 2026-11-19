# Permitly Backend (Risk Classifier + LLM profile)

POST a business description -> get a risk level (High/Medium/Low), the probability,
the top reasons (words that decided it), the 3 most similar labeled examples, and an LLM profile.
FastAPI runs the models. Supabase (Postgres) is the database.

## Setup (once) - VS Code terminal
1. `python3 -m venv venv`
2. Mac: `source venv/bin/activate`   |   Windows: `venv\Scripts\activate`
3. `pip install -r requirements.txt`
4. Copy `.env.example` to `.env` and fill it in. NEVER commit `.env`.
   - `LLM_API_KEY`, `LLM_MODEL` for the profile builder (Gemini free key by default)
   - `SUPABASE_URL`, `SUPABASE_SERVICE_KEY` only if you want request logs (see Supabase below)

## Run order
1. `python train_model.py --data data/labeled_descriptions.csv`   -> trains and saves `models/risk_model.joblib`
2. `uvicorn main:app --reload`   -> API. Open http://127.0.0.1:8000 (one-box page) or http://127.0.0.1:8000/docs
3. `pytest -q`   -> 16 tests (needs no LLM key)
4. `python run_assess.py "We let users send money to family in Vietnam."`   -> full output in the terminal

Optional: `pip install sentence-transformers` then add `--compare` to train_model.py.

## Endpoints
| Method | Path | What it does |
|---|---|---|
| GET | `/health` | Always 200. Also says if the classifier is loaded. |
| POST | `/classify` | `risk_level`, `probability`, `top_reasons`, `similar_examples`, `warnings` |
| POST | `/assess` | Same risk result + LLM `profile` (if the LLM fails, `profile_error` explains why) |
| POST | `/risk`, `/profile` | Risk only (old field names) / LLM profile only |

Errors are always JSON: `{"error": {"code": "...", "message": "...", "request_id": "..."}}`.
Limits: 10-2000 characters per description, 20 requests per minute per IP per endpoint
(change with `MAX_DESCRIPTION_CHARS`, `RATE_LIMIT_PER_MINUTE`).

## Supabase (once)
1. Create a project at supabase.com.
2. SQL Editor -> paste `supabase/schema.sql` -> Run (creates `request_logs`, RLS on).
3. Project Settings -> API: copy the Project URL and the `service_role` key into `.env`
   and set `LOG_TO_SUPABASE=true`. The service key is a secret: backend only, never in the frontend.

## Deploy (Render / Railway / Fly)
- Start command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
- Add every variable from `.env.example` in the host's Environment page.
  Set `TRUST_PROXY=true` and `ALLOWED_ORIGINS=https://your-frontend-url`.
- The trained `models/risk_model.joblib` must exist on the server (commit it, or run train_model.py in the build step).
