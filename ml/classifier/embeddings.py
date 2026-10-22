import pandas as pd
from sentence_transformers import SentenceTransformer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold, cross_val_predict
from sklearn.metrics import classification_report, confusion_matrix

df = pd.read_csv("data/labeled_descriptions.csv")
y = df["risk"]

encoder = SentenceTransformer("all-MiniLM-L6-v2")
X = encoder.encode(df["description"].tolist())

model = LogisticRegression(max_iter=1000)
cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=0)
pred = cross_val_predict(model, X, y, cv=cv)

print(classification_report(y, pred))
print(confusion_matrix(y, pred, labels=["High", "Medium", "Low"]))