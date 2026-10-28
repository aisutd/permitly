"""
train_model.py
==============
Trains the risk model from the teammate's labeled JSON file and saves it.

  Task 3: TF-IDF (word counts) + Logistic Regression   <- our main model
  Task 4: Embeddings (sentence meaning) + Logistic Regression   <- optional comparison
  Task 5: Scores = accuracy + High-risk recall + confusion matrix
  Task 6: kNN so we can return the 3 most similar examples

Run it:
  python train_model.py --data data/labeled_descriptions.csv
Optional (also compare with embeddings, needs: pip install sentence-transformers):
  python train_model.py --data data/labeled_descriptions.csv --compare

The data file can be .csv or .json. It needs a text column (description) and a
risk column with High / Medium / Low. Any other column (why, source_file, ...)
is IGNORED, so it can never leak into the model.
"""

import argparse
import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, make_scorer, recall_score
from sklearn.model_selection import StratifiedKFold, cross_val_predict, cross_val_score, train_test_split
from sklearn.neighbors import NearestNeighbors
from sklearn.pipeline import make_pipeline

import risk_model  # we reuse MODEL_PATH (and embed() if you use embeddings)

LABELS = ["High", "Medium", "Low"]


# ---------------------------------------------------------------------------
# STEP 1: Load the labeled file (.csv or .json) and check it is clean.
# We pick ONE text column and ONE label column and drop everything else
# (like "why" and "source_file"), so extra columns cannot affect the model.
# ---------------------------------------------------------------------------
TEXT_COLUMNS = ["description", "text", "business_description"]
LABEL_COLUMNS = ["risk", "general_risk", "label"]  # first one that holds High/Medium/Low wins


def pick_label_column(df: pd.DataFrame) -> str:
    for name in LABEL_COLUMNS:
        if name in df.columns:
            values = df[name].dropna().astype(str).str.strip().str.capitalize()
            if len(values) > 0 and values.isin(LABELS).all():
                return name
    raise SystemExit(f"No column with only High/Medium/Low found. Columns: {list(df.columns)}")


def load_data(path: str) -> pd.DataFrame:
    if path.lower().endswith(".csv"):
        df = pd.read_csv(path)
    else:
        with open(path, encoding="utf-8") as f:
            raw = json.load(f)
        if isinstance(raw, dict):  # {"data": [ ... ]}
            lists = [value for value in raw.values() if isinstance(value, list)]
            if not lists:
                raise SystemExit("The JSON must be a list of {description, risk} items.")
            raw = lists[0]
        df = pd.DataFrame(raw)

    text_col = next((c for c in TEXT_COLUMNS if c in df.columns), None)
    if text_col is None:
        raise SystemExit(f"No text column found. Columns: {list(df.columns)}")
    label_col = pick_label_column(df)

    ignored = [c for c in df.columns if c not in (text_col, label_col)]
    print(f"Using '{text_col}' as the text and '{label_col}' as the label.")
    print(f"Ignoring columns: {ignored}\n")

    df = df[[text_col, label_col]].rename(columns={text_col: "description", label_col: "label"})
    df = df.dropna().copy()
    df["description"] = df["description"].astype(str).str.strip()
    df["label"] = df["label"].astype(str).str.strip().str.capitalize()  # "high" -> "High"
    df = df[df["description"] != ""].drop_duplicates(subset="description")

    counts = df["label"].value_counts()
    for label in LABELS:
        if counts.get(label, 0) < 3:
            raise SystemExit(f"Need at least 3 examples of '{label}'. Found {counts.get(label, 0)}.")

    print(f"Loaded {len(df)} rows. Rows per label:\n{counts.to_string()}\n")
    return df.reset_index(drop=True)


