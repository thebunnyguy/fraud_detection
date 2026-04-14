"""
model/train_model.py
Train XGBoost on Kaggle credit card fraud dataset and save for Lambda deployment.

Run this ONCE locally before deploying Lambda.

Requirements:
    pip install xgboost scikit-learn pandas joblib
Dataset:
    kaggle datasets download -d mlg-ulb/creditcardfraud
    unzip creditcard.csv.zip
"""

import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, roc_auc_score
from xgboost import XGBClassifier
import joblib
import os

# Dataset path: look in model/ directory first, then project root
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_script_csv = os.path.join(SCRIPT_DIR, "creditcard.csv")
_root_csv = os.path.join(os.path.dirname(SCRIPT_DIR), "creditcard.csv")
CSV_PATH = _script_csv if os.path.exists(_script_csv) else _root_csv

# ── 1. Load & prepare data ────────────────────────────────────
print(f"Loading dataset from {CSV_PATH} ...")
df = pd.read_csv(CSV_PATH)

# Normalize column names to lowercase
df.columns = [c.lower() for c in df.columns]
print(f"Dataset: {df.shape[0]:,} rows | Fraud rate: {df['class'].mean()*100:.3f}%")

# Feature order MUST match what Lambda sends: time, amount, v1…v28
FEATURE_ORDER = ["time", "amount"] + [f"v{i}" for i in range(1, 29)]
X = df[FEATURE_ORDER]
y = df["class"]

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)

# ── 2. Train XGBoost (handles class imbalance via scale_pos_weight) ──
fraud_ratio = (y_train == 0).sum() / (y_train == 1).sum()
print(f"\nTraining XGBoost (scale_pos_weight={fraud_ratio:.1f})...")

model = XGBClassifier(
    n_estimators=300,
    max_depth=6,
    learning_rate=0.05,
    subsample=0.8,
    colsample_bytree=0.8,
    scale_pos_weight=fraud_ratio,
    eval_metric="auc",
    random_state=42,
    n_jobs=-1,
)
model.fit(
    X_train, y_train,
    eval_set=[(X_test, y_test)],
    verbose=50,
)

# ── 3. Evaluate ───────────────────────────────────────────────
y_pred = model.predict(X_test)
y_prob = model.predict_proba(X_test)[:, 1]

print("\n── Evaluation ──")
print(classification_report(y_test, y_pred, target_names=["Legit", "Fraud"]))
print(f"ROC-AUC: {roc_auc_score(y_test, y_prob):.4f}")

# ── 4. Save model for Lambda ──────────────────────────────────
# Save to lambda/ directory so it gets packaged with Lambda code
lambda_dir = os.path.join(os.path.dirname(SCRIPT_DIR), "lambda")
model_path = os.path.join(lambda_dir, "fraud_model.pkl")

joblib.dump(model, model_path)
print(f"\n✅ Model saved to {model_path}")
print(f"Model size: {os.path.getsize(model_path) / 1024 / 1024:.2f} MB")
print("\nNext steps:")
print("1. Commit fraud_model.pkl to git (or add to Lambda zip)")
print("2. Deploy Lambda via GitHub Actions CI/CD")
print("3. Test the endpoint")
