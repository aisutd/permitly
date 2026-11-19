"""
Tests for B1 (health/CORS), B2 (startup load), B3 (/classify), B7 (clean errors), B8 (rate limit).
Run:  pytest -q
(No LLM key is needed: /classify does not call the LLM.)
"""

import pytest

import config

# Three NEW descriptions (not in the training file): one per risk level.
HIGH = "Our app lets people load money into a wallet we hold and send it to friends and family, including relatives in Mexico."
MEDIUM = "Online tutoring marketplace. Parents pay us up front, and we pay each tutor after the lesson is finished."
LOW = "We sell accounting software to small businesses for a monthly fee. We never touch our customers' money."


@pytest.mark.parametrize("text, expected", [(HIGH, "High"), (MEDIUM, "Medium"), (LOW, "Low")])
def test_classify_three_risk_levels(client, text, expected):
    response = client.post("/classify", json={"description": text})
    assert response.status_code == 200
    data = response.json()
    assert data["risk_level"] == expected
    assert 0 < data["probability"] <= 1
    assert data["probability"] == max(data["probabilities"].values())
    assert 1 <= len(data["top_reasons"]) <= 5          # top reasons are returned
    assert all(r["term"] and r["weight"] > 0 for r in data["top_reasons"])
    assert len(data["similar_examples"]) == 3
    assert "X-Request-ID" in response.headers


@pytest.mark.parametrize("text", ["", "   ", "short", "12345 67890 !!!!"])
def test_classify_rejects_bad_input(client, text):
    response = client.post("/classify", json={"description": text})
    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "invalid_input" and error["message"] and error["request_id"]


def test_classify_rejects_too_long_input(client):
    response = client.post("/classify", json={"description": "send money abroad " * 300})
    assert response.status_code == 422
    assert "too long" in response.json()["error"]["message"]


def test_missing_field_is_clean_json(client):
    response = client.post("/classify", json={})
    assert response.status_code == 422 and "error" in response.json()


def test_unknown_route_is_clean_json(client):
    response = client.get("/nope")
    assert response.status_code == 404 and response.json()["error"]["code"] == "http_error"


def test_health_and_model_loaded_at_startup(client):
    data = client.get("/health").json()
    assert data == {"status": "ok", "classifier_loaded": True}


def test_cors_allows_frontend_origin_only(client):
    origin = config.ALLOWED_ORIGINS[0]
    ok = client.get("/health", headers={"Origin": origin})
    assert ok.headers.get("access-control-allow-origin") == origin
    bad = client.get("/health", headers={"Origin": "https://evil.example"})
    assert "access-control-allow-origin" not in bad.headers


def test_rate_limit_returns_429(client, monkeypatch):
    monkeypatch.setattr(config, "RATE_LIMIT_PER_MINUTE", 3)
    codes = [client.post("/classify", json={"description": LOW}).status_code for _ in range(5)]
    assert codes == [200, 200, 200, 429, 429]
    blocked = client.post("/classify", json={"description": LOW})
    assert blocked.headers["Retry-After"].isdigit()
    assert blocked.json()["error"]["code"] == "rate_limited"


def test_llm_timeout_retries_once_then_clean_error(monkeypatch):
    """B7: a timeout is retried exactly once, then we get a friendly RuntimeError."""
    import httpx
    from openai import APITimeoutError

    import llm

    calls = []

    class FakeCompletions:
        def create(self, **kwargs):
            calls.append(1)
            raise APITimeoutError(request=httpx.Request("POST", "https://example.com"))

    class FakeClient:
        chat = type("Chat", (), {"completions": FakeCompletions()})()

    monkeypatch.setattr(llm, "_client", FakeClient())
    monkeypatch.setattr(config, "LLM_API_KEY", "x")
    monkeypatch.setattr(config, "LLM_MODEL", "m")
    monkeypatch.setattr(config, "LLM_RETRY_WAIT_SECONDS", 0)
    with pytest.raises(RuntimeError, match="too long"):
        llm.chat([{"role": "user", "content": "hi"}])
    assert len(calls) == 2  # first try + one retry


def test_assess_still_returns_risk_when_llm_is_down(client, monkeypatch):
    monkeypatch.setattr(config, "LLM_API_KEY", "")
    response = client.post("/assess", json={"description": HIGH})
    assert response.status_code == 200
    data = response.json()
    assert data["general_risk"] == "High" and data["profile"] is None and data["profile_error"]


def test_unhandled_error_never_leaks_stack_trace(client, monkeypatch):
    import main

    def boom(_):
        raise ValueError("secret internal detail")

    monkeypatch.setattr(main, "predict_risk", boom)
    response = client.post("/classify", json={"description": HIGH})
    assert response.status_code == 500
    assert "secret internal detail" not in response.text and "Traceback" not in response.text
    assert response.json()["error"]["code"] == "internal_error"
