"""
assess.py
=========
STEP 5 (Task 8): ONE function that does everything.
The backend team can call assess_business(...) directly, or use the web API in main.py.
"""

from profile_builder import build_profile
from risk_model import predict_risk


def assess_business(description: str) -> dict:
    risk = predict_risk(description)          # needs the trained model
    profile = build_profile(description)      # needs the LLM key
    return {
        "general_risk": risk["general_risk"],
        "probabilities": risk["probabilities"],
        "similar_examples": risk["similar_examples"],
        "profile": profile.model_dump(),
    }
