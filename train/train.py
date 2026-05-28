import os
import sys

import joblib
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
from sklearn.model_selection import train_test_split
from sklearn.svm import SVC

# Make the repo root importable so the shared normalizer is found regardless of CWD.
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)
from preprocessing import ACTIVE_BACKEND, normalize_text

DATA_PATH = os.path.join(BASE_DIR, "data.csv")
MODEL_PATH = os.path.join(BASE_DIR, "model.pkl")
VECTORIZER_PATH = os.path.join(BASE_DIR, "vectorizer.pkl")

print(f"Persian normalization backend: {ACTIVE_BACKEND}")

if not os.path.exists(DATA_PATH):
    raise SystemExit(f"data.csv not found at {DATA_PATH}. Provide it with 'message' and 'label' columns.")

df = pd.read_csv(DATA_PATH)
missing = {"message", "label"} - set(df.columns)
if missing:
    raise SystemExit(f"data.csv is missing required column(s): {', '.join(sorted(missing))}.")

# Drop blanks/NaNs and exact duplicates before training.
df = df[["message", "label"]].dropna()
df["message"] = df["message"].astype(str).map(normalize_text)
df["label"] = df["label"].astype(str).str.strip()
df = df[df["message"].str.len() > 0].drop_duplicates()

if df.empty:
    raise SystemExit("No usable rows in data.csv after cleaning.")
if "spam" not in set(df["label"]):
    raise SystemExit("No 'spam' labelled rows found. The bot requires the positive class to be exactly 'spam'.")

X = df["message"]
y = df["label"]
print(f"Training on {len(df)} rows. Label distribution:\n{y.value_counts().to_string()}")

# These parameters are tuned for Persian short-message spam; change with care.
vectorizer = TfidfVectorizer(
    analyzer="word",
    ngram_range=(1, 2),
    max_features=5000,
    min_df=2,
    max_df=0.9,
)

X_tfidf = vectorizer.fit_transform(X)

# Stratify keeps the spam/normal ratio consistent across train and test splits.
X_train, X_test, y_train, y_test = train_test_split(
    X_tfidf, y, test_size=0.2, random_state=42, stratify=y
)

# class_weight='balanced' compensates for the usual spam/normal imbalance.
# probability=True is REQUIRED: the bot calls predict_proba at runtime.
model = SVC(kernel="linear", probability=True, class_weight="balanced")
model.fit(X_train, y_train)

y_pred = model.predict(X_test)
accuracy = accuracy_score(y_test, y_pred)
print(f"\nAccuracy: {accuracy * 100:.2f}%")
print("\nClassification report:")
print(classification_report(y_test, y_pred))
print("Confusion matrix (rows=true, cols=pred), labels:", list(model.classes_))
print(confusion_matrix(y_test, y_pred))
if accuracy < 0.90:
    print("\nAccuracy is below 90% — consider retraining with more/cleaner data.")

joblib.dump(model, MODEL_PATH)
joblib.dump(vectorizer, VECTORIZER_PATH)
print(f"\nSaved model -> {MODEL_PATH}\nSaved vectorizer -> {VECTORIZER_PATH}")