# ---------------------------------------------------------------------------
# STEP 2: A helper that prints the scores for one model.
# High-risk RECALL = of all truly High businesses, how many did we catch?
# (Missing a High-risk business is the worst mistake.)
# ---------------------------------------------------------------------------
def evaluate(name: str, y_true, y_pred) -> dict:
    accuracy = accuracy_score(y_true, y_pred)
    report = classification_report(y_true, y_pred, labels=LABELS, zero_division=0, output_dict=True)
    high_recall = report["High"]["recall"]

    print(f"----- {name} -----")
    print(f"Accuracy: {accuracy:.2f}   |   High-risk recall: {high_recall:.2f}")
    print(classification_report(y_true, y_pred, labels=LABELS, zero_division=0))
    print("Confusion matrix (rows = TRUE label, columns = PREDICTED label)")
    print(f"Order: {LABELS}")
    print(confusion_matrix(y_true, y_pred, labels=LABELS))
    print()
    return {"model": name, "accuracy": accuracy, "high_recall": high_recall}


def fold_scores(name: str, estimator, X, y, cv) -> None:
    """cross_val_score: score each fold separately, then show the average and the spread.
    The spread (+/-) tells you how much the score depends on which rows land in which fold."""
    def high_recall_fn(y_true, y_pred):
        return float(recall_score(y_true, y_pred, labels=["High"], average=None, zero_division=0)[0])

    high_recall = make_scorer(high_recall_fn)
    acc = cross_val_score(estimator, X, y, cv=cv, scoring="accuracy")
    rec = cross_val_score(estimator, X, y, cv=cv, scoring=high_recall)
    print(f"cross_val_score  {name}")
    print(f"  accuracy    : {acc.mean():.2f} (+/- {acc.std():.2f})   per fold: {[round(float(v), 2) for v in acc]}")
    print(f"  High recall : {rec.mean():.2f} (+/- {rec.std():.2f})   per fold: {[round(float(v), 2) for v in rec]}\n")


# Missing a High-risk business is the worst mistake, so errors on "High" cost double,
# "Medium" 1.5x, "Low" 1x. Settings were chosen by repeated cross-validation on the
# v3 data (see the explanation that came with this file).
CLASS_WEIGHT = {"High": 2.0, "Medium": 1.5, "Low": 1.0}


def new_logistic_regression() -> LogisticRegression:
    # C=10 = trust the training data more (less smoothing than the default C=1).
    return LogisticRegression(max_iter=1000, C=10, class_weight=CLASS_WEIGHT)


def new_vectorizer() -> TfidfVectorizer:
    # sublinear_tf=True: a word repeated 5 times does not count 5x more than a word seen once.
    return TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True)


def new_tfidf_pipeline():
    # TF-IDF = count words (and 2-word pairs), then Logistic Regression decides.
    return make_pipeline(new_vectorizer(), new_logistic_regression())


