"""
risk_model.py
=============
Uses the TRAINED model to:
  (a) predict general_risk  -> High / Medium / Low   (Logistic Regression)
  (b) find the 3 most similar labeled examples        (kNN = k-nearest neighbors)

Two ways to turn text into numbers are supported:
  "tfidf"      = word counts (light and free, runs on a free server)   <- default
  "embeddings" = sentence meaning (heavier, needs: pip install sentence-transformers)

This file does NOT train anything. Training happens in train_model.py.
"""

from pathlib import Path

import joblib
import numpy as np

# Where the trained model is saved (train_model.py creates this file).
MODEL_PATH = Path("models/risk_model.joblib")

# Only used when model_type = "embeddings".
EMBED_MODEL_NAME = "all-MiniLM-L6-v2"

_embedder = None   # loaded only if we need embeddings (it is slow to load)
_bundle = None     # the trained model, loaded the first time we need it

# ---- Safety checks for strange input (rough thresholds, tune when you have more data) ----
# The model can only judge words it saw during training. If a description has none
# (gibberish, another language, numbers only), the honest answer is "Unknown",
# NOT a made-up High/Medium/Low.
FEW_KNOWN_TERMS = 10      # fewer known words/phrases than this -> result is unreliable
LOW_SIMILARITY = 0.10     # best similar example below this -> nothing close in the data
LONG_TEXT_CHARS = 1000    # training examples are ~100-500 characters long


def embed(texts: list[str]) -> np.ndarray:
    """Turn sentences into numbers by MEANING (embeddings). Optional, heavier."""
    global _embedder
    if _embedder is None:
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError:
            raise RuntimeError(
                "Embeddings need an extra library. Run:  pip install sentence-transformers"
            )
        _embedder = SentenceTransformer(EMBED_MODEL_NAME)
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


def _to_numbers(bundle: dict, texts: list[str]):
    """Convert text to numbers the SAME way the model was trained."""
    if bundle.get("model_type", "embeddings") == "tfidf":
        return bundle["vectorizer"].transform(texts)
    return embed(texts)


def predict_risk(description: str) -> dict:
    """Return general_risk, probabilities, the 3 most similar labeled examples,
    and warnings when the input looks strange (needs_review = True)."""
    bundle = load_model()
    vector = _to_numbers(bundle, [description])  # 1 row of numbers

    # How many words/phrases of this description does the model actually know?
    # (Only available for the TF-IDF model.)
    known_terms = int(vector.getnnz()) if hasattr(vector, "getnnz") else None

    # Case 1: the model knows NOTHING in this text -> do not guess.
    if known_terms == 0:
        return {
            "general_risk": "Unknown",
            "probabilities": {},
            "similar_examples": [],
            "needs_review": True,
            "warnings": [
                "no_known_words: none of the words match the training data. "
                "Is the text English and about a business that handles money?"
            ],
        }

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
                "similarity": round(float(1 - distance), 3),  # 1.0 = identical
            }
        )

    # Case 2: we can answer, but the answer may be unreliable. Say why.
    warnings = []
    if known_terms is not None and known_terms < FEW_KNOWN_TERMS:
        warnings.append(
            f"few_known_words: only {known_terms} words/phrases match the training data, "
            "so this result is unreliable."
        )
    if similar_examples and similar_examples[0]["similarity"] < LOW_SIMILARITY:
        warnings.append("no_close_examples: no labeled example is similar to this description.")
    if len(description) > LONG_TEXT_CHARS:
        warnings.append(
            f"long_text: {len(description)} characters, much longer than the training examples "
            "(about 100-500). Try a short summary of what the business does with money."
        )

    return {
        "general_risk": str(label),
        "probabilities": probabilities,
        "similar_examples": similar_examples,
        "needs_review": bool(warnings),
        "warnings": warnings,
    }