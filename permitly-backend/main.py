"""
main.py
=======
The web API (FastAPI). This is what the frontend calls.

Run it:        uvicorn main:app --reload
Dev page:      http://127.0.0.1:8000        (ONE box: type a description, get the answer)
API docs:      http://127.0.0.1:8000/docs   (FastAPI makes this test page for free)

Endpoints:
  GET  /health    -> is the server alive? (always 200)                       [B1]
  POST /classify  -> risk level + probability + top reasons (+ 3 examples)   [B3]  <- the official one
  POST /assess    -> /classify result + LLM profile (used by the dev page)
  POST /risk      -> same data as /classify, older field names
  POST /profile   -> LLM profile only (works BEFORE training)

Every error is JSON: {"error": {"code", "message", "request_id"}}  (never a stack trace)  [B7]
"""

import logging
import time
import uuid
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, Field, field_validator
from starlette.exceptions import HTTPException as StarletteHTTPException

import config
import db
import risk_model
from assess import assess_business
from errors import ApiError
from page import PAGE
from profile_builder import build_profile
from ratelimit import rate_limit
from risk_model import predict_risk

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("permitly.api")


# ---------------------------------------------------------------------------
# B2: load the models ONCE when the server starts (not on every request).
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    started = time.perf_counter()
    try:
        bundle = risk_model.load_model()
        log.info("Classifier (%s) loaded in %.2f s", bundle.get("model_type", "?"), time.perf_counter() - started)

        # Embedding model: only loaded when it is needed (embeddings classifier, or the
        # future RAG search). It is the slow one, so we pay the cost here, not in a request.
        if bundle.get("model_type") == "embeddings" or config.PRELOAD_EMBEDDINGS:
            t = time.perf_counter()
            risk_model.embed(["warm up"])
            log.info("Embedding model loaded in %.2f s", time.perf_counter() - t)
    except FileNotFoundError:
        log.warning("No trained model yet. Run: python train_model.py  (/classify will return 503 until then)")
    except Exception as error:  # noqa: BLE001 - a bad model file must not stop the server from starting
        log.error("Could not load the classifier: %s", type(error).__name__)
    log.info("Startup finished in %.2f s", time.perf_counter() - started)
    yield


app = FastAPI(title="Permitly Risk API", lifespan=lifespan)

# B1: CORS. Only the frontend addresses listed in ALLOWED_ORIGINS may call the API from a browser.
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.ALLOWED_ORIGINS,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
    expose_headers=["X-Request-ID"],
)


# ---------------------------------------------------------------------------
# B8: request id + latency log. We log the path and timing, NEVER the user's text.
# ---------------------------------------------------------------------------
@app.middleware("http")
async def log_requests(request: Request, call_next):
    request_id = uuid.uuid4().hex[:8]
    request.state.request_id = request_id
    started = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception:  # noqa: BLE001 - last safety net: clean JSON, details only in the server log
        log.exception("[%s] unhandled error on %s %s", request_id, request.method, request.url.path)
        response = _error_response(500, "internal_error", "Something went wrong on our side. Please try again.", request_id)

    latency_ms = int((time.perf_counter() - started) * 1000)
    response.headers["X-Request-ID"] = request_id
    log.info("[%s] %s %s -> %s in %d ms", request_id, request.method, request.url.path, response.status_code, latency_ms)
    if request.url.path != "/health":
        db.log_request({"request_id": request_id, "method": request.method, "path": request.url.path,
                        "status": response.status_code, "latency_ms": latency_ms})
    return response


# ---------------------------------------------------------------------------
# B7: clean JSON errors
# ---------------------------------------------------------------------------
def _error_response(status: int, code: str, message: str, request_id: str, headers: dict | None = None):
    return JSONResponse(
        status_code=status,
        content={"error": {"code": code, "message": message, "request_id": request_id}},
        headers=headers,
    )


def _rid(request: Request) -> str:
    return getattr(request.state, "request_id", "-")


@app.exception_handler(ApiError)
async def handle_api_error(request: Request, error: ApiError):
    return _error_response(error.status, error.code, error.message, _rid(request), error.headers)


@app.exception_handler(StarletteHTTPException)
async def handle_http_error(request: Request, error: StarletteHTTPException):
    return _error_response(error.status_code, "http_error", str(error.detail), _rid(request))


@app.exception_handler(RequestValidationError)
async def handle_validation_error(request: Request, error: RequestValidationError):
    first = error.errors()[0] if error.errors() else {}
    message = str(first.get("msg", "Invalid input.")).replace("Value error, ", "")
    return _error_response(422, "invalid_input", message, _rid(request))


