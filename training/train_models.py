"""
Train both XGBoost and Isolation Forest models
"""
import pandas as pd
import numpy as np
import joblib
import json
from pathlib import Path
from sklearn.model_selection import train_test_split
from sklearn.ensemble import IsolationForest
from sklearn.metrics import classification_report, roc_auc_score, precision_recall_curve, auc
from xgboost import XGBClassifier

# Paths
BASE_DIR = Path(__file__).parent.parent
DATA_PATH = BASE_DIR / "creditcard.csv"
ARTIFACTS_DIR = BASE_DIR / "artifacts"
ARTIFACTS_DIR.mkdir(exist_ok=True)

# Feature configuration
FEATURE_COLS = ["time", "amount"] + [f"v{i}" for i in range(1, 29)]

print("=" * 60)
print("FRAUD DETECTION MODEL TRAINING")
print("=" * 60)

# Load data
print(f"\n[1/6] Loading dataset from {DATA_PATH}")
if not DATA_PATH.exists():
    raise FileNotFoundError(f"Dataset not found at {DATA_PATH}")

df = pd.read_csv(DATA_PATH)
df.columns = [c.lower() for c in df.columns]

print(f"Dataset: {len(df):,} transactions")
print(f"Fraud rate: {df['class'].mean()*100:.3f}%")

# Prepare features
X = df[FEATURE_COLS]
y = df["class"]

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)

print(f"Train: {len(X_train):,} | Test: {len(X_test):,}")

# Train XGBoost
print("\n[2/6] Training XGBoost classifier")
fraud_ratio = (y_train == 0).sum() / (y_train == 1).sum()
print(f"Class imbalance ratio: {fraud_ratio:.1f}:1")

xgb_model = XGBClassifier(
    n_estimators=300,
    max_depth=6,
    learning_rate=0.05,
    subsample=0.8,
    colsample_bytree=0.8,
    scale_pos_weight=fraud_ratio,
    eval_metric="auc",
    random_state=42,
    n_jobs=-1
)

xgb_model.fit(X_train, y_train, eval_set=[(X_test, y_test)], verbose=False)
print("XGBoost training complete")

# Evaluate XGBoost
print("\n[3/6] Evaluating XGBoost")
y_pred = xgb_model.predict(X_test)
y_prob = xgb_model.predict_proba(X_test)[:, 1]

print("\nClassification Report:")
print(classification_report(y_test, y_pred, target_names=["Legitimate", "Fraud"]))
print(f"ROC-AUC: {roc_auc_score(y_test, y_prob):.4f}")

precision, recall, _ = precision_recall_curve(y_test, y_prob)
pr_auc = auc(recall, precision)
print(f"PR-AUC: {pr_auc:.4f}")

# Train Isolation Forest on normal transactions
print("\n[4/6] Training Isolation Forest (anomaly detector)")
X_normal = X_train[y_train == 0]
print(f"Training on {len(X_normal):,} legitimate transactions")

iso_model = IsolationForest(
    n_estimators=100,
    contamination=0.001,
    random_state=42,
    n_jobs=-1
)

iso_model.fit(X_normal)
print("Isolation Forest training complete")

# Save models
print("\n[5/6] Saving models")
xgb_path = ARTIFACTS_DIR / "xgboost_model.pkl"
iso_path = ARTIFACTS_DIR / "isolation_forest.pkl"
features_path = ARTIFACTS_DIR / "feature_columns.json"

joblib.dump(xgb_model, xgb_path)
print(f"Saved XGBoost: {xgb_path}")

joblib.dump(iso_model, iso_path)
print(f"Saved Isolation Forest: {iso_path}")

with open(features_path, "w") as f:
    json.dump(FEATURE_COLS, f)
print(f"Saved feature columns: {features_path}")

# Test anomaly detector
print("\n[6/6] Testing anomaly detector")
anomaly_scores_test = iso_model.decision_function(X_test)
anomaly_normalized = 1 / (1 + np.exp(anomaly_scores_test))

fraud_anomaly_mean = anomaly_normalized[y_test == 1].mean()
legit_anomaly_mean = anomaly_normalized[y_test == 0].mean()

print(f"Avg anomaly score - Fraud: {fraud_anomaly_mean:.3f}")
print(f"Avg anomaly score - Legitimate: {legit_anomaly_mean:.3f}")

print("\n" + "=" * 60)
print("TRAINING COMPLETE")
print("=" * 60)
print(f"\nArtifacts saved to: {ARTIFACTS_DIR}")
print("\nNext steps:")
print("1. Run the backend: python app_main.py")
print("2. Test the API: curl http://localhost:5000/health")
