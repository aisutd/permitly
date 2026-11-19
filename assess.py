"""
assess.py
=========
STEP 5 (Task 8): ONE function that does everything.
The backend team can call assess_business(...) directly, or use the web API in main.py.

If the LLM part fails (missing key, rate limit, bad answer), we still return the
risk part and explain the problem in "profile_error". One broken half should not
throw away the other half.
"""

from profile_builder import build_profile
from risk_model import predict_risk


def assess_business(description: str) -> dict:
    risk = predict_risk(description)          # needs the trained model

    try:
        profile = build_profile(description).model_dump()   # needs the LLM key
        profile_error = None
    except (RuntimeError, ValueError) as error:
        profile = None
        profile_error = str(error)

    result = {
        "general_risk": risk["general_risk"],
        "probabilities": risk["probabilities"],
        "similar_examples": risk["similar_examples"],
        "needs_review": risk["needs_review"],
        "warnings": risk["warnings"],
        "profile": profile,
    }
    if profile_error:
        result["profile_error"] = profile_error
    return result