# ---------------------------------------------------------------------------
# B3: input and output shapes
# ---------------------------------------------------------------------------
class DescriptionIn(BaseModel):
    description: str = Field(description="What the business does with money (plain English).")

    @field_validator("description")
    @classmethod
    def check_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Description is empty. Please describe what the business does.")
        if len(value) < config.MIN_DESCRIPTION_CHARS:
            raise ValueError(f"Description is too short (at least {config.MIN_DESCRIPTION_CHARS} characters).")
        if len(value) > config.MAX_DESCRIPTION_CHARS:
            raise ValueError(
                f"Description is too long ({len(value)} characters, maximum {config.MAX_DESCRIPTION_CHARS}). "
                "Please shorten it to what the business does with money."
            )
        if sum(ch.isalpha() for ch in value) < 5:
            raise ValueError("Description must contain real words, not only numbers or symbols.")
        return value


class Reason(BaseModel):
    term: str     # a word or 2-word phrase from the description
    weight: float  # bigger = pushed the model harder toward the answer


class SimilarExample(BaseModel):
    description: str
    label: str
    similarity: float


class ClassifyOut(BaseModel):
    risk_level: str                        # "High" | "Medium" | "Low" | "Unknown"
    probability: float | None              # how sure the model is about risk_level (0 to 1)
    probabilities: dict[str, float]        # all three, so the UI can draw bars
    top_reasons: list[Reason]              # the words that decided it
    similar_examples: list[SimilarExample]
    needs_review: bool
    warnings: list[str]


def _need_model():
    try:
        risk_model.load_model()
    except FileNotFoundError:
        raise ApiError(503, "model_not_trained", "The risk model is not trained yet. Run: python train_model.py")


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def home():
    return PAGE


@app.get("/health")
def health():
    return {"status": "ok", "classifier_loaded": risk_model.is_loaded()}


@app.post("/classify", response_model=ClassifyOut, dependencies=[Depends(rate_limit)])
def classify(body: DescriptionIn):
    _need_model()
    result = predict_risk(body.description)
    probabilities = result["probabilities"]
    return ClassifyOut(
        risk_level=result["general_risk"],
        probability=probabilities.get(result["general_risk"]),
        probabilities=probabilities,
        top_reasons=result["top_reasons"],
        similar_examples=result["similar_examples"],
        needs_review=result["needs_review"],
        warnings=result["warnings"],
    )


@app.post("/risk", dependencies=[Depends(rate_limit)])
def risk(body: DescriptionIn):
    _need_model()
    return predict_risk(body.description)


@app.post("/profile", dependencies=[Depends(rate_limit)])
def profile(body: DescriptionIn):
    try:
        return build_profile(body.description).model_dump()
    except RuntimeError as error:  # missing key, timeout, rate limit (messages come from llm.py)
        raise ApiError(503, "llm_unavailable", str(error))
    except ValueError as error:    # the LLM answered, but not with a valid profile (twice)
        raise ApiError(502, "llm_bad_answer", str(error))


@app.post("/assess", dependencies=[Depends(rate_limit)])
def assess(body: DescriptionIn):
    _need_model()
    # If only the LLM half fails, assess_business still returns the risk half
    # and explains the problem in "profile_error".
    return assess_business(body.description)

@app.get("/states", dependencies=[Depends(rate_limit)])
def list_states():
    try:
        result = (
            db.get_client()
            .table("states")
            .select("code, name, license_type, statute, source_date")
            .order("name")
            .execute()
        )
        return {"states": result.data}
    except Exception:
        log.exception("Failed to retrieve states")
        raise ApiError(503, "database_unavailable", "Unable to retrieve states")


@app.get("/states/{code}", dependencies=[Depends(rate_limit)])
def get_state(code: str):
    code = code.upper()

    try:
        client = db.get_client()

        state_result = (
            client.table("states")
            .select("*")
            .eq("code", code)
            .execute()
        )

        if not state_result.data:
            raise ApiError(404, "state_not_found", "State not found")

        requirements_result = (
            client.table("state_requirements")
            .select("field_name, value, section, quote, note")
            .eq("state_code", code)
            .order("field_name")
            .execute()
        )

        return {
            "state": state_result.data[0],
            "requirements": requirements_result.data,
        }

    except ApiError:
        raise
    except Exception:
        log.exception("Failed to retrieve state requirements")
        raise ApiError(
            503,
            "database_unavailable",
            "Unable to retrieve state requirements",
        )