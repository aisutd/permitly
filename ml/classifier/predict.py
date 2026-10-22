import joblib, pandas as pd
from sentence_transformers import SentenceTransformer
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.neighbors import NearestNeighbors

MODEL_PATH = "classifier/model.joblib"
_encoder = None

def _get_encoder():
    global _encoder
    if _encoder is None:
        _encoder = SentenceTransformer("all-MiniLM-L6-v2")
    return _encoder

def train():
    df = pd.read_csv("data/labeled_descriptions.csv")
    risk_model = make_pipeline(TfidfVectorizer(), LogisticRegression(max_iter=1000))
    risk_model.fit(df["description"], df["risk"])
    vectors = _get_encoder().encode(df["description"].tolist())
    nn = NearestNeighbors(n_neighbors=3, metric="cosine").fit(vectors)
    joblib.dump({"risk_model": risk_model, "nn": nn,
                 "examples": df[["description", "risk"]]}, MODEL_PATH)

def classify(description):
    bundle = joblib.load(MODEL_PATH)
    general_risk = bundle["risk_model"].predict([description])[0]
    vec = _get_encoder().encode([description])
    _, idx = bundle["nn"].kneighbors(vec)
    similar = bundle["examples"].iloc[idx[0]].to_dict("records")
    return {"general_risk": general_risk, "similar_examples": similar}

if __name__ == "__main__":
    train()
    print(classify("An app where gig workers send part of their pay to family in Mexico."))