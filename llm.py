"""
llm.py
======
Task B7: ONE place that talks to the LLM. The profile builder uses it now,
and the future /ask (RAG) endpoint should use the same function.

Rules:
  - Every call has a timeout (LLM_TIMEOUT_SECONDS).
  - If the call fails for a temporary reason (timeout, no connection, rate limit,
    server error 5xx) we wait a little and try ONE more time.
  - If it still fails we raise RuntimeError with a short, friendly message
    (no stack trace, no secret) that the API can show to the user.
"""

import logging
import time

from openai import APIConnectionError, APIStatusError, APITimeoutError, OpenAI, RateLimitError

import config

log = logging.getLogger("permitly.llm")

_client: OpenAI | None = None


def _get_client() -> OpenAI:
    global _client
    if not config.LLM_API_KEY:
        raise RuntimeError("LLM_API_KEY is missing. Copy .env.example to .env and paste your key.")
    if not config.LLM_MODEL:
        raise RuntimeError("LLM_MODEL is missing in the .env file.")
    if _client is None:
        # max_retries=0: WE control the retry (exactly one), the library must not add more.
        _client = OpenAI(
            api_key=config.LLM_API_KEY,
            base_url=config.LLM_BASE_URL,
            timeout=config.LLM_TIMEOUT_SECONDS,
            max_retries=0,
        )
    return _client


def chat(messages: list[dict]) -> str:
    """Send messages to the LLM and return the answer text."""
    client = _get_client()
    last_problem = ""

    for attempt in (1, 2):  # first try + ONE retry
        try:
            response = client.chat.completions.create(
                model=config.LLM_MODEL, temperature=0, messages=messages
            )
            return response.choices[0].message.content or ""
        except APITimeoutError:
            last_problem = "The AI service took too long to answer. Please try again."
        except APIConnectionError:
            last_problem = "Could not reach the AI service. Please try again."
        except RateLimitError:
            last_problem = "The AI service is busy (free-plan rate limit). Wait a minute and try again."
        except APIStatusError as error:
            if error.status_code < 500:  # 400/401/403/404 = our mistake, retrying will not help
                log.error("LLM rejected the request: status %s", error.status_code)
                raise RuntimeError("The AI service rejected the request. Check LLM_API_KEY and LLM_MODEL.")
            last_problem = "The AI service had an internal error. Please try again."

        log.warning("LLM call failed (attempt %s/2): %s", attempt, last_problem)
        if attempt == 1:
            time.sleep(config.LLM_RETRY_WAIT_SECONDS)

    raise RuntimeError(last_problem)
