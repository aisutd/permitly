"""
config.py
=========
Task B1: ALL settings live here, and they all come from environment variables
(the .env file on your computer, or the "Environment" page on Render).
No secret is ever written in the code.
"""

import os

from dotenv import load_dotenv

load_dotenv()  # reads the .env file if it exists


def _int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, default))
    except ValueError:
        return default


def _float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, default))
    except ValueError:
        return default


# ----- LLM (any OpenAI-style company: Gemini, Groq, OpenRouter, OpenAI...) -----
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://generativelanguage.googleapis.com/v1beta/openai/")
LLM_MODEL = os.getenv("LLM_MODEL", "")
LLM_TIMEOUT_SECONDS = _float("LLM_TIMEOUT_SECONDS", 15)       # B7: give up on one call after this
LLM_RETRY_WAIT_SECONDS = _float("LLM_RETRY_WAIT_SECONDS", 5)  # B7: wait before the ONE retry

# ----- Web server -----
# Frontend addresses that may call this API (comma separated). "*" = everyone (dev only!).
ALLOWED_ORIGINS = [o.strip() for o in os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:5173").split(",") if o.strip()]
MAX_DESCRIPTION_CHARS = _int("MAX_DESCRIPTION_CHARS", 2000)   # B3: "too long" limit
MIN_DESCRIPTION_CHARS = _int("MIN_DESCRIPTION_CHARS", 10)

# ----- Rate limit (B8) -----
RATE_LIMIT_PER_MINUTE = _int("RATE_LIMIT_PER_MINUTE", 20)     # per IP, per endpoint
# Set TRUST_PROXY=true on Render/Railway/Fly so we read the real visitor IP from X-Forwarded-For.
TRUST_PROXY = os.getenv("TRUST_PROXY", "false").lower() in ("1", "true", "yes")

# ----- Supabase (Postgres database) -----
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY", "")  # SECRET: backend only, never in the frontend
LOG_TO_SUPABASE = os.getenv("LOG_TO_SUPABASE", "false").lower() in ("1", "true", "yes")

# ----- Models -----
PRELOAD_EMBEDDINGS = os.getenv("PRELOAD_EMBEDDINGS", "false").lower() in ("1", "true", "yes")
