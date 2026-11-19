"""
db.py
=====
Supabase (Postgres) connection. The backend uses the SERVICE key, so keep it secret
(env variable only). If Supabase is not configured, everything here quietly does nothing,
so the API still runs on your laptop without a database.

Now:   request_logs (B8)
Next:  states / state_requirements (B4), document chunks with pgvector (B5)
"""

import logging
import threading

import config

log = logging.getLogger("permitly.db")

_client = None


def is_configured() -> bool:
    return bool(config.SUPABASE_URL and config.SUPABASE_SERVICE_KEY)


def get_client():
    """Create the Supabase client once and reuse it."""
    global _client
    if not is_configured():
        raise RuntimeError("SUPABASE_URL / SUPABASE_SERVICE_KEY are missing in the .env file.")
    if _client is None:
        from supabase import create_client  # imported here so the API starts even without the library

        _client = create_client(config.SUPABASE_URL, config.SUPABASE_SERVICE_KEY)
    return _client


def log_request(row: dict) -> None:
    """Save one request log row WITHOUT slowing the answer (runs in a background thread).
    A logging problem must never break a user request, so every error is swallowed."""
    if not (config.LOG_TO_SUPABASE and is_configured()):
        return

    def _insert() -> None:
        try:
            get_client().table("request_logs").insert(row).execute()
        except Exception as error:  # noqa: BLE001
            log.warning("Could not save request log to Supabase: %s", type(error).__name__)

    threading.Thread(target=_insert, daemon=True).start()
