"""
train_model.py
==============
Trains and compares the two models from our task list, then saves the best-setup model.

  Task 3: Baseline  = word counts (TF-IDF)  + Logistic Regression
  Task 4: Embeddings = sentence meaning     + Logistic Regression
  Task 5: Compare them (accuracy + High-risk recall + confusion matrix)
  Task 6: Fit kNN so we can return the 3 most similar examples

Run it:   python train_model.py
Later, with real data:   python train_model.py --data data/labeled_descriptions.csv
(The CSV needs the columns: description, label  -> label is High, Medium or Low)
"""

import argparse

import joblib
import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
from sklearn.model_selection import StratifiedKFold, cross_val_predict, train_test_split
from sklearn.neighbors import NearestNeighbors
from sklearn.pipeline import make_pipeline

import risk_model  # we reuse its embed() function and MODEL_PATH

LABELS = ["High", "Medium", "Low"]


# ---------------------------------------------------------------------------
# STEP 1: Load the labeled CSV and check it is clean.
# ---------------------------------------------------------------------------
def load_data(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)

    missing = {"description", "label"} - set(df.columns)
    if missing:
        raise SystemExit(f"CSV is missing columns: {missing}")

    df = df.dropna(subset=["description", "label"]).copy()
    df["description"] = df["description"].astype(str).str.strip()
    df["label"] = df["label"].astype(str).str.strip()
    df = df[df["description"] != ""]

    bad = df[~df["label"].isin(LABELS)]
    if len(bad) > 0:
        raise SystemExit(f"{len(bad)} rows have a label that is not High/Medium/Low. Fix the CSV.")

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


def new_logistic_regression() -> LogisticRegression:
    # class_weight="balanced" = pay extra attention to the smaller groups.
    return LogisticRegression(max_iter=1000, class_weight="balanced")


def main(data_path: str) -> None:
    df = load_data(data_path)
    texts = df["description"].tolist()
    labels = df["label"].to_numpy()

    # -----------------------------------------------------------------------
    # STEP 3: Turn every description into numbers (embeddings). Done once.
    # -----------------------------------------------------------------------
    print("Creating embeddings (the first run downloads a small model, please wait)...")
    X_all = risk_model.embed(texts)

    # -----------------------------------------------------------------------
    # STEP 4: Split 80% train / 20% test. Both models use the SAME split (fair).
    # stratify=labels keeps the High/Medium/Low mix equal in both parts.
    # -----------------------------------------------------------------------
    idx = np.arange(len(df))
    train_idx, test_idx = train_test_split(idx, test_size=0.2, stratify=labels, random_state=42)
    train_texts = [texts[i] for i in train_idx]
    test_texts = [texts[i] for i in test_idx]

    # -----------------------------------------------------------------------
    # STEP 5 (Task 3): Baseline = TF-IDF word counts + Logistic Regression.
    # -----------------------------------------------------------------------
    def new_baseline():
        return make_pipeline(TfidfVectorizer(ngram_range=(1, 2)), new_logistic_regression())

    baseline = new_baseline().fit(train_texts, labels[train_idx])
    results = [evaluate("Baseline (TF-IDF + LogReg)", labels[test_idx], baseline.predict(test_texts))]

    # -----------------------------------------------------------------------
    # STEP 6 (Task 4): Embeddings + Logistic Regression.
    # -----------------------------------------------------------------------
    emb_clf = new_logistic_regression().fit(X_all[train_idx], labels[train_idx])
    results.append(
        evaluate("Embeddings + LogReg", labels[test_idx], emb_clf.predict(X_all[test_idx]))
    )

    # -----------------------------------------------------------------------
    # STEP 7 (Task 5): Cross-validation = repeat train/test several times on
    # different slices, so the score does not depend on one lucky split.
    # -----------------------------------------------------------------------
    n_splits = min(5, int(pd.Series(labels).value_counts().min()))
    cv_results = []
    if n_splits >= 2:
        cv = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=42)
        print(f"Cross-validation with {n_splits} folds:\n")
        cv_results.append(evaluate(
            "CV Baseline (TF-IDF + LogReg)", labels,
            cross_val_predict(new_baseline(), texts, labels, cv=cv)))
        cv_results.append(evaluate(
            "CV Embeddings + LogReg", labels,
            cross_val_predict(new_logistic_regression(), X_all, labels, cv=cv)))

    # -----------------------------------------------------------------------
    # STEP 8 (Task 5): Print the comparison table + one-sentence winner.
    # -----------------------------------------------------------------------
    table = pd.DataFrame(results + cv_results)
    print("===== COMPARISON TABLE =====")
    print(table.to_string(index=False, float_format=lambda v: f"{v:.2f}"))

    final_rows = cv_results if cv_results else results
    best = max(final_rows, key=lambda r: (r["high_recall"], r["accuracy"]))
    print(f"\nBest at catching High-risk businesses: {best['model']} "
          f"(High recall {best['high_recall']:.2f}, accuracy {best['accuracy']:.2f})\n")

    # -----------------------------------------------------------------------
    # STEP 9 (Tasks 4 + 6): Train the FINAL model on ALL the data and save it.
    #   clf = Logistic Regression  -> predicts High / Medium / Low
    #   nn  = kNN                  -> finds the 3 most similar labeled examples
    # -----------------------------------------------------------------------
    final_clf = new_logistic_regression().fit(X_all, labels)
    nn = NearestNeighbors(n_neighbors=min(3, len(df)), metric="cosine").fit(X_all)

    bundle = {"clf": final_clf, "nn": nn, "texts": texts, "labels": labels.tolist()}
    risk_model.MODEL_PATH.parent.mkdir(exist_ok=True)
    joblib.dump(bundle, risk_model.MODEL_PATH)
    print(f"Saved model to {risk_model.MODEL_PATH}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", default="data/sample_labeled.csv", help="Path to labeled CSV")
    args = parser.parse_args()
    main(args.data)
