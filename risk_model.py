"""
risk_model.py
=============
Uses the TRAINED model to:
  (a) predict general_risk  -> High / Medium / Low   (embeddings + Logistic Regression)
  (b) find the 3 most similar labeled examples        (kNN = k-nearest neighbors)

This file does NOT train anything. Training happens in train_model.py.
"""

from pathlib import Path

import joblib
import numpy as np

# Where the trained model is saved (train_model.py creates this file).
MODEL_PATH = Path("models/risk_model.joblib")

# The tool that turns a sentence into numbers ("embedding").
# Sentences with similar meaning get similar numbers.
EMBED_MODEL_NAME = "all-MiniLM-L6-v2"

_embedder = None   # loaded the first time we need it (it is slow to load)
_bundle = None     # the trained model, loaded the first time we need it


def embed(texts: list[str]) -> np.ndarray:
    """Turn a list of sentences into a table of numbers (one row per sentence)."""
    global _embedder
    if _embedder is None:
        from sentence_transformers import SentenceTransformer  # imported here because it is heavy
        _embedder = SentenceTransformer(EMBED_MODEL_NAME)
    # normalize_embeddings=True makes every row the same length, which helps similarity search.
    return _embedder.encode(texts, normalize_embeddings=True)


def load_model() -> dict:
    """Load the saved model from disk (only once)."""
    global _bundle
    if _bundle is None:
        if not MODEL_PATH.exists():
            raise FileNotFoundError(
                "No trained model found. Run:  python train_model.py  first."
            )
        _bundle = joblib.load(MODEL_PATH)
    return _bundle


def predict_risk(description: str) -> dict:
    """Return general_risk, probabilities, and the 3 most similar labeled examples."""
    bundle = load_model()
    vector = embed([description])  # 1 row of numbers

    # (a) Logistic Regression: pick the label with the highest probability.
    clf = bundle["clf"]
    label = clf.predict(vector)[0]
    probabilities = {
        cls: round(float(p), 3) for cls, p in zip(clf.classes_, clf.predict_proba(vector)[0])
    }

    # (b) kNN: find the closest labeled descriptions.
    distances, indices = bundle["nn"].kneighbors(vector)
    similar_examples = []
    for distance, idx in zip(distances[0], indices[0]):
        similar_examples.append(
            {
                "description": bundle["texts"][idx],
                "label": bundle["labels"][idx],
                "similarity": round(float(1 - distance), 3),  # 1.0 = identical meaning
            }
        )

    return {
        "general_risk": str(label),
        "probabilities": probabilities,
        "similar_examples": similar_examples,
    }
