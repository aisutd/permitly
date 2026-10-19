"""
main.py
=======
STEP 6: The web API (FastAPI). This is what the backend / website calls.

Run it:        uvicorn main:app --reload
Test it here:  http://127.0.0.1:8000/docs   (FastAPI makes a free test page)

Endpoints:
  GET  /health   -> is the server alive?
  POST /profile  -> LLM profile only             (works BEFORE training)
  POST /risk     -> risk + 3 similar examples    (needs the trained model)
  POST /assess   -> everything together

Input is ONE text field: {"description": "..."}  (plain text, 10-5000 characters).
Strange input (gibberish, other languages) returns general_risk "Unknown" or a
non-empty "warnings" list with needs_review = true.
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, field_validator

from assess import assess_business
from profile_builder import build_profile
from risk_model import predict_risk

app = FastAPI(title="Permitly Risk API")


# The shape of what the user sends us.
class DescriptionIn(BaseModel):
    description: str = Field(min_length=10, max_length=5000)

    @field_validator("description")
    @classmethod
    def must_contain_words(cls, value: str) -> str:
        value = value.strip()
        if len(value) < 10:
            raise ValueError("Description is too short (at least 10 characters).")
        if sum(ch.isalpha() for ch in value) < 5:
            raise ValueError("Description must contain real words, not only numbers or symbols.")
        return value


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/profile")
def profile(body: DescriptionIn):
    try:
        return build_profile(body.description).model_dump()
    except RuntimeError as error:   # e.g. missing API key
        raise HTTPException(status_code=500, detail=str(error))
    except ValueError as error:     # LLM answer was invalid twice
        raise HTTPException(status_code=502, detail=str(error))


@app.post("/risk")
def risk(body: DescriptionIn):
    try:
        return predict_risk(body.description)
    except FileNotFoundError as error:  # model not trained yet
        raise HTTPException(status_code=503, detail=str(error))


@app.post("/assess")
def assess(body: DescriptionIn):
    try:
        return assess_business(body.description)
    except FileNotFoundError as error:
        raise HTTPException(status_code=503, detail=str(error))
    except RuntimeError as error:
        raise HTTPException(status_code=500, detail=str(error))
    except ValueError as error:
        raise HTTPException(status_code=502, detail=str(error))