def main(data_path: str, model_type: str, compare: bool) -> None:
    df = load_data(data_path)
    texts = df["description"].tolist()
    labels = df["label"].to_numpy()

    # -----------------------------------------------------------------------
    # STEP 3: Split 80% train / 20% test.
    # stratify=labels keeps the High/Medium/Low mix equal in both parts.
    # -----------------------------------------------------------------------
    idx = np.arange(len(df))
    train_idx, test_idx = train_test_split(idx, test_size=0.2, stratify=labels, random_state=42)
    train_texts = [texts[i] for i in train_idx]
    test_texts = [texts[i] for i in test_idx]

    # Cross-validation = repeat train/test on different slices, so the score
    # does not depend on one lucky split.
    n_splits = min(5, int(pd.Series(labels).value_counts().min()))
    cv = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=42) if n_splits >= 2 else None

    # -----------------------------------------------------------------------
    # STEP 4 (Task 3): TF-IDF + Logistic Regression.
    # -----------------------------------------------------------------------
    results, cv_results = [], []
    tfidf_model = new_tfidf_pipeline().fit(train_texts, labels[train_idx])
    results.append(evaluate("TF-IDF + LogReg", labels[test_idx], tfidf_model.predict(test_texts)))
    if cv is not None:
        print(f"Cross-validation with {n_splits} folds:\n")
        cv_preds = cross_val_predict(new_tfidf_pipeline(), texts, labels, cv=cv)
        cv_results.append(evaluate("CV TF-IDF + LogReg", labels, cv_preds))
        # Save every row with what the model guessed WHEN IT HAD NOT SEEN that row.
        Path("reports").mkdir(exist_ok=True)
        out = pd.DataFrame({"description": texts, "true_risk": labels, "predicted_risk": cv_preds})
        out["correct"] = out["true_risk"] == out["predicted_risk"]
        out.to_csv("reports/cv_predictions.csv", index=False)
        print("Saved row-by-row predictions to reports/cv_predictions.csv\n")
        fold_scores("TF-IDF + LogReg", new_tfidf_pipeline(), texts, labels, cv)

    # -----------------------------------------------------------------------
    # STEP 5 (Task 4, optional): Embeddings + Logistic Regression.
    # Only runs with --compare (or --model embeddings).
    # -----------------------------------------------------------------------
    X_emb = None
    if compare or model_type == "embeddings":
        print("Creating embeddings (the first run downloads a small model, please wait)...")
        X_emb = risk_model.embed(texts)
        emb_clf = new_logistic_regression().fit(X_emb[train_idx], labels[train_idx])
        results.append(evaluate("Embeddings + LogReg", labels[test_idx], emb_clf.predict(X_emb[test_idx])))
        if cv is not None:
            cv_results.append(evaluate(
                "CV Embeddings + LogReg", labels,
                cross_val_predict(new_logistic_regression(), X_emb, labels, cv=cv)))
            fold_scores("Embeddings + LogReg", new_logistic_regression(), X_emb, labels, cv)

    # -----------------------------------------------------------------------
    # STEP 6 (Task 5): Print the comparison table.
    # -----------------------------------------------------------------------
    print("===== SCORE TABLE =====")
    print(pd.DataFrame(results + cv_results).to_string(index=False, float_format=lambda v: f"{v:.2f}"))
    final_rows = cv_results if cv_results else results
    if len(final_rows) > 1:
        best = max(final_rows, key=lambda r: (r["high_recall"], r["accuracy"]))
        print(f"\nBest at catching High-risk businesses: {best['model']} "
              f"(High recall {best['high_recall']:.2f}, accuracy {best['accuracy']:.2f})")
    print()

    # -----------------------------------------------------------------------
    # STEP 7 (Task 6): Train the FINAL model on ALL the data and save it.
    #   clf = Logistic Regression -> predicts High / Medium / Low
    #   nn  = kNN                 -> finds the 3 most similar labeled examples
    # -----------------------------------------------------------------------
    extra = {}
    if model_type == "tfidf":
        vectorizer = new_vectorizer()
        X_final = vectorizer.fit_transform(texts)
        extra["vectorizer"] = vectorizer  # saved so the API converts text the same way
    else:
        X_final = X_emb

    final_clf = new_logistic_regression().fit(X_final, labels)
    nn = NearestNeighbors(n_neighbors=min(3, len(df)), metric="cosine", algorithm="brute").fit(X_final)

    bundle = {"model_type": model_type, "clf": final_clf, "nn": nn,
              "texts": texts, "labels": labels.tolist(), **extra}
    risk_model.MODEL_PATH.parent.mkdir(exist_ok=True)
    joblib.dump(bundle, risk_model.MODEL_PATH)
    print(f"Saved '{model_type}' model to {risk_model.MODEL_PATH}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", default="data/labeled_descriptions.csv", help="Path to labeled .csv or .json")
    parser.add_argument("--model", choices=["tfidf", "embeddings"], default="tfidf",
                        help="Which model to SAVE for the API (default: tfidf)")
    parser.add_argument("--compare", action="store_true",
                        help="Also train + score the embeddings model (needs sentence-transformers)")
    args = parser.parse_args()
    main(args.data, args.model, args.compare)
